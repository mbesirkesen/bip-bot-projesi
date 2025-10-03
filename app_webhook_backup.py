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

# Mesajı API yanıtına eklemek için global değişken
last_bip_message = ""

def send_bip_message(group_id, message):
    """BiP mesajı gönderir (mock)"""
    global last_bip_message
    last_bip_message = f"[MOCK BiP GRUP {group_id}] {message}"
    logger.info(f"BiP mesajı gönderildi: {message}")
    print(last_bip_message)

def remind(event_id, group_id, delay):
    """Hatırlatıcı zamanlayıcısı başlatır"""
    def send_reminder():
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

        logger.info(f"Webhook alındı - Kullanıcı: {user_id}, Grup: {group_id}, Mesaj: {message}")

        if not check_rate_limit(user_id):
            send_bip_message(group_id, "Lutfen komutlar arasinda 2 sn bekleyin.")
            return jsonify({'status': 'rate_limited'})

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

        # Slot kapatma (moderatör)
        elif message.startswith('/slot_kapat'):
            parts = message.split()
            if len(parts) < 2:
                response_msg = "Kullanim: /slot_kapat SLOT_ID"
            else:
                try:
                    slot_id = int(parts[1])
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
                    response_msg = "Slot kapatilirken hata olustu."

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

@app.route('/health', methods=['GET'])
def health_check():
    """Sağlık kontrolü endpoint'i"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

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

