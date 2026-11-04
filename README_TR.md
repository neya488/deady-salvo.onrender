# DEADY SALVO – Kurulum ve yayınlama

## 1) Termux'ta yerel kurulum

Termux'ta proje klasörüne gir:

```bash
cd deady_salvo_platform
pkg update -y
pkg install python -y
pip install -r requirements.txt
```

Uygulamayı başlat:

```bash
python app.py
```

Telefondaki tarayıcıdan aç:

`http://127.0.0.1:5000`

Sunucuyu durdurmak için Termux'ta `CTRL+C` kullan. Android klavyende CTRL tuşu yoksa Termux ekstra tuş satırından CTRL+C yapabilirsin.

## 2) İlk yönetici hesabını oluştur

Önce normal kayıt sayfasından bir hesap oluştur:

`http://127.0.0.1:5000/register`

Ardından sunucuyu durdur ve Termux'ta şu komutu çalıştır:

```bash
python -c "import sqlite3; c=sqlite3.connect('deady_salvo.db'); u=input('Yönetici yapmak istediğin kullanıcı adı: '); r=c.execute('UPDATE users SET is_admin=1 WHERE username=?',(u,)); c.commit(); print('Yönetici yapıldı.' if r.rowcount else 'Kullanıcı bulunamadı. Önce kayıt ol.'); c.close()"
```

Tekrar `python app.py` ile başlat. Yönetici hesabınla giriş yapınca menüde Yönetim görünür.

## 3) İnternete yayınlama (Render)

Termux'ta yerel sunucu çalıştırmak, siteyi herkese açmaz. Herkese açık ve telefon kapalıyken de çalışacak site için bir hosting gerekir.

Kolay yol:
1. GitHub'da hesap aç.
2. Bu ZIP'i aç ve içindeki dosyaları bir GitHub deposuna yükle.
3. Render.com hesabı aç ve GitHub hesabını bağla.
4. Render'da **New + → Blueprint** seçip bu depoyu bağla.
5. Render, `render.yaml` dosyasındaki ayarlarla servisi kurar.
6. Yayın tamamlanınca Render sana `https://...onrender.com` adresi verir.

Render'ın ücretsiz planı, kalıcı disk veya servis özellikleri değişebilir ve ücretsiz servisler uykuya geçebilir. Bu projede veritabanı kalıcılığı için Render disk tanımı bulunur; disk ücretli plan gerektirebilir. Yayına almadan önce Render'ın güncel fiyat ve disk koşullarını kontrol et.

## 4) Güvenlik ve önemli notlar

- `SECRET_KEY` güçlü ve gizli olmalı. Render Blueprint bunu otomatik üretir.
- Yönetici hesabı için tahmin edilmesi zor, benzersiz bir parola kullan.
- İlk sürümde profil fotoğrafı yükleme ve özel mesajlaşma bilerek eklenmedi; dosya yükleme ve mesajlaşma ek güvenlik ve moderasyon gerektirir.
- Herkese açık toplulukta kullanıcı gönderileri görülebilir. Zararlı içerikleri yönetim panelinden kaldır.
- Bu başlangıç projesi temel CSRF koruması, parola hashleme, güvenli çerez ayarları ve güvenlik başlıkları içerir; profesyonel ölçekte yayın öncesi ayrıca güvenlik testi ve yedekleme planı gerekir.
- `deady.localhost` yalnızca yerel bir alan adı varsayımıdır; internetteki gerçek adresin hosting sağlayıcının verdiği URL veya bağlayacağın özel alan adı olur.
