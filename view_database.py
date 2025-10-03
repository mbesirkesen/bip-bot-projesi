#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 SQLite Veritabanı Görüntüleyici
BiP Bot veritabanındaki tüm verileri gösterir
"""

import sqlite3
from datetime import datetime

def view_database():
    """Veritabanındaki tüm verileri gösterir"""
    print("=" * 60)
    print("BiP Bot SQLite Veritabani Icerigi")
    print("=" * 60)
    
    try:
        # Veritabanına bağlan
        conn = sqlite3.connect('bip_bot.db')
        conn.row_factory = sqlite3.Row  # Dict-like access
        cursor = conn.cursor()
        
        # 1. Events tablosu
        print("\nETKINLIKLER (Events)")
        print("-" * 40)
        cursor.execute('SELECT * FROM events ORDER BY created_at DESC')
        events = cursor.fetchall()
        
        if events:
            for event in events:
                print(f"ID: {event['event_id']}")
                print(f"Başlık: {event['title']}")
                print(f"Oluşturan: {event['created_by']}")
                print(f"Grup ID: {event['group_id']}")
                print(f"Tarih: {event['created_at']}")
                print(f"Durum: {event['status']}")
                print("-" * 20)
        else:
            print("Henüz etkinlik yok.")
        
        # 2. Slots tablosu
        print("\nSLOTLAR (Slots)")
        print("-" * 40)
        cursor.execute('SELECT * FROM slots ORDER BY start_datetime')
        slots = cursor.fetchall()
        
        if slots:
            for slot in slots:
                print(f"ID: {slot['slot_id']}")
                print(f"Etkinlik ID: {slot['event_id']}")
                print(f"Başlangıç: {slot['start_datetime']}")
                print(f"Bitiş: {slot['end_datetime']}")
                print(f"Durum: {slot['status']}")
                print("-" * 20)
        else:
            print("Henüz slot yok.")
        
        # 3. Slot Votes tablosu
        print("\nSLOT OYLARI (Slot Votes)")
        print("-" * 40)
        cursor.execute('SELECT * FROM slot_votes ORDER BY created_at DESC')
        slot_votes = cursor.fetchall()
        
        if slot_votes:
            for vote in slot_votes:
                print(f"Etkinlik ID: {vote['event_id']}")
                print(f"Slot ID: {vote['slot_id']}")
                print(f"Kullanıcı: {vote['user_id']}")
                print(f"Oy: {vote['choice']}")
                print(f"Tarih: {vote['created_at']}")
                print("-" * 20)
        else:
            print("Henüz slot oyu yok.")
        
        # 4. Polls tablosu
        print("\nANKETLER (Polls)")
        print("-" * 40)
        cursor.execute('SELECT * FROM polls ORDER BY created_at DESC')
        polls = cursor.fetchall()
        
        if polls:
            for poll in polls:
                print(f"ID: {poll['poll_id']}")
                print(f"Etkinlik ID: {poll['event_id']}")
                print(f"Soru: {poll['question']}")
                print(f"Tarih: {poll['created_at']}")
                print(f"Durum: {poll['status']}")
                print("-" * 20)
        else:
            print("Henüz anket yok.")
        
        # 5. Poll Choices tablosu
        print("\nANKET SECENEKLERI (Poll Choices)")
        print("-" * 40)
        cursor.execute('SELECT * FROM poll_choices ORDER BY choice_id')
        choices = cursor.fetchall()
        
        if choices:
            for choice in choices:
                print(f"ID: {choice['choice_id']}")
                print(f"Anket ID: {choice['poll_id']}")
                print(f"Metin: {choice['text']}")
                print(f"Enlem: {choice['latitude']}")
                print(f"Boylam: {choice['longitude']}")
                print(f"Tarih: {choice['created_at']}")
                print("-" * 20)
        else:
            print("Henüz anket seçeneği yok.")
        
        # 6. Poll Votes tablosu
        print("\nANKET OYLARI (Poll Votes)")
        print("-" * 40)
        cursor.execute('SELECT * FROM poll_votes ORDER BY created_at DESC')
        poll_votes = cursor.fetchall()
        
        if poll_votes:
            for vote in poll_votes:
                print(f"Anket ID: {vote['poll_id']}")
                print(f"Seçenek ID: {vote['choice_id']}")
                print(f"Kullanıcı: {vote['user_id']}")
                print(f"Tarih: {vote['created_at']}")
                print("-" * 20)
        else:
            print("Henüz anket oyu yok.")
        
        # 7. Expenses tablosu
        print("\nGIDERLER (Expenses)")
        print("-" * 40)
        cursor.execute('SELECT * FROM expenses ORDER BY created_at DESC')
        expenses = cursor.fetchall()
        
        if expenses:
            for expense in expenses:
                print(f"ID: {expense['expense_id']}")
                print(f"Etkinlik ID: {expense['event_id']}")
                print(f"Kullanıcı: {expense['user_id']}")
                print(f"Tutar: {expense['amount']} TL")
                print(f"Not: {expense['notes']}")
                print(f"Ağırlık: {expense['weight']}")
                print(f"Tarih: {expense['created_at']}")
                print("-" * 20)
        else:
            print("Henüz gider yok.")
        
        # 8. Users tablosu
        print("\nKULLANICILAR (Users)")
        print("-" * 40)
        cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
        users = cursor.fetchall()
        
        if users:
            for user in users:
                print(f"ID: {user['user_id']}")
                print(f"Ad: {user['name']}")
                print(f"Rol: {user['role']}")
                print(f"Oluşturulma: {user['created_at']}")
                print(f"Son Aktif: {user['last_active']}")
                print("-" * 20)
        else:
            print("Henüz kullanıcı yok.")
        
        # Özet istatistikler
        print("\nOZET ISTATISTIKLER")
        print("-" * 40)
        
        cursor.execute('SELECT COUNT(*) as count FROM events')
        event_count = cursor.fetchone()['count']
        print(f"Toplam Etkinlik: {event_count}")
        
        cursor.execute('SELECT COUNT(*) as count FROM slots')
        slot_count = cursor.fetchone()['count']
        print(f"Toplam Slot: {slot_count}")
        
        cursor.execute('SELECT COUNT(*) as count FROM slot_votes')
        slot_vote_count = cursor.fetchone()['count']
        print(f"Toplam Slot Oyu: {slot_vote_count}")
        
        cursor.execute('SELECT COUNT(*) as count FROM polls')
        poll_count = cursor.fetchone()['count']
        print(f"Toplam Anket: {poll_count}")
        
        cursor.execute('SELECT COUNT(*) as count FROM poll_votes')
        poll_vote_count = cursor.fetchone()['count']
        print(f"Toplam Anket Oyu: {poll_vote_count}")
        
        cursor.execute('SELECT COUNT(*) as count FROM expenses')
        expense_count = cursor.fetchone()['count']
        print(f"Toplam Gider: {expense_count}")
        
        cursor.execute('SELECT COUNT(*) as count FROM users')
        user_count = cursor.fetchone()['count']
        print(f"Toplam Kullanıcı: {user_count}")
        
        # Toplam gider
        cursor.execute('SELECT SUM(amount) as total FROM expenses')
        total_expense = cursor.fetchone()['total'] or 0
        print(f"Toplam Gider Tutarı: {total_expense} TL")
        
        conn.close()
        print("\n[SUCCESS] Veritabani incelemesi tamamlandi!")
        
    except Exception as e:
        print(f"[ERROR] Hata: {str(e)}")

if __name__ == "__main__":
    view_database()
