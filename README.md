# 🤖 BiP Bot - Etkinlik Yönetim Sistemi v2.0

**SQLite Veritabanı ile Güçlendirilmiş Profesyonel Etkinlik Yönetim Sistemi**

BiP Bot, grup etkinliklerini kolayca organize etmenizi sağlayan akıllı bir bot sistemidir. ACID uyumlu SQLite veritabanı, ilişkisel veri modeli ve gelişmiş özellikler ile etkinliklerinizi profesyonelce yönetin.

## ✨ Özellikler

- 🎉 **Etkinlik Oluşturma**: Kolay etkinlik başlatma
- 🕒 **Tarih/Saat Oylaması**: Katılımcıların uygun zamanları belirlemesi
- 📍 **Mekan Seçimi**: Lokasyon önerileri ve oylama
- 💰 **Gider Takibi**: Ağırlıklı masraf dağılımı
- ⏰ **Otomatik Hatırlatıcılar**: 24 saat ve 1 saat önceden bildirimler
- 📊 **Detaylı Özetler**: Kapsamlı etkinlik raporları
- 🔐 **Moderatör Kontrolü**: Yetki tabanlı işlemler

## 🚀 Kurulum

### Gereksinimler

```bash
pip install flask flask-cors pandas qrcode
```

### Kurulum Adımları

1. **Projeyi klonlayın**:
   ```bash
   git clone <repo-url>
   cd bip-bot-projesi
   ```

2. **Sanal ortam oluşturun**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # veya
   venv\Scripts\activate  # Windows
   ```

3. **Bağımlılıkları yükleyin**:
   ```bash
   pip install -r requirements.txt
   ```

4. **QR kod oluşturun**:
   ```bash
   python qr_olustur.py
   ```

5. **Uygulamayı başlatın**:
   ```bash
   python app.py
   ```

## 📱 Kullanım

### Web Arayüzü

1. Tarayıcınızda `http://localhost:5000` adresine gidin
2. Frontend arayüzü ile bot'u test edin
3. Başlığa çift tıklayarak kullanıcı/grup ID'lerini ayarlayın

### BiP Komutları

| Komut | Açıklama | Örnek |
|-------|----------|-------|
| `/yeni ETKİNLİK_ADI` | Yeni etkinlik oluştur | `/yeni Kahve Buluşması` |
| `/slot YYYY-MM-DD HH:MM-HH:MM` | Tarih/saat seçeneği ekle | `/slot 2025-12-25 18:00-20:00` |
| `/katil slot=1 yes/no` | Slot için katılım oyu ver | `/katil slot=1 yes` |
| `/mekan MEKAN_ADI [enlem boylam]` | Mekan önerisi ekle | `/mekan Starbucks 40.1 29.2` |
| `/oy_mekan CHOICE_ID` | Mekan için oy ver | `/oy_mekan 1` |
| `/gider TUTAR "Açıklama" [ağırlık]` | Gider ekle | `/gider 150 "Pizza" 1.5` |
| `/ozet` | Etkinlik özetini göster | `/ozet` |
| `/slot_kapat SLOT_ID` | Slot'u kapat (moderatör) | `/slot_kapat 1` |
| `/oy_kilit` | Oylamayı kilitle (moderatör) | `/oy_kilit` |

## 🏗️ Proje Yapısı

```
bip-bot-projesi/
├── app.py                 # Ana Flask uygulaması
├── frontend.html          # Web arayüzü
├── qr_olustur.py          # QR kod oluşturucu
├── requirements.txt       # Python bağımlılıkları
├── README.md             # Bu dosya
├── invite.png            # QR kod (oluşturulur)
└── CSV Dosyaları/
    ├── events.csv        # Etkinlik bilgileri
    ├── slots.csv         # Tarih/saat seçenekleri
    ├── slot_votes.csv    # Slot oyları
    ├── polls.csv         # Mekan oylamaları
    ├── poll_choices.csv  # Mekan seçenekleri
    ├── poll_votes.csv    # Mekan oyları
    ├── expenses.csv      # Gider kayıtları
    └── users.csv         # Kullanıcı bilgileri
```

## 🔧 Yapılandırma

### Ortam Değişkenleri

```bash
# Uygulama portu (varsayılan: 5000)
export PORT=5000

# Debug modu (varsayılan: False)
export DEBUG=True

# BiP Bot URL'i QR kod için
export BIP_BOT_URL=http://your-domain.com
```

### Production Deployment

1. **Gunicorn ile**:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

2. **Docker ile**:
   ```dockerfile
   FROM python:3.9-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
   ```

## 🛠️ Geliştirme

### Yeni Özellik Ekleme

1. `app.py` dosyasında yeni komut işleyicisi ekleyin
2. Gerekli CSV dosyalarını güncelleyin
3. Frontend'e yeni butonlar ekleyin
4. Test edin ve dokümantasyonu güncelleyin

### Hata Ayıklama

```bash
# Debug modunda çalıştır
export DEBUG=True
python app.py

# Logları kontrol et
tail -f app.log
```

## 📊 API Endpoints

| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/webhook/bip` | POST | BiP komutlarını işler |
| `/health` | GET | Sistem sağlık kontrolü |
| `/invite` | GET | Davet sayfası ve QR kod |

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/yeni-ozellik`)
3. Commit yapın (`git commit -am 'Yeni özellik eklendi'`)
4. Push yapın (`git push origin feature/yeni-ozellik`)
5. Pull Request oluşturun

## 📝 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için `LICENSE` dosyasına bakın.

## 🆘 Destek

- 📧 Email: support@example.com
- 💬 Issues: GitHub Issues sayfasını kullanın
- 📖 Dokümantasyon: [Wiki sayfası](link-to-wiki)

## 🔄 Güncelleme Geçmişi

### v1.1.0 (2025-01-XX)
- ✅ Gelişmiş hata yönetimi
- ✅ Logging sistemi eklendi
- ✅ Frontend iyileştirmeleri
- ✅ QR kod oluşturucu geliştirildi
- ✅ API dokümantasyonu eklendi

### v1.0.0 (2025-01-XX)
- 🎉 İlk sürüm yayınlandı
- ✅ Temel etkinlik yönetimi
- ✅ Slot ve mekan oylaması
- ✅ Gider takibi

---

**BiP Bot ile etkinliklerinizi kolayca organize edin! 🎉**
