YouTube Kamera ile Kontrol (Gesture-based YouTube Controller)

Açıklama
- Bu proje, MediaPipe ile elde tespiti yapıp çeşitli el hareketlerini YouTube klavye kısayollarına çevirir.

Kurulum
PowerShell'de (proje kökünde):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
```

Çalıştırma
- YouTube oynatıcısını ön plana getirin (odak) ve ardından programı çalıştırın:

```powershell
python .\main.py
```

Uyarılar ve İpuçları
- Program pyautogui ile fiziksel klavye olayları gönderir; çalıştırmadan önce dikkatli olun.
- Kameraya erişim izni gereklidir.
- Eğer kısayollar farklıysa (ör. farklı dil/klavye yerleşimi), `main.py` içinde `pyautogui.press(...)` çağrılarını düzenleyin.
- Geliştirme önerileri: hareket eşiklerini (threshold) ayarlayın, hata loglarını ekleyin veya eğitim modu ekleyin.

