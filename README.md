# Argon

Argon, Türkçe anahtar kelimelerle yazılmış kodu çalıştıran bir yorumlayıcı ve PyQt tabanlı bir masaüstü IDE içerir.

## Özellikler

- Türkçe söz dizimi ile kod yazma
- Değişkenler, fonksiyonlar, sınıflar, döngüler, koşullar, switch/case, try/catch
- Türkçe adlarla Python standart kütüphanelerini kullanabilme
- PyQt5 veya PySide6 üzerinden çalışan IDE
- Otomatik tamamlama, satır numaraları, dosya gezgini, kayıt desteği
- Örnek `.tc` dosyaları ve testlerle birlikte

## Kurulum

1. Python 3.11 veya sonraki bir sürümünü kullanın.
2. Gerekli paketleri yükleyin:

```bash
python -m pip install PyQt5
```

> Eğer PySide6 kullanmak isterseniz:
>
> ```bash
> python -m pip install PySide6
> ```

## Çalıştırma

### Yorumlayıcı

```bash
python interpreter.py örnekler/merhaba.tc
```

### Etkileşimli mod

```bash
python interpreter.py -i
```

### IDE

```bash
python ide.py
```

## Örnekler

`örnekler/` klasörü içinde çeşitli Türkçe kod dosyaları vardır:

- `merhaba.tc`
- `complete.tc`
- `hesap_makinesi.tc`
- `kutuphane.tc`
- `moduller_ve_lambda.tc`
- `profesyonel.tc`
- `ultra.tc`

## Testler

Aşağıdaki komutla testleri çalıştırabilirsiniz:

```bash
python -m pytest -q
```

## Proje Yapısı

- `interpreter.py` — TürkCode yorumlayıcısı
- `ide.py` — Qt tabanlı IDE
- `docs/` — dil rehberi ve belge
- `örnekler/` — örnek TürkCode dosyaları
- `tests/` — otomatik testler

## Notlar

- IDE için `PyQt5` veya `PySide6` gereklidir.
- Qt platform eklentileri bulunmazsa `QT_QPA_PLATFORM_PLUGIN_PATH` otomatik olarak algılanmaya çalışılır.
