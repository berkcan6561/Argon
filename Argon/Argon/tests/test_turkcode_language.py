from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from interpreter import TurkCodeInterpreter, stringify


def run_code(source: str):
    interpreter = TurkCodeInterpreter()
    result = interpreter.calistir(source)
    return interpreter, result


def test_basic_expressions_and_print(capsys):
    source = """
    degisken x = 10;
    degisken y = 5;
    yaz("Sonuc: " + (x + y));
    """

    _, result = run_code(source)
    output = capsys.readouterr().out.strip()

    assert result is None
    assert output == "Sonuc: 15"


def test_functions_default_params_and_recursion(capsys):
    source = """
    fonksiyon faktoriyel(n) {
        eger (n <= 1) {
            dondur 1;
        }
        dondur n * faktoriyel(n - 1);
    }

    fonksiyon selamla(isim = "Misafir") {
        dondur "Merhaba " + isim;
    }

    yaz(selamla());
    yaz("F: " + faktoriyel(5));
    """

    run_code(source)
    output = capsys.readouterr().out.strip().splitlines()

    assert output == ["Merhaba Misafir", "F: 120"]


def test_loops_switch_try_and_ternary(capsys):
    source = """
    degisken toplam = 0;
    dongu (degisken i = 1; i <= 4; i++) {
        toplam += i;
    }

    degisken etiket = (toplam == 10) ? "tamam" : "hatali";
    yaz(etiket);

    sec(toplam) {
        durum 10:
            yaz("on");
            dur;
        varsayilan:
            yaz("diger");
    }

    dene {
        degisken x = 10 / 0;
    }
    yakala (hata) {
        yaz("yakalandi");
    }
    """

    run_code(source)
    output = capsys.readouterr().out.strip().splitlines()

    assert output == ["tamam", "on", "yakalandi"]


def test_objects_classes_and_methods(capsys):
    source = """
    sinif Kisi {
        degisken ad = "Bilinmiyor";

        fonksiyon baslat(ad) {
            this.ad = ad;
        }

        fonksiyon selamla() {
            dondur "Merhaba " + this.ad;
        }
    }

    degisken kisi = yeni Kisi("Ahmet");
    yaz(kisi.selamla());
    """

    run_code(source)
    output = capsys.readouterr().out.strip()

    assert output == "Merhaba Ahmet"


def test_modules_and_collections(tmp_path):
    target = tmp_path / "veri.txt"
    source = f'''
    dosya().yaz("{target.as_posix()}", "merhaba");
    degisken metin = dosya().oku("{target.as_posix()}");
    degisken veri = json().coz('{{"ad":"Ayse","yas":30}}');
    degisken sonuc = [metin, veri.ad, veri.yas];
    '''

    interpreter, result = run_code(source)

    assert stringify(result) == '["merhaba", "Ayse", 30]'
    assert Path(target).read_text(encoding="utf-8") == "merhaba"
    assert interpreter.degiskenler["metin"] == "merhaba"


def test_imports_arrow_functions_and_functional_builtins(tmp_path):
    helper = tmp_path / "yardimci.tc"
    helper.write_text(
        """
        fonksiyon birEkle(x) {
            dondur x + 1;
        }

        degisken sabit = 41;
        """,
        encoding="utf-8",
    )

    source = f'''
    ithal "{helper.as_posix()}" olarak yardimci;
    degisken sayilar = [1, 2, 3, 4];
    degisken kareler = harita((x) => x * x, sayilar);
    degisken ciftler = suz((x) => x % 2 == 0, sayilar);
    degisken toplam = azalt((acc, x) => acc + x, kareler, 0);
    degisken sonuc = yardimci.sabit + toplam;
    '''

    interpreter, result = run_code(source)

    assert result == 71
    assert stringify(interpreter.degiskenler["kareler"]) == "[1, 4, 9, 16]"
    assert stringify(interpreter.degiskenler["ciftler"]) == "[2, 4]"


def test_plain_import_merges_symbols(tmp_path, capsys):
    helper = tmp_path / "selam.tc"
    helper.write_text(
        """
        fonksiyon selamla(isim) {
            dondur "Merhaba " + isim;
        }
        """,
        encoding="utf-8",
    )

    source = f'''
    ithal "{helper.as_posix()}";
    yaz(selamla("Ada"));
    '''

    run_code(source)
    assert capsys.readouterr().out.strip() == "Merhaba Ada"


def test_python_libraries_can_be_imported_with_turkish_aliases(capsys):
    source = """
    ithal "math" olarak matematik;
    degisken sonuc = matematik.karekök(81) + matematik.faktoriyel(4);
    yaz(sonuc);
    """

    interpreter, result = run_code(source)

    assert result is None
    assert interpreter.degiskenler["sonuc"] == 33.0
    assert capsys.readouterr().out.strip() == "33.0"
    assert stringify(interpreter.degiskenler["matematik"]) == "<python kutuphanesi math>"


def test_plain_python_import_exports_original_and_turkish_names():
    source = """
    ithal "math";
    degisken sonuc = karekok(25) + factorial(3);
    """

    _, result = run_code(source)

    assert result == 11.0


def test_library_builtin_and_python_object_members_use_turkish_names():
    source = """
    degisken rastgele = kütüphane("rastgele");
    degisken istatistik = kutuphane("statistics");
    degisken secim = rastgele.seç([42]);
    degisken ort = istatistik.ortalama([2, 4, 6]);
    degisken metin = "MERHABA".küçükHarf();
    degisken sonuc = [secim, ort, metin];
    """

    _, result = run_code(source)

    assert stringify(result) == '[42, 4, "merhaba"]'


def test_syntax_error_contains_file_and_location():
    interpreter = TurkCodeInterpreter()

    with pytest.raises(Exception) as exc_info:
        interpreter.cozumle("degisken =", dosya_adi="ornek.tc")

    error = exc_info.value
    assert getattr(error, "filename", None) == "ornek.tc"
    assert getattr(error, "line", None) == 1
    assert getattr(error, "column", None) is not None


@pytest.mark.parametrize(
    "filename",
    [
        "merhaba.tc",
        "complete.tc",
        "gelişmiş.tc",
        "hesap_makinesi.tc",
        "kutuphane.tc",
        "moduller_ve_lambda.tc",
        "profesyonel.tc",
        "ultra.tc",
    ],
)
def test_example_files_run(filename, capsys):
    base = Path(__file__).resolve().parents[1] / "örnekler"
    example_path = base / filename
    source = example_path.read_text(encoding="utf-8")

    interpreter = TurkCodeInterpreter()
    interpreter.calistir(source, dosya_adi=str(example_path))

    assert capsys.readouterr().out.strip() != ""
