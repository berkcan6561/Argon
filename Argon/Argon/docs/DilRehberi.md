# TürkCode Dil Rehberi

Bu sürüm, tek dosyada üst üste eklenmiş deneme sürümleri yerine çalışan bir yorumlayıcı ve daha yetenekli bir IDE üzerine kuruludur. Belgede yalnızca gerçekten desteklenen sözdizimi ve özellikler yer alır.

## 1. Çalıştırma

Komut satırı:

```bash
python interpreter.py örnekler/merhaba.tc
python interpreter.py -i
```

IDE:

```bash
python ide.py
```

## 2. Temel Kurallar

- Dosya uzantısı: `.tc`
- Satır sonu için `;` önerilir.
- Basit satırlarda `;` yazılmasa da yorumlayıcı çoğu durumda bunu tolere eder.
- Tek satır yorum: `//`
- Blok yorum: `/* ... */`

## 3. Değişkenler ve Tipler

```turkcode
degisken ad = "Ayse";
degisken yas = 21;
degisken oran = 4.5;
degisken aktif = dogru;
degisken veri = bos;
degisken sayilar = [1, 2, 3];
degisken kisi = {ad: "Ayse", sehir: "Ankara"};
```

Desteklenen tipler:

- `tam`
- `ondalik`
- `metin`
- `mantiksal`
- `liste`
- `nesne`
- `bos`

## 4. Operatörler

### Aritmetik

```turkcode
+   -   *   /   %   ^
```

Tam sayı bölme için:

```turkcode
tamBol(7, 3);   // 2
```

### Karşılaştırma

```turkcode
==   !=   >   <   >=   <=
```

### Mantıksal

```turkcode
ve
veya
degil
```

### Atama

```turkcode
=
+=
-=
*=
/=
%=
++ 
--
```

## 5. Koşullar

```turkcode
eger (puan >= 90) {
    yaz("Harika");
}
degilse eger (puan >= 70) {
    yaz("Iyi");
}
degilse {
    yaz("Gelismeli");
}
```

Ternary:

```turkcode
degisken sonuc = yas >= 18 ? "yetiskin" : "cocuk";
```

Switch:

```turkcode
sec(gun) {
    durum 1:
        yaz("Pazartesi");
        dur;
    durum 2:
        yaz("Sali");
        dur;
    varsayilan:
        yaz("Bilinmiyor");
}
```

## 6. Döngüler

### C tarzı `for`

```turkcode
dongu (degisken i = 0; i < 5; i++) {
    yaz(i);
}
```

### `while`

```turkcode
degisken i = 0;
while (i < 3) {
    yaz(i);
    i++;
}
```

### `do-while`

```turkcode
degisken i = 0;
yap {
    yaz(i);
    i++;
} while (i < 3);
```

### `foreach`

```turkcode
her (degisken eleman in ["a", "b", "c"]) {
    yaz(eleman);
}
```

## 7. Fonksiyonlar

Normal fonksiyon:

```turkcode
fonksiyon topla(a, b = 0) {
    dondur a + b;
}
```

Recursive fonksiyon:

```turkcode
fonksiyon faktoriyel(n) {
    eger (n <= 1) {
        dondur 1;
    }
    dondur n * faktoriyel(n - 1);
}
```

### Anonim Fonksiyonlar

Blok gövdeli anonim fonksiyon:

```turkcode
degisken ikiKat = fonksiyon(x) {
    dondur x * 2;
};
```

Ok fonksiyonu:

```turkcode
degisken kare = (x) => x * x;
degisken topla = (a, b) => a + b;
```

## 8. Koleksiyon Fonksiyonları

### `harita`

```turkcode
degisken kareler = harita((x) => x * x, [1, 2, 3, 4]);
```

### `suz`

```turkcode
degisken ciftler = suz((x) => x % 2 == 0, [1, 2, 3, 4]);
```

### `azalt`

```turkcode
degisken toplam = azalt((acc, x) => acc + x, [1, 2, 3, 4], 0);
```

### `aralik`

```turkcode
degisken sayilar = aralik(1, 6);   // [1, 2, 3, 4, 5]
```

## 9. Nesneler ve Özellik Erişimi

```turkcode
degisken kisi = {
    ad: "Mehmet",
    yas: 30
};

yaz(kisi.ad);
yaz(kisi.yas);
```

Liste ve indeks erişimi:

```turkcode
degisken sayilar = [10, 20, 30];
yaz(sayilar[1]);
```

## 10. Sınıflar

```turkcode
sinif Sayac {
    degisken deger = 0;

    fonksiyon baslat(ilkDeger = 0) {
        this.deger = ilkDeger;
    }

    fonksiyon arttir() {
        this.deger++;
    }

    fonksiyon oku() {
        dondur this.deger;
    }
}

degisken sayac = yeni Sayac(10);
sayac.arttir();
yaz(sayac.oku());
```

Kurucu metod adı `baslat` olmalıdır.

## 11. Modül, Dosya ve Kütüphane İthal Etme

TürkCode dosyaları başka dosyalardan içeri alınabilir.

### Takma ad ile

```turkcode
ithal "yardimci.tc" olarak yardimci;
yaz(yardimci.selamla("Ada"));
```

### Sembolleri doğrudan içeri alma

```turkcode
ithal "matematik.tc";
yaz(topla(2, 3));
```

İthal edilen yollar aktif dosyaya göre çözülür. Uzantı yazılmazsa yorumlayıcı önce `.tc` eklemeyi dener.

### Python kütüphanesi içeri alma

Dosya bulunamazsa aynı isim Python kütüphanesi olarak yüklenir. Böylece standart kütüphane ve kurulu paketler kullanılabilir.

```turkcode
ithal "math" olarak matematik;
yaz(matematik.karekök(81));       // 9.0
yaz(matematik.faktoriyel(5));     // 120
```

Takma ad vermeden ithal ederseniz kütüphanenin açık fonksiyonları geçerli ortama eklenir.

```turkcode
ithal "math";
yaz(karekok(25) + factorial(3));  // 11.0
```

Fonksiyon içinde de `kutuphane` / `kütüphane` kullanılabilir.

```turkcode
degisken rastgele = kütüphane("rastgele");      // random
degisken istatistik = kutuphane("statistics");

yaz(rastgele.seç([10, 20, 30]));
yaz(istatistik.ortalama([2, 4, 6]));
```

Yaygın Python fonksiyonları için Türkçe takma adlar vardır: `sqrt` için `karekok`/`karekök`, `randint` için `rastgeleTam`, `mean` için `ortalama`, `loads` için `coz`/`çöz`, `upper` için `buyukHarf`/`büyükHarf` gibi. Takma adı olmayan fonksiyonlar özgün Python adıyla çağrılabilir.

## 12. Hata Yönetimi

```turkcode
dene {
    degisken x = 10 / 0;
}
yakala (hata) {
    yaz("Hata yakalandi");
}
```

Elle hata fırlatma:

```turkcode
firlat "Bir sorun olustu";
```

## 13. Yerleşik Fonksiyonlar

### Liste

- `uzunluk`
- `ilk`
- `son`
- `sirala`
- `ters`
- `ekle`
- `sil`
- `dilim`
- `birlestir`
- `harita`
- `suz`
- `azalt`
- `aralik`

### Metin

- `buyukHarf`
- `kucukHarf`
- `degistir`
- `icerir`
- `basla`
- `bitir`
- `parcala`
- `karakter`
- `metinParcasi`

### Matematik

- `yuvarla`
- `yuvarlaAsagi`
- `yuvarlaYukari`
- `mutlak`
- `karekok`
- `us`
- `tamBol`
- `sin`
- `cos`
- `tan`
- `log`
- `log10`
- `rastgele`
- `rastgeleTam`

### Zaman

- `simdi`
- `tarih`
- `saat`
- `zaman`

### Tip ve dönüşüm

- `tip`
- `miSayi`
- `miMetin`
- `miListe`
- `miNesne`
- `tam`
- `ondalik`
- `metin`

### Kütüphane

- `kutuphane`
- `kütüphane`
- `modul`
- `modül`
- `paket`

## 14. Modüller

Modüller fonksiyon gibi çağrılır ve nesne döndürür:

```turkcode
degisken j = json();
degisken r = regex();
degisken t = tarihModul();
degisken d = dosya();
```

### `json()`

- `donustur`
- `coz`

### `regex()`

- `esles`
- `bul`
- `degistir`

### `tarihModul()`

- `simdi`
- `bugun`
- `formatla`

### `dosya()`

- `oku`
- `satirlariOku`
- `yaz`
- `ekle`
- `varMi`
- `klasorMu`

### `ag()`

- `iste`

### Python kütüphaneleri

`kutuphane("math")`, `kutuphane("random")`, `kutuphane("statistics")`, `kutuphane("pathlib")` gibi çağrılar gerçek Python modüllerini döndürür. Kütüphane adı için bazı Türkçe karşılıklar da tanınır: `matematik`, `rastgele`, `istatistik`, `tarihSaat`, `işletim`, `yol`, `düzenliIfade`.

## 15. IDE Özellikleri

Güncel IDE şunları içerir:

- Proje gezgini
- Çoklu sekme yönetimi
- Satır numaraları
- Sözdizimi renklendirme
- Otomatik tamamlama
- Akıllı girinti
- Parantez/tırnak eşleme
- Yorum aç-kapat kısayolu
- Sorun paneli
- Sembol paneli
- Sözdizimi kontrolü
- Dahili çalıştırma konsolu
- Hazır kod parçacıkları

## 16. Örnek Dosyalar

`örnekler/` klasöründe çalışan örnekler bulunur:

- `merhaba.tc`
- `complete.tc`
- `gelişmiş.tc`
- `hesap_makinesi.tc`
- `profesyonel.tc`
- `ultra.tc`
- `moduller_ve_lambda.tc`
- `kutuphane.tc`

## 17. Geliştirme Notu

- Belgede yer almayan sentakslar desteklenmeyebilir.
- Yeni özellik eklerken önce `tests/` altına test eklemek en sağlıklı yoldur.
