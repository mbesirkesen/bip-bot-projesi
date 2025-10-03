#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Veritabanını test verileri ile doldurur
"""

import sqlite3
from datetime import datetime, timezone, timedelta
import random

def populate_database():
    """Veritabanını test verileri ile doldurur"""
    
    # Veritabanına bağlan
    conn = sqlite3.connect('bip_bot.db')
    cursor = conn.cursor()
    
    try:
        print("Veritabani dolduruluyor...")
        
        # 1. Etkinlik oluştur
        cursor.execute('''
            INSERT INTO events (title, group_id, created_by, status)
            VALUES (?, ?, ?, ?)
        ''', ('Kampus Etut Gecesi', 'group_etut_123', 'moderator_ali', 'active'))
        event_id = cursor.lastrowid
        print(f"Etkinlik olusturuldu: ID {event_id}")
        
        # 2. Kullanıcılar ekle
        users = [
            ('user_ali', 'Ali Yılmaz', 'user'),
            ('user_ayse', 'Ayşe Demir', 'user'),
            ('user_mehmet', 'Mehmet Kaya', 'user'),
            ('user_fatma', 'Fatma Öz', 'user'),
            ('user_ahmet', 'Ahmet Çelik', 'user'),
            ('user_zeynep', 'Zeynep Şahin', 'user'),
            ('user_can', 'Can Öztürk', 'user'),
            ('user_elif', 'Elif Arslan', 'user'),
            ('moderator_ali', 'Ali Moderator', 'moderator')
        ]
        
        for user_id, name, role in users:
            cursor.execute('''
                INSERT OR REPLACE INTO users (user_id, name, role)
                VALUES (?, ?, ?)
            ''', (user_id, name, role))
        print(f"{len(users)} kullanici eklendi")
        
        # 3. Slotlar ekle
        slots = [
            ('2025-10-15T18:00:00+00:00', '2025-10-15T21:00:00+00:00'),
            ('2025-10-16T18:00:00+00:00', '2025-10-16T21:00:00+00:00'),
            ('2025-10-17T18:00:00+00:00', '2025-10-17T21:00:00+00:00'),
            ('2025-10-18T14:00:00+00:00', '2025-10-18T17:00:00+00:00'),
            ('2025-10-19T18:00:00+00:00', '2025-10-19T21:00:00+00:00')
        ]
        
        slot_ids = []
        for start, end in slots:
            cursor.execute('''
                INSERT INTO slots (event_id, start_datetime, end_datetime, status)
                VALUES (?, ?, ?, ?)
            ''', (event_id, start, end, 'active'))
            slot_ids.append(cursor.lastrowid)
        print(f"{len(slots)} slot eklendi")
        
        # 4. Mekanlar için anket oluştur
        cursor.execute('''
            INSERT INTO polls (event_id, question)
            VALUES (?, ?)
        ''', (event_id, 'En uygun etut mekani hangisi?'))
        poll_id = cursor.lastrowid
        print(f"Anket olusturuldu: ID {poll_id}")
        
        # 5. Mekan seçenekleri ekle
        places = [
            'Merkez Kutuphane',
            'Muhendislik Fakultesi Kafe',
            'Fen Fakultesi Laboratuvari',
            'Ogrenci Merkezi',
            'Kampus Kafeterya'
        ]
        
        choice_ids = []
        for place in places:
            cursor.execute('''
                INSERT INTO poll_choices (poll_id, text, votes)
                VALUES (?, ?, ?)
            ''', (poll_id, place, 0))
            choice_ids.append(cursor.lastrowid)
        print(f"{len(places)} mekan secenegi eklendi")
        
        # 6. Slot oyları ekle (her kullanıcı bir slot'a oy verir)
        slot_votes = [
            ('user_ali', 0),      # Slot 1
            ('user_ayse', 0),     # Slot 1
            ('user_mehmet', 1),   # Slot 2
            ('user_fatma', 1),    # Slot 2
            ('user_ahmet', 1),    # Slot 2
            ('user_zeynep', 2),   # Slot 3
            ('user_can', 2),      # Slot 3
            ('user_elif', 3),     # Slot 4
            ('moderator_ali', 4)  # Slot 5
        ]
        
        for user_id, slot_index in slot_votes:
            slot_id = slot_ids[slot_index]
            cursor.execute('''
                INSERT INTO slot_votes (event_id, slot_id, user_id, choice)
                VALUES (?, ?, ?, ?)
            ''', (event_id, slot_id, user_id, 'yes'))
        print(f"{len(slot_votes)} slot oyu eklendi")
        
        # 7. Mekan oyları ekle (her kullanıcı bir mekan'a oy verir)
        place_votes = [
            ('user_ali', 0),      # Merkez Kütüphane
            ('user_ayse', 0),     # Merkez Kütüphane
            ('user_mehmet', 0),   # Merkez Kütüphane
            ('user_fatma', 1),    # Mühendislik Fakültesi Kafe
            ('user_ahmet', 1),    # Mühendislik Fakültesi Kafe
            ('user_zeynep', 2),   # Fen Fakültesi Laboratuvarı
            ('user_can', 3),      # Öğrenci Merkezi
            ('user_elif', 3),     # Öğrenci Merkezi
            ('moderator_ali', 4)  # Kampüs Kafeterya
        ]
        
        for user_id, choice_index in place_votes:
            choice_id = choice_ids[choice_index]
            cursor.execute('''
                INSERT INTO poll_votes (poll_id, choice_id, user_id)
                VALUES (?, ?, ?)
            ''', (poll_id, choice_id, user_id))
            
            # Oy sayısını güncelle
            cursor.execute('''
                UPDATE poll_choices 
                SET votes = votes + 1 
                WHERE choice_id = ?
            ''', (choice_id,))
        print(f"{len(place_votes)} mekan oyu eklendi")
        
        # 8. Giderler ekle
        expenses = [
            ('user_ali', 150.0, 'Kahve ve cay', 1.0),
            ('user_ayse', 200.0, 'Atistirmalik ve meyve suyu', 1.0),
            ('user_mehmet', 100.0, 'Not kagidi ve kalem', 1.0),
            ('user_fatma', 300.0, 'Pizza siparisi', 1.0),
            ('user_ahmet', 250.0, 'Sandvic ve icecek', 1.0),
            ('user_zeynep', 180.0, 'Kek ve kurabiye', 1.0),
            ('user_can', 120.0, 'Cay ve kahve', 1.0),
            ('user_elif', 350.0, 'Ana yemek siparisi', 1.0)
        ]
        
        for user_id, amount, notes, weight in expenses:
            cursor.execute('''
                INSERT INTO expenses (event_id, user_id, amount, notes, weight)
                VALUES (?, ?, ?, ?, ?)
            ''', (event_id, user_id, amount, notes, weight))
        print(f"{len(expenses)} gider eklendi")
        
        # Değişiklikleri kaydet
        conn.commit()
        print(f"\nVeritabani basariyla dolduruldu!")
        print(f"Ozet:")
        print(f"   • Etkinlik: {event_id}")
        print(f"   • Kullanici: {len(users)}")
        print(f"   • Slot: {len(slots)}")
        print(f"   • Mekan: {len(places)}")
        print(f"   • Slot Oyu: {len(slot_votes)}")
        print(f"   • Mekan Oyu: {len(place_votes)}")
        print(f"   • Gider: {len(expenses)}")
        
    except Exception as e:
        print(f"Hata: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    populate_database()
