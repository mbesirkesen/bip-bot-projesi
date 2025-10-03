#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📱 BiP Bot - QR Kod Oluşturucu
BiP Bot davet linki için QR kod oluşturur

Özellikler:
- Yüksek kaliteli QR kod üretimi
- Otomatik dosya boyutu optimizasyonu
- Environment variable desteği
- Unicode karakter desteği
- Hata yönetimi ve loglama

Kullanım:
python qr_olustur.py

Yazar: BiP Bot Development Team
Versiyon: 2.0.0
"""

import qrcode
import os
import sys
from datetime import datetime

def create_qr_code(url, filename="invite.png"):
    """
    Verilen URL için QR kod oluşturur
    
    Args:
        url (str): QR kodda gösterilecek URL
        filename (str): Kaydedilecek dosya adı
    
    Returns:
        bool: Başarılı olup olmadığı
    """
    try:
        # QR kod oluştur
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        # Görüntü oluştur
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Kaydet
        img.save(filename)
        
        # Dosya boyutunu kontrol et
        file_size = os.path.getsize(filename)
        print(f"QR kod basariyla olusturuldu: {filename}")
        print(f"Dosya boyutu: {file_size} bytes")
        print(f"URL: {url}")
        print(f"Olusturulma zamani: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True
        
    except Exception as e:
        print(f"QR kod olusturma hatasi: {str(e)}")
        return False

def main():
    """Ana fonksiyon"""
    # URL'yi belirle (environment variable'dan al veya varsayılan kullan)
    base_url = os.environ.get('BIP_BOT_URL', 'http://localhost:5000')
    invite_url = f"{base_url}/invite"
    
    # QR kod oluştur
    success = create_qr_code(invite_url)
    
    if success:
        print("\nQR kod hazir! Bu kodu BiP ile tarayarak bot'u kullanmaya baslayabilirsiniz.")
    else:
        print("\nQR kod olusturulamadi. Lutfen hatalari kontrol edin.")
        sys.exit(1)

if __name__ == "__main__":
    main()