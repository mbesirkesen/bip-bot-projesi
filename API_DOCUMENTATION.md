# 🤖 BiP Bot RESTful API Dokümantasyonu

## Genel Bilgiler

BiP Bot RESTful API, etkinlik yönetimi için tasarlanmış modern bir API'dir. Tüm endpoint'ler JSON formatında veri alır ve döndürür.

**Base URL:** `http://localhost:5000`

## Endpoint'ler

### 1. Etkinlik Oluşturma
**POST** `/events`

Yeni bir etkinlik oluşturur.

**Request Body:**
```json
{
  "title": "Pizza Gecesi",
  "created_by": "user123",
  "group_id": "group456"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Etkinlik oluşturuldu: Pizza Gecesi",
  "event_id": 1,
  "data": {
    "event_id": 1,
    "title": "Pizza Gecesi",
    "created_by": "user123",
    "group_id": "group456"
  }
}
```

### 2. Slot Ekleme
**POST** `/events/{id}/slots`

Etkinliğe tarih/saat slotu ekler.

**Request Body:**
```json
{
  "start_datetime": "2025-10-12T18:00:00",
  "end_datetime": "2025-10-12T20:00:00"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Slot eklendi: 2025-10-12 18:00 - 20:00",
  "slot_id": 1,
  "data": {
    "slot_id": 1,
    "event_id": 1,
    "start_datetime": "2025-10-12T18:00:00",
    "end_datetime": "2025-10-12T20:00:00"
  }
}
```

### 3. Slot Oy Verme
**POST** `/events/{id}/vote-slot`

Slot için katılım oyu verir.

**Request Body:**
```json
{
  "user_id": "user123",
  "slot_id": 1,
  "choice": "yes"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Slot 1 için oy: yes",
  "data": {
    "event_id": 1,
    "slot_id": 1,
    "user_id": "user123",
    "choice": "yes"
  }
}
```

### 4. Anket Oluşturma
**POST** `/events/{id}/poll`

Etkinlik için anket oluşturur.

**Request Body:**
```json
{
  "question": "En iyi mekan hangisi?"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Anket oluşturuldu: En iyi mekan hangisi?",
  "poll_id": 1,
  "data": {
    "poll_id": 1,
    "event_id": 1,
    "question": "En iyi mekan hangisi?"
  }
}
```

### 5. Anket Oy Verme
**POST** `/events/{id}/vote`

Anket için oy verir.

**Request Body:**
```json
{
  "user_id": "user123",
  "choice_id": 1
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Anket için oy verildi: 1",
  "data": {
    "event_id": 1,
    "poll_id": 1,
    "choice_id": 1,
    "user_id": "user123"
  }
}
```

### 6. Gider Ekleme
**POST** `/events/{id}/expense`

Etkinliğe gider ekler.

**Request Body:**
```json
{
  "user_id": "user123",
  "amount": 150.50,
  "notes": "Pizza ve içecek",
  "weight": 1.0
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Gider eklendi: 150.5 TL, Not: Pizza ve içecek, Ağırlık: 1.0",
  "expense_id": 1,
  "data": {
    "expense_id": 1,
    "event_id": 1,
    "user_id": "user123",
    "amount": 150.5,
    "notes": "Pizza ve içecek",
    "weight": 1.0
  }
}
```

### 7. Etkinlik Özeti
**GET** `/events/{id}/summary`

Etkinliğin detaylı özetini getirir.

**Response:**
```json
{
  "status": "success",
  "data": {
    "event": {
      "event_id": 1,
      "title": "Pizza Gecesi",
      "created_by": "user123",
      "group_id": "group456",
      "created_at": "2025-01-01T10:00:00",
      "status": "active"
    },
    "slots": {
      "1": {
        "start_datetime": "2025-10-12T18:00:00",
        "end_datetime": "2025-10-12T20:00:00",
        "yes_votes": 5,
        "no_votes": 2,
        "total_votes": 7
      }
    },
    "best_slot": {
      "start_datetime": "2025-10-12T18:00:00",
      "end_datetime": "2025-10-12T20:00:00",
      "yes_votes": 5,
      "no_votes": 2,
      "total_votes": 7
    },
    "poll_choices": {
      "1": {
        "text": "Kütüphane",
        "latitude": null,
        "longitude": null,
        "votes": 3
      }
    },
    "best_choice": {
      "text": "Kütüphane",
      "latitude": null,
      "longitude": null,
      "votes": 3
    },
    "expenses": [
      {
        "expense_id": 1,
        "event_id": 1,
        "user_id": "user123",
        "amount": 150.5,
        "notes": "Pizza ve içecek",
        "weight": 1.0,
        "created_at": "2025-01-01T10:30:00"
      }
    ],
    "total_expense": 150.5,
    "participant_count": 7,
    "average_per_person": 21.5,
    "balances": {
      "user123": 128.5,
      "user456": -21.5
    }
  }
}
```

### 8. Hatırlatıcı Gönderme
**POST** `/events/{id}/remind`

Etkinlik için hatırlatıcı gönderir.

**Request Body:**
```json
{
  "message": "Etkinlik yaklaşıyor!",
  "delay": 3600
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Hatırlatıcı 3600 saniye sonra gönderilecek",
  "data": {
    "event_id": 1,
    "group_id": "group456",
    "message": "Etkinlik yaklaşıyor!",
    "delay": 3600
  }
}
```

## Hata Kodları

- **400 Bad Request:** Geçersiz JSON veya eksik alan
- **404 Not Found:** Etkinlik bulunamadı
- **500 Internal Server Error:** Sunucu hatası

## Örnek Kullanım

### Python ile API Kullanımı

```python
import requests

# Etkinlik oluştur
response = requests.post("http://localhost:5000/events", json={
    "title": "Pizza Gecesi",
    "created_by": "user123",
    "group_id": "group456"
})

event_id = response.json()['event_id']

# Slot ekle
requests.post(f"http://localhost:5000/events/{event_id}/slots", json={
    "start_datetime": "2025-10-12T18:00:00",
    "end_datetime": "2025-10-12T20:00:00"
})

# Özet al
summary = requests.get(f"http://localhost:5000/events/{event_id}/summary")
print(summary.json())
```

### JavaScript ile API Kullanımı

```javascript
// Etkinlik oluştur
const response = await fetch('http://localhost:5000/events', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    title: 'Pizza Gecesi',
    created_by: 'user123',
    group_id: 'group456'
  })
});

const data = await response.json();
const eventId = data.event_id;

// Slot ekle
await fetch(`http://localhost:5000/events/${eventId}/slots`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    start_datetime: '2025-10-12T18:00:00',
    end_datetime: '2025-10-12T20:00:00'
  })
});
```

## Test

API'yi test etmek için:

```bash
python test_api.py
```

Bu script tüm endpoint'leri test eder ve sonuçları gösterir.

## Webhook Endpoint

Mevcut webhook endpoint'i hala çalışmaktadır:

**POST** `/webhook/bip`

BiP bot komutlarını işler (legacy support için).
