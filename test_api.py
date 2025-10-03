#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 BiP Bot API Test Script
Tüm RESTful API endpoint'lerini test eder
"""

import requests
import json
import time
from datetime import datetime, timedelta

# API base URL
BASE_URL = "http://localhost:5000"

def test_api():
    """API endpoint'lerini test eder"""
    print("BiP Bot API Test Baslatiliyor...\n")
    
    # Test verileri
    user_id = "test_user_123"
    group_id = "test_group_456"
    event_title = "Test Etkinliği"
    
    # 1. Etkinlik oluştur
    print("1. Etkinlik olusturuluyor...")
    response = requests.post(f"{BASE_URL}/events", json={
        "title": event_title,
        "created_by": user_id,
        "group_id": group_id
    })
    
    if response.status_code == 200:
        data = response.json()
        event_id = data['event_id']
        print(f"[OK] Etkinlik olusturuldu: ID {event_id}")
    else:
        print(f"[ERROR] Etkinlik olusturulamadi: {response.text}")
        return
    
    # 2. Slot ekle
    print("\n2. Slot ekleniyor...")
    start_time = (datetime.now() + timedelta(days=1)).isoformat()
    end_time = (datetime.now() + timedelta(days=1, hours=2)).isoformat()
    
    response = requests.post(f"{BASE_URL}/events/{event_id}/slots", json={
        "start_datetime": start_time,
        "end_datetime": end_time
    })
    
    if response.status_code == 200:
        data = response.json()
        slot_id = data['slot_id']
        print(f"[OK] Slot eklendi: ID {slot_id}")
    else:
        print(f"[ERROR] Slot eklenemedi: {response.text}")
        slot_id = 1  # Varsayılan slot ID
    
    # 3. Slot için oy ver
    print("\n3. Slot için oy veriliyor...")
    response = requests.post(f"{BASE_URL}/events/{event_id}/vote-slot", json={
        "user_id": user_id,
        "slot_id": slot_id,
        "choice": "yes"
    })
    
    if response.status_code == 200:
        print("[OK] Slot oyu verildi")
    else:
        print(f"[ERROR] Slot oyu verilemedi: {response.text}")
    
    # 4. Anket oluştur
    print("\n4. Anket olusturuluyor...")
    response = requests.post(f"{BASE_URL}/events/{event_id}/poll", json={
        "question": "En iyi mekan hangisi?"
    })
    
    if response.status_code == 200:
        data = response.json()
        poll_id = data['poll_id']
        print(f"[OK] Anket olusturuldu: ID {poll_id}")
    else:
        print(f"[ERROR] Anket olusturulamadi: {response.text}")
    
    # 5. Gider ekle
    print("\n5. Gider ekleniyor...")
    response = requests.post(f"{BASE_URL}/events/{event_id}/expense", json={
        "user_id": user_id,
        "amount": 150.50,
        "description": "Pizza ve icecek",
        "slot_id": slot_id,
        "weight": 1.0
    })
    
    if response.status_code == 200:
        data = response.json()
        expense_id = data['expense_id']
        print(f"[OK] Gider eklendi: ID {expense_id}")
    else:
        print(f"[ERROR] Gider eklenemedi: {response.text}")
    
    # 6. Etkinlik özeti al
    print("\n6. Etkinlik ozeti aliniyor...")
    response = requests.get(f"{BASE_URL}/events/{event_id}/summary")
    
    if response.status_code == 200:
        data = response.json()
        summary = data['data']
        print(f"[OK] Ozet alindi:")
        print(f"   - Etkinlik: {summary['event']['title']}")
        print(f"   - Toplam gider: {summary['total_expense']} TL")
        print(f"   - Katilimci: {summary['participant_count']} kisi")
    else:
        print(f"[ERROR] Ozet alinamadi: {response.text}")
    
    # 7. Hatırlatıcı gönder
    print("\n7. Hatirlatici gonderiliyor...")
    response = requests.post(f"{BASE_URL}/events/{event_id}/remind", json={
        "message": "Test hatirlaticisi!",
        "delay": 5  # 5 saniye sonra
    })
    
    if response.status_code == 200:
        print("[OK] Hatirlatici gonderildi")
    else:
        print(f"[ERROR] Hatirlatici gonderilemedi: {response.text}")
    
    # 8. Health check
    print("\n8. Health check...")
    response = requests.get(f"{BASE_URL}/health")
    
    if response.status_code == 200:
        data = response.json()
        print(f"[OK] API saglikli: {data['timestamp']}")
    else:
        print(f"[ERROR] Health check basarisiz: {response.text}")
    
    print("\n[SUCCESS] API testleri tamamlandi!")
    print(f"[INFO] Test edilen etkinlik ID: {event_id}")

if __name__ == "__main__":
    try:
        test_api()
    except requests.exceptions.ConnectionError:
        print("[ERROR] Baglanti hatasi: API sunucusu calismiyor olabilir.")
        print("[INFO] Once 'python app.py' ile sunucuyu baslatin.")
    except Exception as e:
        print(f"[ERROR] Test hatasi: {str(e)}")
