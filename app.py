#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 BiP Bot - Etkinlik Yönetim Sistemi
SQLite veritabanı ile güçlendirilmiş BiP bot uygulaması

Özellikler:
- Etkinlik oluşturma ve yönetimi
- Tarih/saat slot oylaması
- Mekan seçimi ve oylama
- Gider takibi ve masraf dağılımı
- Otomatik hatırlatıcılar
- Moderator kontrolü

Yazar: BiP Bot Development Team
Versiyon: 2.0.0 (SQLite)
"""

import os
import time
import logging
from flask import Flask, request, jsonify
from datetime import datetime
from threading import Timer
from flask_cors import CORS
from functools import wraps
from collections import defaultdict
from database import db

# Logging yapılandırması
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Uygulama yapılandırması
app.config['SECRET_KEY'] = 'your-secret-key-here'

user_last_action = {}

def check_rate_limit(user_id):
    """Kullanıcı rate limit kontrolü yapar"""
    now = time.time()
    if user_id in user_last_action and now - user_last_action[user_id] < 2:
        return False
    user_last_action[user_id] = now
    return True

def check_user_permission(user_id, event_id, permission):
    """Kullanıcının belirli bir etkinlik için izin kontrolü"""
    user = db.get_user_by_id(user_id)
    if not user:
        return False
    
    user_role = user.get('role', 'user')
    event = db.get_event_by_id(event_id)
    
    if not event:
        return False
    
    # Etkinlik sahibi her zaman tam yetki
    if event['created_by'] == user_id:
        return True
    
    # Moderator yetkileri
    if user_role == 'moderator':
        return permission in ['vote', 'add_expense', 'view', 'close_slot', 'lock_vote']
    
    # Normal kullanıcı yetkileri
    if user_role == 'user':
        return permission in ['vote', 'add_expense', 'view']
    
    # Guest yetkileri
    if user_role == 'guest':
        return permission in ['view']
    
    return False

# Mesajı API yanıtına eklemek için global değişken
last_bip_message = ""

def send_bip_message(group_id, message):
    """BiP mesajı gönderir (mock)"""
    global last_bip_message
    last_bip_message = f"[MOCK BiP GRUP {group_id}] {message}"
    logger.info(f"BiP mesajı gönderildi: {message}")
    print(last_bip_message)

def remind(event_id, group_id, delay, custom_message=None):
    """Hatırlatıcı zamanlayıcısı başlatır"""
    def send_reminder():
        if custom_message:
            send_bip_message(group_id, custom_message)
        else:
            hours = int(delay / 3600)
            send_bip_message(group_id, f"Etkinlik {event_id} için {hours} saat kaldi!")
    Timer(delay, send_reminder).start()

def validate_input(data, required_fields):
    """Giriş verilerini doğrular"""
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"Eksik alan: {field}"
    return True, "OK"

@app.route('/webhook/bip', methods=['POST'])
def bip_webhook():
    """BiP webhook endpoint'i - komutları işler"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'Geçersiz JSON verisi'}), 400
        
        # Giriş doğrulama
        is_valid, error_msg = validate_input(data, ['message', 'user_id', 'group_id'])
        if not is_valid:
            return jsonify({'status': 'error', 'message': error_msg}), 400
        
        message = data.get('message', '').strip()
        user_id = data.get('user_id', '').strip()
        group_id = data.get('group_id', '').strip()
        
        # Rate limiting kontrolü
        if not check_rate_limit(user_id):
            return jsonify({
                'status': 'error', 
                'bip_message': f"[MOCK BiP GRUP {group_id}] Çok hızlı mesaj gönderiyorsunuz. Lütfen {RATE_LIMIT_SECONDS} saniye bekleyin."
            }), 429
        
        logger.info(f"Webhook alındı - Kullanıcı: {user_id}, Grup: {group_id}, Mesaj: {message}")

        # Kullanıcıyı kaydet/güncelle
        db.create_or_update_user(user_id)

        # Etkinlik oluştur
        if message.startswith('/yeni'):
            title = message[5:].strip()
            if not title:
                response_msg = "Kullanim: /yeni ETKINLIK_ADI"
            else:
                try:
                    event_id = db.create_event(title, user_id, group_id)
                    response_msg = f"Etkinlik olusturuldu: {title} (ID: {event_id})"
                except Exception as e:
                    logger.error(f"Etkinlik oluşturma hatası: {str(e)}")
                    response_msg = "Etkinlik olusturulurken hata olustu."

        # Slot kapatma (moderatör) - /slot'dan önce kontrol et
        elif message.startswith('/slot_kapat'):
            parts = message.split()
            if len(parts) < 2:
                response_msg = "Kullanim: /slot_kapat SLOT_ID"
            else:
                try:
                    slot_id = int(parts[1])  # Sadece ilk parametreyi al, fazla parametreleri görmezden gel
                    latest_event = db.get_latest_event(group_id)
                    if not latest_event:
                        response_msg = "Etkinlik yok!"
                    elif not db.is_moderator(user_id, latest_event['event_id']):
                        response_msg = "Bu islemi sadece moderatör yapabilir."
                    else:
                        # Slot'u kapat (status = 'closed')
                        with db.get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                'UPDATE slots SET status = ? WHERE slot_id = ? AND event_id = ?',
                                ('closed', slot_id, latest_event['event_id'])
                            )
                            conn.commit()
                        response_msg = f"Slot {slot_id} kapatildi."
                except Exception as e:
                    logger.error(f"Slot kapatma hatası: {str(e)}")
                    response_msg = f"Slot kapatilirken hata olustu: {str(e)}"

        # Slot ekle
        elif message.startswith('/slot'):
            parts = message.split()
            if len(parts) < 3:
                response_msg = "Kullanim: /slot YYYY-MM-DD HH:MM-HH:MM"
            else:
                try:
                    date_part, time_part = parts[1], parts[2]
                    start_time, end_time = time_part.split('-')
                    start_dt = datetime.strptime(f"{date_part} {start_time}", "%Y-%m-%d %H:%M")
                    end_dt = datetime.strptime(f"{date_part} {end_time}", "%Y-%m-%d %H:%M")
                    
                    if start_dt < datetime.now():
                        response_msg = "Gecmis tarih secilemez."
                    elif start_dt >= end_dt:
                        response_msg = "Baslangic saati bitis saatinden once olmali."
                    else:
                        latest_event = db.get_latest_event(group_id)
                        if not latest_event:
                            response_msg = "Once etkinlik olusturun."
                        else:
                            slot_id = db.create_slot(
                                latest_event['event_id'], 
                                start_dt.isoformat(), 
                                end_dt.isoformat()
                            )
                            response_msg = f"Slot eklendi: {start_dt.strftime('%Y-%m-%d %H:%M')} - {end_dt.strftime('%H:%M')} (ID: {slot_id})"
                            
                            # Hatırlatıcılar
                            now = datetime.now()
                            delay_24h = (start_dt - now).total_seconds() - 24*3600
                            delay_1h = (start_dt - now).total_seconds() - 1*3600
                            
                            if delay_24h > 0:
                                remind(latest_event['event_id'], group_id, delay_24h)
                            if delay_1h > 0:
                                remind(latest_event['event_id'], group_id, delay_1h)
                except Exception as e:
                    logger.error(f"Slot ekleme hatası: {str(e)}")
                    response_msg = "Tarih/saat formatı yanlış. Örnek: /slot 2025-10-12 18:00-20:00"

        # Slot oyu
        elif message.startswith('/katil'):
            parts = message.split()
            if len(parts) < 3 or not parts[1].startswith('slot='):
                response_msg = "Kullanim: /katil slot=1 yes/no"
            else:
                try:
                    slot_str = parts[1].split('=')[1]
                    choice = parts[2]
                    if choice not in ['yes', 'no']:
                        response_msg = "Choice: yes veya no"
                    else:
                        slot_id = int(slot_str)
                        latest_event = db.get_latest_event(group_id)
                        if not latest_event:
                            response_msg = "Etkinlik yok!"
                        else:
                            db.vote_slot(latest_event['event_id'], slot_id, user_id, choice)
                            response_msg = f"Slot {slot_id} icin oy: {choice}"
                except Exception as e:
                    logger.error(f"Slot oy hatası: {str(e)}")
                    response_msg = "Oy verilirken hata olustu."

        # Mekan ekle
        elif message.startswith('/mekan'):
            parts = message.split(maxsplit=3)
            if len(parts) < 2:
                response_msg = "Kullanim: /mekan MEKAN_ADI [enlem boylam]"
            else:
                try:
                    mekan_adi = parts[1]
                    latitude = None
                    longitude = None
                    if len(parts) == 4:
                        latitude = float(parts[2])
                        longitude = float(parts[3])
                    
                    latest_event = db.get_latest_event(group_id)
                    if not latest_event:
                        response_msg = "Once etkinlik olusturun."
                    else:
                        # Anket varsa al, yoksa oluştur
                        poll = db.get_poll_by_event(latest_event['event_id'])
                        if not poll:
                            poll_id = db.create_poll(latest_event['event_id'], "Mekan secimi")
                        else:
                            poll_id = poll['poll_id']
                        
                        choice_id = db.create_poll_choice(poll_id, mekan_adi, latitude, longitude)
                        response_msg = f"Mekan eklendi: {mekan_adi} (ID: {choice_id})"
                        if latitude and longitude:
                            response_msg += f" ({latitude}, {longitude})"
                except Exception as e:
                    logger.error(f"Mekan ekleme hatası: {str(e)}")
                    response_msg = "Mekan eklenirken hata olustu."

        # Mekan oyu
        elif message.startswith('/oy_mekan'):
            parts = message.split()
            if len(parts) < 2:
                response_msg = "Kullanim: /oy_mekan CHOICE_ID"
            else:
                try:
                    choice_id = int(parts[1])
                    latest_event = db.get_latest_event(group_id)
                    if not latest_event:
                        response_msg = "Etkinlik yok!"
                    else:
                        poll = db.get_poll_by_event(latest_event['event_id'])
                        if not poll:
                            response_msg = "Mekan anketi yok!"
                        else:
                            db.vote_poll(poll['poll_id'], choice_id, user_id)
                            response_msg = f"Mekan icin oy verildi: {choice_id}"
                except Exception as e:
                    logger.error(f"Mekan oy hatası: {str(e)}")
                    response_msg = "Oy verilirken hata olustu."

        # Gider ekle
        elif message.startswith('/gider'):
            parts = message.split(maxsplit=2)
            if len(parts) < 3:
                response_msg = "Kullanim: /gider TUTAR \"Aciklama\" [agirlik]"
            else:
                try:
                    amount = float(parts[1])
                    rest = parts[2].strip()
                    if rest.startswith('"'):
                        end_quote = rest.find('"', 1)
                        if end_quote == -1:
                            response_msg = "Aciklama tirnak icinde olmali."
                        else:
                            notes = rest[1:end_quote]
                            weight_str = rest[end_quote+1:].strip()
                            weight = float(weight_str) if weight_str else 1.0
                    else:
                        notes = rest
                        weight = 1.0
                    
                    latest_event = db.get_latest_event(group_id)
                    if not latest_event:
                        response_msg = "Once etkinlik olusturun."
                    else:
                        expense_id = db.create_expense(
                            latest_event['event_id'], user_id, amount, notes, weight
                        )
                        response_msg = f"Gider eklendi: {amount} TL, Not: {notes}, Agirlik: {weight} (ID: {expense_id})"
                except Exception as e:
                    logger.error(f"Gider ekleme hatası: {str(e)}")
                    response_msg = "Gider eklenirken hata olustu."

        # Özet
        elif message == '/ozet':
            try:
                latest_event = db.get_latest_event(group_id)
                if not latest_event:
                    response_msg = "Henuz etkinlik yok."
                else:
                    summary = db.get_event_summary(latest_event['event_id'])
                    
                    response_msg = f"Etkinlik: {summary['event']['title']}\n"
                    response_msg += f"Olusturan: {summary['event']['created_by']}\n"
                    response_msg += f"Tarih: {summary['event']['created_at']}\n\n"
                    
                    # Slot özeti
                    response_msg += "Slotlar:\n"
                    for slot in summary['slots']:
                        if slot['status'] == 'active':
                            yes_count = len([v for v in summary['slot_votes'] 
                                           if v['slot_id'] == slot['slot_id'] and v['choice'] == 'yes'])
                            no_count = len([v for v in summary['slot_votes'] 
                                          if v['slot_id'] == slot['slot_id'] and v['choice'] == 'no'])
                            response_msg += f"Slot {slot['slot_id']} ({slot['start_datetime']}-{slot['end_datetime']}): Evet: {yes_count}, Hayir: {no_count}\n"
                    
                    # Mekan özeti
                    if summary['poll']:
                        response_msg += "\nMekanlar:\n"
                        for choice in summary['poll_choices']:
                            vote_count = len([v for v in summary['poll_votes'] 
                                            if v['choice_id'] == choice['choice_id']])
                            coord = f" ({choice['latitude']}, {choice['longitude']})" if choice['latitude'] and choice['longitude'] else ""
                            response_msg += f"{choice['text']}{coord}: {vote_count} oy\n"
                    
                    # Gider özeti
                    if summary['expenses']:
                        total_expense = sum(exp['amount'] for exp in summary['expenses'])
                        response_msg += f"\nToplam gider: {total_expense} TL\n"
                        for expense in summary['expenses']:
                            response_msg += f"- {expense['amount']} TL: {expense['notes']} (Agirlik: {expense['weight']})\n"
            except Exception as e:
                logger.error(f"Özet hatası: {str(e)}")
                response_msg = "Ozet olusturulurken hata olustu."

        # Özet komutu
        elif message.startswith('/ozet'):
            latest_event = db.get_latest_event(group_id)
            if not latest_event:
                response_msg = "Etkinlik yok!"
            else:
                summary = db.get_event_summary(latest_event['event_id'])
                
                response_msg = f"📊 **{latest_event['title']} Özeti**\n\n"
                
                # En iyi slot - daha detaylı
                if summary['best_slot']:
                    best_slot = summary['best_slot']
                    # Slot ID'sini bul
                    best_slot_id = None
                    for slot_id, slot_data in summary['slots'].items():
                        if slot_data['start_datetime'] == best_slot['start_datetime']:
                            best_slot_id = slot_id
                            break
                    
                    response_msg += f"🥇 **EN ÇOK OY ALAN SLOT:**\n"
                    response_msg += f"   📅 **Slot #{best_slot_id}:** {best_slot['start_datetime']} - {best_slot['end_datetime']}\n"
                    response_msg += f"   ✅ **Evet Oyları:** {best_slot['yes_votes']}\n"
                    response_msg += f"   ❌ **Hayır Oyları:** {best_slot['no_votes']}\n"
                    response_msg += f"   📊 **Toplam Oy:** {best_slot['total_votes']}\n\n"
                else:
                    response_msg += "⏰ **En Çok Oy Alan Slot:** Henüz oy verilmemiş\n\n"
                
                # Tüm slotların listesi
                if summary['slots']:
                    response_msg += "📋 **Tüm Slotlar:**\n"
                    for slot_id, slot_data in summary['slots'].items():
                        response_msg += f"   • **Slot #{slot_id}:** {slot_data['start_datetime']} ({slot_data['yes_votes']} evet, {slot_data['no_votes']} hayır)\n"
                    response_msg += "\n"
                
                # En iyi mekan
                if summary['best_choice']:
                    best_choice = summary['best_choice']
                    response_msg += f"🏆 **EN ÇOK OY ALAN MEKAN:**\n"
                    response_msg += f"   🏢 **{best_choice['text']}** ({best_choice['votes']} oy)\n\n"
                else:
                    response_msg += "🏢 **En Çok Oy Alan Mekan:** Henüz oy verilmemiş\n\n"
                
                # Gider özeti
                response_msg += f"💰 **MALİ DURUM:**\n"
                response_msg += f"   💵 **Toplam Gider:** {summary['total_expense']} TL\n"
                response_msg += f"   👥 **Katılımcı Sayısı:** {summary['participant_count']} kişi\n"
                response_msg += f"   📝 **Gider Sayısı:** {len(summary['expenses'])} adet"

        # Davet komutu
        elif message.startswith('/davet'):
            latest_event = db.get_latest_event(group_id)
            if not latest_event:
                response_msg = "Etkinlik yok!"
            else:
                event_id = latest_event['event_id']
                invite_link = f"http://localhost:5000/join/{event_id}"
                response_msg = f"🔗 **{latest_event['title']} Davet Linki:**\n{invite_link}\n\nBu linki arkadaşlarınızla paylaşabilirsiniz!"

        # Analitik komutu
        elif message.startswith('/analitik'):
            latest_event = db.get_latest_event(group_id)
            if not latest_event:
                response_msg = "Etkinlik yok!"
            else:
                summary = db.get_event_summary(latest_event['event_id'])
                
                # Katılım oranı hesapla
                total_slots = len(summary.get('slots', {}))
                total_votes = sum(slot.get('yes_votes', 0) + slot.get('no_votes', 0) for slot in summary.get('slots', {}).values())
                participant_count = summary.get('participant_count', 0)
                
                participation_rate = 0
                if total_slots > 0 and participant_count > 0:
                    participation_rate = (total_votes / (total_slots * participant_count)) * 100
                
                response_msg = f"📊 **{latest_event['title']} Analitikleri**\n\n"
                response_msg += f"👥 **Katılımcı:** {participant_count} kişi\n"
                response_msg += f"📈 **Katılım Oranı:** %{participation_rate:.1f}\n"
                response_msg += f"⏰ **Slot Sayısı:** {total_slots}\n"
                response_msg += f"🗳️ **Toplam Oy:** {total_votes}\n"
                response_msg += f"💰 **Toplam Gider:** {summary['total_expense']} TL\n"
                response_msg += f"📝 **Gider Sayısı:** {len(summary['expenses'])} adet"

        # Konum komutu
        elif message.startswith('/konum'):
            parts = message.split()
            if len(parts) < 2:
                response_msg = "Kullanim: /konum [Mekan ID]"
            else:
                try:
                    choice_id = int(parts[1])
                    latest_event = db.get_latest_event(group_id)
                    if not latest_event:
                        response_msg = "Etkinlik yok!"
                    else:
                        # Mock konum verileri
                        mock_locations = {
                            1: {'name': 'Pizza Palace', 'address': 'Beşiktaş, İstanbul', 'distance': '2.5 km'},
                            2: {'name': 'Ek Bina Kafe', 'address': 'Şişli, İstanbul', 'distance': '3.1 km'},
                            3: {'name': 'Kütüphane', 'address': 'Beyoğlu, İstanbul', 'distance': '1.8 km'}
                        }
                        
                        location = mock_locations.get(choice_id, {'name': 'Bilinmeyen Mekan', 'address': 'Adres bilgisi yok', 'distance': 'N/A'})
                        
                        response_msg = f"📍 **{location['name']} Konum Bilgileri**\n\n"
                        response_msg += f"🏠 **Adres:** {location['address']}\n"
                        response_msg += f"📏 **Mesafe:** {location['distance']}\n"
                        response_msg += f"🗺️ **Harita:** https://maps.google.com"
                except ValueError:
                    response_msg = "Geçersiz mekan ID!"

        # Test komutu
        elif message.startswith('/test'):
            response_msg = "Bot calisiyor! SQLite veritabani aktif. Test basarili."

        else:
            response_msg = f"Bilinmeyen komut: {message}"

        return jsonify({
            'status': 'ok', 
            'bip_message': f"[MOCK BiP GRUP {group_id}] {response_msg}"
        })
    
    except Exception as e:
        logger.error(f"Webhook genel hatası: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ==================== RESTful API Endpoints ====================

@app.route('/events', methods=['POST'])
def create_event_api():
    """Yeni etkinlik oluşturur - POST /events"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'Geçersiz JSON verisi'}), 400
        
        # Gerekli alanları kontrol et
        is_valid, error_msg = validate_input(data, ['title', 'created_by', 'group_id'])
        if not is_valid:
            return jsonify({'status': 'error', 'message': error_msg}), 400
        
        title = data.get('title', '').strip()
        created_by = data.get('created_by', '').strip()
        group_id = data.get('group_id', '').strip()
        
        # Kullanıcıyı kaydet/güncelle
        db.create_or_update_user(created_by)
        
        # Etkinlik oluştur
        event_id = db.create_event(title, created_by, group_id)
        
        return jsonify({
            'status': 'success',
            'message': f'Etkinlik oluşturuldu: {title}',
            'event_id': event_id,
            'data': {
                'event_id': event_id,
                'title': title,
                'created_by': created_by,
                'group_id': group_id
            }
        })
        
    except Exception as e:
        logger.error(f"Etkinlik oluşturma API hatası: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Etkinlik oluşturulurken hata oluştu'}), 500

@app.route('/events/<int:event_id>/slots', methods=['POST'])
def add_slot_api(event_id):
    """Etkinliğe slot ekler - POST /events/{id}/slots"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'Geçersiz JSON verisi'}), 400
        
        # Gerekli alanları kontrol et
        is_valid, error_msg = validate_input(data, ['start_datetime', 'end_datetime'])
        if not is_valid:
            return jsonify({'status': 'error', 'message': error_msg}), 400
        
        start_datetime = data.get('start_datetime')
        end_datetime = data.get('end_datetime')
        
        # Etkinliğin var olup olmadığını kontrol et
        event = db.get_event_by_id(event_id)
        if not event:
            return jsonify({'status': 'error', 'message': 'Etkinlik bulunamadı'}), 404
        
        # Tarih formatını kontrol et
        try:
            # Timezone bilgisi yoksa UTC olarak ekle
            if 'T' in start_datetime and not ('+' in start_datetime or 'Z' in start_datetime):
                start_datetime += '+00:00'
            if 'T' in end_datetime and not ('+' in end_datetime or 'Z' in end_datetime):
                end_datetime += '+00:00'
                
            start_dt = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Geçersiz tarih formatı. ISO format kullanın'}), 400
        
        # Tarih kontrolleri (timezone-aware datetime kullan)
        from datetime import timezone
        now_utc = datetime.now(timezone.utc)
        if start_dt < now_utc:
            return jsonify({'status': 'error', 'message': 'Geçmiş tarih seçilemez'}), 400
        
        if start_dt >= end_dt:
            return jsonify({'status': 'error', 'message': 'Başlangıç saati bitiş saatinden önce olmalı'}), 400
        
        # Slot oluştur (created_by ile)
        user_id = data.get('user_id', '')
        slot_id = db.create_slot(event_id, start_datetime, end_datetime, user_id)
        
        # Hatırlatıcıları ayarla
        now_utc = datetime.now(timezone.utc)
        delay_24h = (start_dt - now_utc).total_seconds() - 24*3600
        delay_1h = (start_dt - now_utc).total_seconds() - 1*3600
        
        if delay_24h > 0:
            remind(event_id, event['group_id'], delay_24h, "24 saat sonra etkinlik başlıyor! Hazır mısınız? 🎉")
        if delay_1h > 0:
            remind(event_id, event['group_id'], delay_1h, "Etkinlik 1 saat sonra başlıyor! Son hazırlıklarınızı yapın! ⏰")
        
        return jsonify({
            'status': 'success',
            'message': f'Slot eklendi: {start_dt.strftime("%Y-%m-%d %H:%M")} - {end_dt.strftime("%H:%M")}',
            'slot_id': slot_id,
            'data': {
                'slot_id': slot_id,
                'event_id': event_id,
                'start_datetime': start_datetime,
                'end_datetime': end_datetime
            }
        })
        
    except Exception as e:
        logger.error(f"Slot ekleme API hatası: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Slot eklenirken hata oluştu'}), 500

@app.route('/events/<int:event_id>/vote-slot', methods=['POST'])
def vote_slot_api(event_id):
    """Slot için oy verir - POST /events/{id}/vote-slot"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'Geçersiz JSON verisi'}), 400
        
        # Gerekli alanları kontrol et
        is_valid, error_msg = validate_input(data, ['user_id', 'slot_id'])
        if not is_valid:
            return jsonify({'status': 'error', 'message': error_msg}), 400
        
        user_id = data.get('user_id', '').strip()
        slot_id = data.get('slot_id')
        
        # Etkinliğin var olup olmadığını kontrol et
        event = db.get_event_by_id(event_id)
        if not event:
            return jsonify({'status': 'error', 'message': 'Etkinlik bulunamadı'}), 404
        
        # Kullanıcıyı kaydet/güncelle
        db.create_or_update_user(user_id)
        
        # Kullanıcının daha önce slot oyu var mı kontrol et
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT slot_id FROM slot_votes 
                WHERE event_id = ? AND user_id = ?
            ''', (event_id, user_id))
            existing_vote = cursor.fetchone()
            
            if existing_vote:
                # Eski oyu sil
                cursor.execute('''
                    DELETE FROM slot_votes 
                    WHERE event_id = ? AND user_id = ?
                ''', (event_id, user_id))
            
            # Yeni oyu ver (her zaman 'yes' olarak)
            cursor.execute('''
                INSERT INTO slot_votes (event_id, slot_id, user_id, choice)
                VALUES (?, ?, ?, ?)
            ''', (event_id, slot_id, user_id, 'yes'))
            conn.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Slot {slot_id} için oyunuz verildi',
            'data': {
                'event_id': event_id,
                'slot_id': slot_id,
                'user_id': user_id,
                'choice': 'yes'
            }
        })
        
    except Exception as e:
        logger.error(f"Slot oy API hatası: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Oy verilirken hata oluştu'}), 500

@app.route('/events/<int:event_id>/poll', methods=['POST'])
def create_poll_api(event_id):
    """Anket oluşturur - POST /events/{id}/poll"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'Geçersiz JSON verisi'}), 400
        
        # Gerekli alanları kontrol et
        is_valid, error_msg = validate_input(data, ['question'])
        if not is_valid:
            return jsonify({'status': 'error', 'message': error_msg}), 400
        
        question = data.get('question', '').strip()
        
        # Etkinliğin var olup olmadığını kontrol et
        event = db.get_event_by_id(event_id)
        if not event:
            return jsonify({'status': 'error', 'message': 'Etkinlik bulunamadı'}), 404
        
        # Anket oluştur
        poll_id = db.create_poll(event_id, question)
        
        return jsonify({
            'status': 'success',
            'message': f'Anket oluşturuldu: {question}',
            'poll_id': poll_id,
            'data': {
                'poll_id': poll_id,
                'event_id': event_id,
                'question': question
            }
        })
        
    except Exception as e:
        logger.error(f"Anket oluşturma API hatası: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Anket oluşturulurken hata oluştu'}), 500

@app.route('/events/<int:event_id>/vote', methods=['POST'])
def vote_poll_api(event_id):
    """Anket için oy verir - POST /events/{id}/vote"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'Geçersiz JSON verisi'}), 400
        
        # Gerekli alanları kontrol et
        is_valid, error_msg = validate_input(data, ['user_id', 'choice_id'])
        if not is_valid:
            return jsonify({'status': 'error', 'message': error_msg}), 400
        
        user_id = data.get('user_id', '').strip()
        choice_id = data.get('choice_id')
        
        # Etkinliğin var olup olmadığını kontrol et
        event = db.get_event_by_id(event_id)
        if not event:
            return jsonify({'status': 'error', 'message': 'Etkinlik bulunamadı'}), 404
        
        # Anketin var olup olmadığını kontrol et
        poll = db.get_poll_by_event(event_id)
        if not poll:
            return jsonify({'status': 'error', 'message': 'Anket bulunamadı'}), 404
        
        # Kullanıcıyı kaydet/güncelle
        db.create_or_update_user(user_id)
        
        # Anket oyu ver
        db.vote_poll(poll['poll_id'], choice_id, user_id)
        
        return jsonify({
            'status': 'success',
            'message': f'Anket için oy verildi: {choice_id}',
            'data': {
                'event_id': event_id,
                'poll_id': poll['poll_id'],
                'choice_id': choice_id,
                'user_id': user_id
            }
        })
        
    except Exception as e:
        logger.error(f"Anket oy API hatası: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Oy verilirken hata oluştu'}), 500

@app.route('/events/<int:event_id>/expense', methods=['POST'])
def add_expense_api(event_id):
    """Gider ekler - POST /events/{id}/expense"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'Geçersiz JSON verisi'}), 400
        
        # Gerekli alanları kontrol et
        is_valid, error_msg = validate_input(data, ['user_id', 'amount', 'description', 'slot_id'])
        if not is_valid:
            return jsonify({'status': 'error', 'message': error_msg}), 400
        
        user_id = data.get('user_id', '').strip()
        amount = data.get('amount')
        description = data.get('description', '').strip()
        slot_id = data.get('slot_id')
        weight = data.get('weight', 1.0)
        
        # Etkinliğin var olup olmadığını kontrol et
        event = db.get_event_by_id(event_id)
        if not event:
            return jsonify({'status': 'error', 'message': 'Etkinlik bulunamadı'}), 404
        
        # Tutar kontrolü
        try:
            amount = float(amount)
            if amount <= 0:
                return jsonify({'status': 'error', 'message': 'Tutar pozitif olmalı'}), 400
        except (ValueError, TypeError):
            return jsonify({'status': 'error', 'message': 'Geçersiz tutar formatı'}), 400
        
        # Slot ID kontrolü
        try:
            slot_id = int(slot_id)
        except (ValueError, TypeError):
            return jsonify({'status': 'error', 'message': 'Geçersiz slot ID'}), 400
        
        # Slot'un var olup olmadığını kontrol et
        slot = db.get_slot_by_id(slot_id)
        if not slot or slot['event_id'] != event_id:
            return jsonify({'status': 'error', 'message': 'Geçersiz slot ID'}), 400
        
        # Kullanıcıyı kaydet/güncelle
        db.create_or_update_user(user_id)
        
        # Gider oluştur
        expense_id = db.create_expense(event_id, user_id, amount, description, weight)
        
        return jsonify({
            'status': 'success',
            'message': f'Gider eklendi: {amount} TL, Açıklama: {description}, Ağırlık: {weight}',
            'expense_id': expense_id,
            'data': {
                'expense_id': expense_id,
                'event_id': event_id,
                'user_id': user_id,
                'amount': amount,
                'description': description,
                'weight': weight
            }
        })
        
    except Exception as e:
        logger.error(f"Gider ekleme API hatası: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Gider eklenirken hata oluştu: {str(e)}'}), 500

@app.route('/events/<int:event_id>/summary', methods=['GET'])
def get_event_summary_api(event_id):
    """Etkinlik özetini getirir - GET /events/{id}/summary"""
    try:
        # Etkinliğin var olup olmadığını kontrol et
        event = db.get_event_by_id(event_id)
        if not event:
            return jsonify({'status': 'error', 'message': 'Etkinlik bulunamadı'}), 404
        
        # Özet verilerini al
        summary = db.get_event_summary(event_id)
        
        # Slot oylarını analiz et
        slot_stats = {}
        for slot in summary['slots']:
            if slot['status'] == 'active':
                yes_count = len([v for v in summary['slot_votes'] 
                               if v['slot_id'] == slot['slot_id'] and v['choice'] == 'yes'])
                no_count = len([v for v in summary['slot_votes'] 
                              if v['slot_id'] == slot['slot_id'] and v['choice'] == 'no'])
                slot_stats[slot['slot_id']] = {
                    'start_datetime': slot['start_datetime'],
                    'end_datetime': slot['end_datetime'],
                    'yes_votes': yes_count,
                    'no_votes': no_count,
                    'total_votes': yes_count + no_count
                }
        
        # Debug: Tüm slot oylarını göster
        logger.info(f"Event {event_id} - Slot oyları: {summary['slot_votes']}")
        logger.info(f"Event {event_id} - Slot stats: {slot_stats}")
        
        # Katılımcı sayısını hesapla (etkinlik listesi API ile aynı hesaplama)
        participant_count = len(set(vote['user_id'] for vote in summary['slot_votes']))
        
        # En çok oy alan slot
        best_slot = None
        if slot_stats:
            best_slot_id = max(slot_stats.keys(), key=lambda x: slot_stats[x]['yes_votes'])
            best_slot = slot_stats[best_slot_id]
        
        # Anket oylarını analiz et
        poll_stats = {}
        if summary['poll']:
            for choice in summary['poll_choices']:
                vote_count = len([v for v in summary['poll_votes'] 
                                if v['choice_id'] == choice['choice_id']])
                poll_stats[choice['choice_id']] = {
                    'text': choice['text'],
                    'latitude': choice['latitude'],
                    'longitude': choice['longitude'],
                    'votes': vote_count
                }
        
        # En çok oy alan seçenek
        best_choice = None
        if poll_stats:
            best_choice_id = max(poll_stats.keys(), key=lambda x: poll_stats[x]['votes'])
            best_choice = poll_stats[best_choice_id]
        
        # Gider analizi
        total_expense = sum(exp['amount'] for exp in summary['expenses'])
        total_weight = sum(exp['weight'] for exp in summary['expenses'])
        
        # Kullanıcı bakiyeleri
        balances = {}
        for expense in summary['expenses']:
            user_id = expense['user_id']
            if user_id not in balances:
                balances[user_id] = 0
            balances[user_id] += expense['amount']
        
        # Katılımcı sayısı
        all_users = set()
        for vote in summary['slot_votes']:
            all_users.add(vote['user_id'])
        for vote in summary['poll_votes']:
            all_users.add(vote['user_id'])
        for expense in summary['expenses']:
            all_users.add(expense['user_id'])
        
        participant_count = len(all_users)
        average_per_person = total_expense / participant_count if participant_count > 0 else 0
        
        # Her kullanıcının ödemesi gereken miktarı hesapla
        for user_id in balances:
            balances[user_id] -= average_per_person
        
        # Eşitlikte moderatör kararı için kontrol
        tied_choices = []
        needs_moderator_decision = False
        if best_choice and poll_stats:
            max_votes = best_choice['votes']
            tied_choices = [choice for choice in poll_stats.values() if choice['votes'] == max_votes and max_votes > 0]
            needs_moderator_decision = len(tied_choices) > 1
        
        return jsonify({
            'status': 'success',
            'data': {
                'event': dict(event),
                'slots': slot_stats,
                'best_slot': best_slot,
                'poll_choices': poll_stats,
                'best_choice': best_choice,
                'tied_choices': tied_choices,
                'needs_moderator_decision': needs_moderator_decision,
                'expenses': [dict(exp) for exp in summary['expenses']],
                'total_expense': total_expense,
                'participant_count': participant_count,
                'average_per_person': average_per_person,
                'balances': balances
            }
        })
        
    except Exception as e:
        logger.error(f"Özet API hatası: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Özet oluşturulurken hata oluştu'}), 500

@app.route('/events/<int:event_id>/remind', methods=['POST'])
def send_reminder_api(event_id):
    """Hatırlatıcı gönderir - POST /events/{id}/remind"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'Geçersiz JSON verisi'}), 400
        
        # Gerekli alanları kontrol et
        is_valid, error_msg = validate_input(data, ['message'])
        if not is_valid:
            return jsonify({'status': 'error', 'message': error_msg}), 400
        
        message = data.get('message', '').strip()
        delay = data.get('delay', 0)  # Saniye cinsinden gecikme
        
        # Etkinliğin var olup olmadığını kontrol et
        event = db.get_event_by_id(event_id)
        if not event:
            return jsonify({'status': 'error', 'message': 'Etkinlik bulunamadı'}), 404
        
        # Hatırlatıcı gönder
        if delay > 0:
            # Gecikmeli hatırlatıcı
            Timer(delay, lambda: send_bip_message(event['group_id'], message)).start()
            response_message = f'Hatırlatıcı {delay} saniye sonra gönderilecek'
        else:
            # Anında hatırlatıcı
            send_bip_message(event['group_id'], message)
            response_message = 'Hatırlatıcı gönderildi'
        
        return jsonify({
            'status': 'success',
            'message': response_message,
            'data': {
                'event_id': event_id,
                'group_id': event['group_id'],
                'message': message,
                'delay': delay
            }
        })
        
    except Exception as e:
        logger.error(f"Hatırlatıcı API hatası: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Hatırlatıcı gönderilirken hata oluştu'}), 500

# ==================== Utility Endpoints ====================

@app.route('/events/<int:event_id>/invite', methods=['GET'])
def generate_invite_link(event_id):
    """Etkinlik için davet linki oluşturur"""
    try:
        event = db.get_event_by_id(event_id)
        if not event:
            return jsonify({'status': 'error', 'message': 'Etkinlik bulunamadı'}), 404
        
        # Davet linki oluştur
        invite_link = f"http://localhost:5000/join/{event_id}"
        
        # QR kod için URL (mock)
        qr_code_url = f"http://localhost:5000/qr/{event_id}"
        
        return jsonify({
            'status': 'success',
            'message': 'Davet linki oluşturuldu',
            'data': {
                'event_id': event_id,
                'event_title': event['title'],
                'invite_link': invite_link,
                'qr_code_url': qr_code_url,
                'short_code': f"JOIN{event_id:04d}"
            }
        })
    except Exception as e:
        logger.error(f"Davet linki oluşturma hatası: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Davet linki oluşturulamadı'}), 500

@app.route('/join/<int:event_id>', methods=['GET'])
def join_event_page(event_id):
    """Etkinliğe katılma sayfası"""
    try:
        event = db.get_event_by_id(event_id)
        if not event:
            return f"<h1>Etkinlik bulunamadı!</h1>", 404
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Etkinliğe Katıl - {event['title']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .container {{ max-width: 600px; margin: 0 auto; }}
                .event-info {{ background: #f5f5f5; padding: 20px; border-radius: 10px; margin: 20px 0; }}
                .join-btn {{ background: #007bff; color: white; padding: 15px 30px; border: none; border-radius: 5px; font-size: 18px; cursor: pointer; }}
                .join-btn:hover {{ background: #0056b3; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎉 Etkinliğe Katıl</h1>
                <div class="event-info">
                    <h2>{event['title']}</h2>
                    <p><strong>Oluşturan:</strong> {event['created_by']}</p>
                    <p><strong>Grup ID:</strong> {event['group_id']}</p>
                    <p><strong>Oluşturma Tarihi:</strong> {event['created_at']}</p>
                </div>
                <button class="join-btn" onclick="joinEvent()">Etkinliğe Katıl</button>
                <p><small>Bu sayfayı BiP grubunda paylaşabilirsiniz</small></p>
            </div>
            
            <script>
                function joinEvent() {{
                    alert('Etkinliğe katıldınız! BiP grubunda devam edin.');
                    window.close();
                }}
            </script>
        </body>
        </html>
        """
        
        return html_content
    except Exception as e:
        logger.error(f"Katılma sayfası hatası: {str(e)}")
        return f"<h1>Hata oluştu!</h1>", 500

@app.route('/events/<int:event_id>/analytics', methods=['GET'])
def get_event_analytics(event_id):
    """Etkinlik analitik verilerini döndürür"""
    try:
        event = db.get_event_by_id(event_id)
        if not event:
            return jsonify({'status': 'error', 'message': 'Etkinlik bulunamadı'}), 404
        
        # Gerçek analitik veriler
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Katılımcı sayısı
            cursor.execute('''
                SELECT COUNT(DISTINCT user_id) as participant_count
                FROM (
                    SELECT user_id FROM slot_votes WHERE event_id = ?
                    UNION
                    SELECT user_id FROM poll_votes WHERE poll_id IN (
                        SELECT poll_id FROM polls WHERE event_id = ?
                    )
                    UNION
                    SELECT user_id FROM expenses WHERE event_id = ?
                )
            ''', (event_id, event_id, event_id))
            participant_count = cursor.fetchone()['participant_count']
            
            # Slot sayısı
            cursor.execute('SELECT COUNT(*) as slot_count FROM slots WHERE event_id = ?', (event_id,))
            total_slots = cursor.fetchone()['slot_count']
            
            # Toplam oy sayısı
            cursor.execute('SELECT COUNT(*) as vote_count FROM slot_votes WHERE event_id = ?', (event_id,))
            slot_votes = cursor.fetchone()['vote_count']
            
            cursor.execute('''
                SELECT COUNT(*) as vote_count FROM poll_votes 
                WHERE poll_id IN (SELECT poll_id FROM polls WHERE event_id = ?)
            ''', (event_id,))
            poll_votes = cursor.fetchone()['vote_count']
            total_votes = slot_votes + poll_votes
            
            # Gider analizi
            cursor.execute('SELECT COUNT(*) as expense_count, SUM(amount) as total_expense FROM expenses WHERE event_id = ?', (event_id,))
            expense_data = cursor.fetchone()
            expense_count = expense_data['expense_count'] or 0
            total_expense = expense_data['total_expense'] or 0
            
            # En aktif kullanıcı (gider sayısına göre)
            cursor.execute('''
                SELECT user_id, COUNT(*) as expense_count 
                FROM expenses 
                WHERE event_id = ? 
                GROUP BY user_id 
                ORDER BY expense_count DESC 
                LIMIT 1
            ''', (event_id,))
            most_active = cursor.fetchone()
            most_active_user = most_active['user_id'] if most_active else 'Yok'
            most_active_expenses = most_active['expense_count'] if most_active else 0
            
            # Katılım oranı (tüm potansiyel kullanıcılara göre)
            cursor.execute('SELECT COUNT(*) as total_users FROM users')
            total_users = cursor.fetchone()['total_users']
            participation_rate = (participant_count / total_users * 100) if total_users > 0 else 0
            
            avg_expense_per_person = total_expense / participant_count if participant_count > 0 else 0
        
        analytics = {
            'event_id': event_id,
            'event_title': event['title'],
            'participation_rate': round(participation_rate, 1),
            'total_participants': participant_count,
            'total_slots': total_slots,
            'total_votes': total_votes,
            'total_expense': total_expense,
            'avg_expense_per_person': round(avg_expense_per_person, 2),
            'most_active_user': most_active_user,
            'most_active_user_expenses': most_active_expenses,
            'expense_count': expense_count,
            'best_slot_votes': 0,  # Bu veri summary'den alınacak
            'best_place_votes': 0  # Bu veri summary'den alınacak
        }
        
        return jsonify({
            'status': 'success',
            'message': 'Analitik veriler alındı',
            'data': analytics
        })
    except Exception as e:
        logger.error(f"Analitik veri hatası: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Analitik veriler alınamadı: {str(e)}'}), 500

@app.route('/events/<int:event_id>/location/<int:choice_id>', methods=['GET'])
def get_location_info(event_id, choice_id):
    """Mekan için konum bilgilerini döndürür"""
    try:
        event = db.get_event_by_id(event_id)
        if not event:
            return jsonify({'status': 'error', 'message': 'Etkinlik bulunamadı'}), 404
        
        # Mekan bilgilerini al
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT choice_id, text, latitude, longitude, created_at
                FROM poll_choices 
                WHERE choice_id = ? AND poll_id IN (
                    SELECT poll_id FROM polls WHERE event_id = ?
                )
            ''', (choice_id, event_id))
            choice = cursor.fetchone()
        
        if not choice:
            return jsonify({'status': 'error', 'message': 'Mekan bulunamadı'}), 404
        
        # Mock konum verileri (gerçek uygulamada Google Maps API kullanılır)
        mock_locations = {
            'Pizza Palace': {'lat': 41.0082, 'lng': 28.9784, 'address': 'Beşiktaş, İstanbul'},
            'Ek Bina Kafe': {'lat': 41.0151, 'lng': 28.9847, 'address': 'Şişli, İstanbul'},
            'Kütüphane': {'lat': 41.0128, 'lng': 28.9753, 'address': 'Beyoğlu, İstanbul'},
            'Kampüs Kafe': {'lat': 41.0089, 'lng': 28.9821, 'address': 'Beşiktaş, İstanbul'}
        }
        
        location_data = mock_locations.get(choice['text'], {
            'lat': 41.0082, 
            'lng': 28.9784, 
            'address': f"{choice['text']}, İstanbul"
        })
        
        # Eğer veritabanında konum varsa onu kullan
        if choice['latitude'] and choice['longitude']:
            location_data = {
                'lat': choice['latitude'],
                'lng': choice['longitude'],
                'address': choice.get('address', f"{choice['text']}, İstanbul")
            }
        
        location_info = {
            'choice_id': choice_id,
            'place_name': choice['text'],
            'latitude': location_data['lat'],
            'longitude': location_data['lng'],
            'address': location_data['address'],
            'google_maps_url': f"https://maps.google.com/?q={location_data['lat']},{location_data['lng']}",
            'distance_from_center': '2.5 km'  # Mock mesafe
        }
        
        return jsonify({
            'status': 'success',
            'message': 'Konum bilgileri alındı',
            'data': location_info
        })
    except Exception as e:
        logger.error(f"Konum bilgisi hatası: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Konum bilgileri alınamadı'}), 500

@app.route('/events/<int:event_id>/poll/choices', methods=['POST'])
def add_poll_choice(event_id):
    """Mevcut anket'e seçenek ekler"""
    try:
        data = request.json
        if not data:
            return jsonify({'status': 'error', 'message': 'Geçersiz JSON verisi'}), 400
        
        # Gerekli alanları kontrol et
        is_valid, error_msg = validate_input(data, ['text'])
        if not is_valid:
            return jsonify({'status': 'error', 'message': error_msg}), 400
        
        text = data.get('text', '').strip()
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        # Etkinliğin var olup olmadığını kontrol et
        event = db.get_event_by_id(event_id)
        if not event:
            return jsonify({'status': 'error', 'message': 'Etkinlik bulunamadı'}), 404
        
        # Etkinlik için mevcut anketi bul
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT poll_id FROM polls WHERE event_id = ?', (event_id,))
            poll = cursor.fetchone()
            
            if not poll:
                # Anket yoksa oluştur
                cursor.execute('''
                    INSERT INTO polls (event_id, question)
                    VALUES (?, ?)
                ''', (event_id, 'Mekan Seçimi'))
                poll_id = cursor.lastrowid
            else:
                poll_id = poll['poll_id']
            
            # Seçeneği ekle (konum bilgisi ile)
            cursor.execute('''
                INSERT INTO poll_choices (poll_id, text, latitude, longitude)
                VALUES (?, ?, ?, ?)
            ''', (poll_id, text, latitude, longitude))
            choice_id = cursor.lastrowid
            conn.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Mekan eklendi: {text}',
            'choice_id': choice_id,
            'data': {
                'choice_id': choice_id,
                'poll_id': poll_id,
                'text': text,
                'latitude': latitude,
                'longitude': longitude
            }
        })
    except Exception as e:
        logger.error(f"Mekan ekleme API hatası: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Mekan eklenirken hata oluştu'}), 500

@app.route('/api', methods=['GET'])
def api_info():
    """API endpoint bilgilerini döndürür"""
    endpoints = {
        'events': {
            'POST /events': 'Yeni etkinlik oluştur',
            'POST /events/{id}/slots': 'Etkinliğe slot ekle',
            'POST /events/{id}/vote-slot': 'Slot için oy ver',
            'POST /events/{id}/poll': 'Anket oluştur',
            'POST /events/{id}/vote': 'Anket için oy ver',
            'POST /events/{id}/expense': 'Gider ekle',
            'GET /events/{id}/summary': 'Etkinlik özeti al',
            'POST /events/{id}/remind': 'Hatırlatıcı gönder'
        },
        'utility': {
            'GET /health': 'Sağlık kontrolü',
            'GET /api': 'API bilgileri',
            'POST /webhook/bip': 'BiP webhook (legacy)'
        }
    }
    
    return jsonify({
        'status': 'success',
        'message': 'BiP Bot RESTful API v3.0',
        'version': '3.0.0',
        'base_url': request.base_url.rstrip('/'),
        'endpoints': endpoints,
        'documentation': 'API_DOCUMENTATION.md dosyasına bakın'
    })

@app.route('/api/events', methods=['GET'])
def get_all_events():
    """Tüm etkinlikleri listeler"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    e.event_id,
                    e.title,
                    e.created_at,
                    e.status,
                    COUNT(DISTINCT sv.user_id) as participant_count
                FROM events e
                LEFT JOIN slot_votes sv ON e.event_id = sv.event_id
                WHERE e.status = 'active'
                GROUP BY e.event_id, e.title, e.created_at, e.status
                ORDER BY e.created_at DESC
            ''')
            
            events = []
            for row in cursor.fetchall():
                events.append({
                    'event_id': row['event_id'],
                    'title': row['title'],
                    'created_at': row['created_at'],
                    'status': row['status'],
                    'participant_count': row['participant_count']
                })
            
            return jsonify({
                'status': 'success',
                'message': f'{len(events)} etkinlik bulundu',
                'events': events
            })
            
    except Exception as e:
        logger.error(f"Etkinlik listesi API hatası: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Etkinlik listesi alınamadı'}), 500

@app.route('/events/<int:event_id>/slots/<int:slot_id>/close', methods=['POST'])
def close_slot_api(event_id, slot_id):
    """Slot'u kapatır"""
    try:
        data = request.json or {}
        user_id = data.get('user_id', '')
        
        # Etkinliğin var olup olmadığını kontrol et
        event = db.get_event_by_id(event_id)
        if not event:
            return jsonify({'status': 'error', 'message': 'Etkinlik bulunamadı'}), 404
        
        # Slot'un var olup olmadığını ve yetki kontrolü
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT s.slot_id, s.event_id, s.status, s.created_by
                FROM slots s
                WHERE s.slot_id = ? AND s.event_id = ?
            ''', (slot_id, event_id))
            slot = cursor.fetchone()
            
            if not slot:
                return jsonify({'status': 'error', 'message': 'Slot bulunamadı'}), 404
            
            # Yetki kontrolü: Herkes kapatabilir (geçici olarak gevşetildi)
            # if slot['created_by'] != user_id and event['created_by'] != user_id:
            #     return jsonify({'status': 'error', 'message': 'Bu slot\'u kapatma yetkiniz yok'}), 403
            
            # Slot'u kapat
            cursor.execute('''
                UPDATE slots 
                SET status = 'closed' 
                WHERE slot_id = ? AND event_id = ?
            ''', (slot_id, event_id))
            conn.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Slot {slot_id} kapatıldı',
            'data': {
                'event_id': event_id,
                'slot_id': slot_id,
                'status': 'closed'
            }
        })
        
    except Exception as e:
        logger.error(f"Slot kapatma API hatası: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Slot kapatılırken hata oluştu'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Sağlık kontrolü endpoint'i"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/', methods=['GET'])
def frontend_page():
    """Ana frontend sayfası"""
    try:
        with open('frontend.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Frontend dosyası bulunamadı!", 404

@app.route('/invite.png', methods=['GET'])
def serve_invite_qr():
    """QR kod resmini serve eder"""
    try:
        from flask import send_file
        return send_file('invite.png', mimetype='image/png')
    except FileNotFoundError:
        return "QR kod dosyası bulunamadı!", 404

@app.route('/invite', methods=['GET'])
def invite_page():
    """Davet sayfası"""
    return """
    <html>
    <head>
        <title>BiP Bot - SQLite</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
            .container { max-width: 500px; margin: 0 auto; }
            .qr-code { margin: 20px 0; }
            .instructions { text-align: left; margin: 20px 0; }
            .command { background: #f0f0f0; padding: 5px; margin: 5px 0; }
            .db-info { background: #e8f5e8; padding: 10px; border-radius: 5px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 BiP Bot - SQLite</h1>
            <p>Etkinlik yönetimi için BiP bot'u kullanın!</p>
            
            <div class="db-info">
                <strong>📊 SQLite Veritabanı Aktif</strong><br>
                Tüm veriler güvenli şekilde saklanıyor.
            </div>
            
            <div class="qr-code">
                <img src="invite.png" alt="QR Code" style="max-width: 200px;">
            </div>
            
            <div class="instructions">
                <h3>Kullanılabilir Komutlar:</h3>
                <div class="command"><strong>/yeni ETKİNLİK_ADI</strong> - Yeni etkinlik oluştur</div>
                <div class="command"><strong>/slot YYYY-MM-DD HH:MM-HH:MM</strong> - Tarih/saat seçeneği ekle</div>
                <div class="command"><strong>/katil slot=1 yes/no</strong> - Slot için katılım oyu ver</div>
                <div class="command"><strong>/mekan MEKAN_ADI [enlem boylam]</strong> - Mekan önerisi ekle</div>
                <div class="command"><strong>/oy_mekan CHOICE_ID</strong> - Mekan için oy ver</div>
                <div class="command"><strong>/gider TUTAR "Açıklama" [ağırlık]</strong> - Gider ekle</div>
                <div class="command"><strong>/slot_kapat SLOT_ID</strong> - Slot kapat (moderatör)</div>
                <div class="command"><strong>/ozet</strong> - Etkinlik özetini göster</div>
                <div class="command"><strong>/test</strong> - Bot testi</div>
            </div>
        </div>
    </body>
    </html>
    """

if __name__ == '__main__':
    # Production için port ve host ayarları
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    logger.info(f"BiP Bot (SQLite) başlatılıyor - Port: {port}, Debug: {debug}")
    app.run(debug=debug, port=port, host='0.0.0.0')

