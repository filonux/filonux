#!/usr/bin/env python3
"""Pruebas de donate.py: validadores con vectores oficiales, errores a propósito, render y sincronización.

    python3 scripts/test_donate.py

Solo biblioteca estándar. Con `pycryptodome` y `bech32` instalados se añaden dos comparaciones contra implementaciones
independientes; con `segno`, las pruebas de `sync` y del kit de los repos; con `zxing-cpp`, `cairosvg` y `pillow`, la lectura
de los QR con un decodificador independiente. Sin ellas se omiten (skipped): es normal. Las direcciones de prueba son
públicas de documentación o sintéticas; solo la clase `Perfil` lee tu perfil real (README, Únete/Join, QR, kit de los repos
y direcciones.ini).
"""
import html
import io
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True  # antes de importar donate: no se crea scripts/__pycache__/ y el repo no necesita .gitignore
import donate as d  # noqa: E402

COIN = {c["key"]: c for c in d.COINS}
LEVEL = lambda key, addr: d.check_address(COIN[key], addr)[0]

# Públicas y de documentación (no son direcciones de nadie a quien debas pagar):
BTC_OK = ["bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4", "BC1QW508D6QEJXTDG4Y5R3ZARVARY0C5XW7KV8F3T4",
          "bc1p0xlxvlhemja6c4dqv22uapctqupfhlxm9h8z3k2e72q4k9hcz7vqzk5jj0",  # Taproot (BIP-350)
          "bc1pw508d6qejxtdg4y5r3zarvary0c5xw7kw508d6qejxtdg4y5r3zarvary0c5xw7kt5nd6y",
          "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2", "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"]
BTC_BAD = ["bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t5",                       # checksum
           "tb1qw508d6qejxtdg4y5r3zarvary0c5xw7kxpjzsx",                       # testnet
           "BC13W508D6QEJXTDG4Y5R3ZARVARY0C5XW7KN40WF2",                       # versión 17
           "bc1rw5uspcuh", "BC1QR508D6QEJXTDG4Y5R3ZARVARYV98GJ9P",             # programa corto / v0 de 16 bytes
           "bc1p0xlxvlhemja6c4dqv22uapctqupfhlxm9h8z3k2e72q4k9hcz7vqh2y7hd",  # v1 con checksum Bech32 (no Bech32m)
           "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kemeawh",                       # v0 con checksum Bech32m
           "Bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",                       # mayúsculas mezcladas
           "11A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNb", ""]
# Vectores oficiales del EIP-55
ETH_MIXED = ["0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed", "0xfB6916095ca1df60bB79Ce92cE3Ea74c37c5d359",
             "0xdbF03B407c01E7cD3CBea99509d93f8DDDC8C6FB", "0xD1220A0cf47c7B9Be7A2E6BA89F429762e7b9aDb"]
ETH_CAPS = ["0x52908400098527886E0F7030069857D2E4169EE7", "0x8617E340B3D01FA5F11F306F4090FD50E238070D"]
ETH_LOWER = ["0xde709f2102306220921060314715629080e2fb77", "0x27b1fdb04752bbc536007a920d24acb045561c26"]
OTHER_NETWORKS = ["TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",                                  # Tron (y contrato de USDT en Tron)
                  "44AFFq5kSiGBoZ4NMDwYtN18obc8AemS33DBLWs3H7otXft3XjrpDtQGv7SqSsaBYBb98uNbr2VBBEt7f2wfn3RVGQBEP3A",  # Monero
                  "t1Hsc1LR8yKnbbe3twRp88p6vFfC5t7DLbs"]                                  # Zcash

# Bech32/Bech32m del BIP-173 y BIP-350
BECH32_OK = ["A12UEL5L", "a12uel5l", "abcdef1qpzry9x8gf2tvdw0s3jn54khce6mua7lmqqqxw", "?1ezyfcl",
             "split1checkupstagehandshakeupstreamerranterredcaperred2y9e3w"]
BECH32M_OK = ["A1LQFN3A", "a1lqfn3a", "abcdef1l7aum6echk45nj3s0wdvt2fg8x9yrzpqzd3ryx", "?1v759aa",
              "split1checkupstagehandshakeupstreamerranterredcaperredlc445v"]

PROFILE = ("# Perfil\n\n<img src=\"./assets/banner2.svg\" width=\"480\" alt=\"x\">\n\n## `$ ./stats.sh`\n\nx\n\n"
           "## `$ ./contacto.sh`\n\ncorreo\n")


def mutations(addr):
    """Una letra cambiada, una letra borrada y dos letras contiguas intercambiadas."""
    for i, ch in enumerate(addr):
        for r in "0qQ1zZ":
            if r != ch:
                yield addr[:i] + r + addr[i + 1:]
        yield addr[:i] + addr[i + 1:]
        if i + 1 < len(addr) and addr[i] != addr[i + 1]:
            yield addr[:i] + addr[i + 1] + addr[i] + addr[i + 2:]


def quiet():
    return redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO())


def decode_qr(svg, scale=1):
    """Lo que lee un decodificador independiente (zxing-cpp) en un QR SVG pintado a `scale`× su tamaño en pantalla."""
    try:
        import cairosvg
        import zxingcpp
        from PIL import Image
    except ImportError:
        raise unittest.SkipTest("zxing-cpp, cairosvg o pillow no instalados")
    png = cairosvg.svg2png(url=str(svg), scale=scale, background_color="#ffffff")
    return [r.text for r in zxingcpp.read_barcodes(Image.open(io.BytesIO(png)).convert("RGB"))]


class Hash(unittest.TestCase):
    def test_keccak_vectors(self):
        self.assertEqual(d.keccak256(b"").hex(), "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470")
        self.assertEqual(d.keccak256(b"abc").hex(), "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45")

    def test_keccak_contra_implementacion_independiente(self):
        try:
            from Crypto.Hash import keccak
        except ImportError:
            self.skipTest("pycryptodome no instalado")
        for n in (0, 1, 65, 135, 136, 137, 300):
            data = os.urandom(n)
            self.assertEqual(d.keccak256(data), keccak.new(digest_bits=256, data=data).digest(), n)


class Validadores(unittest.TestCase):
    def test_btc(self):
        for a in BTC_OK:
            self.assertEqual(LEVEL("btc", a), "ok", a)
        for a in BTC_BAD:
            self.assertEqual(LEVEL("btc", a), "error", a)

    def test_bech32_y_bech32m_oficiales(self):
        for a in BECH32_OK:
            hrp = a.lower().rsplit("1", 1)[0]
            self.assertIsNotNone(d._bech32(a, hrp, "bech32", maxlen=None), a)
            self.assertIsNone(d._bech32(a, hrp, "bech32m", maxlen=None), a)
        for a in BECH32M_OK:
            hrp = a.lower().rsplit("1", 1)[0]
            self.assertIsNotNone(d._bech32(a, hrp, "bech32m", maxlen=None), a)
            self.assertIsNone(d._bech32(a, hrp, "bech32", maxlen=None), a)

    def test_btc_contra_libreria_independiente(self):
        try:
            import bech32
        except ImportError:
            self.skipTest("bech32 no instalado")
        for n in (20, 32):
            for _ in range(50):
                a = bech32.encode("bc", 0, os.urandom(n))
                self.assertEqual(LEVEL("btc", a), "ok", a)

    def test_eth_vectores_eip55(self):
        for a in ETH_MIXED:
            self.assertEqual(d.check_address(COIN["usdt"], a), d.OK, a)
        for a in ETH_CAPS + ETH_LOWER:       # válidas, pero sin checksum que las proteja: avisa
            self.assertEqual(LEVEL("usdt", a), "warn", a)

    def test_eth_rechaza(self):
        a = ETH_MIXED[0]
        malas = [a[:-1], a + "0", a.replace("0x", "0X"), a[2:], "0x" + "g" * 40, "0x" + a[2:].replace("a", "A", 1),
                 d.USDT_CONTRACT, "0x" + d.USDT_CONTRACT[2:].upper(), ""] + OTHER_NETWORKS
        for m in malas:
            self.assertEqual(LEVEL("usdt", m), "error", m)

    def test_eth_cualquier_errata_se_detecta(self):
        for a in ETH_MIXED:
            for m in mutations(a):
                if m != a:
                    self.assertNotEqual(LEVEL("usdt", m), "ok", m)
            for i, ch in enumerate(a):          # cambiar solo una mayúscula/minúscula (la errata típica)
                if ch.isalpha() and i > 1:
                    self.assertEqual(LEVEL("usdt", a[:i] + ch.swapcase() + a[i + 1:]), "error", (a, i))

    def test_btc_cualquier_errata_se_detecta(self):
        for a in BTC_OK[:1] + BTC_OK[4:]:
            for m in mutations(a):
                if m != a:
                    self.assertNotEqual(LEVEL("btc", m), "ok", m)

    def test_btc_no_acepta_direccion_de_usdt_ni_al_reves(self):
        self.assertEqual(LEVEL("btc", ETH_MIXED[0]), "error")
        self.assertEqual(LEVEL("usdt", BTC_OK[0]), "error")


class Ini(unittest.TestCase):
    def _load(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.ini"
            p.write_text(text, encoding="utf-8")
            return d.load_ini(p)

    def test_lee_direcciones_y_comentarios(self):
        got = self._load(f"# c\n[general]\nbtc = {BTC_OK[0]}   # comentario\nusdt =\n")
        self.assertEqual(got, {"btc": BTC_OK[0], "usdt": ""})

    def test_falta_el_archivo_o_esta_vacio(self):
        self.assertEqual(d.load_ini(Path("/no/existe.ini")), {})
        self.assertEqual(self._load("# solo comentarios\n"), {})

    def test_otras_secciones_ya_no_existen(self):
        with self.assertRaises(SystemExit):
            self._load("[general]\nbtc =\n[Mint-Doctor]\nbtc =\n")

    def test_el_ini_del_paquete_es_valido_y_no_contiene_direcciones_de_prueba(self):
        ini = d.load_ini()
        self.assertTrue(set(ini) <= {"btc", "usdt"}, ini)
        publicas = {a.lower() for a in BTC_OK + ETH_MIXED + ETH_CAPS + ETH_LOWER + OTHER_NETWORKS}
        for key, a in ini.items():
            if a:
                self.assertNotEqual(LEVEL(key, a), "error", key)
                self.assertNotIn(a.lower(), publicas, f"{key}: es una dirección de documentación, no tuya")


class Render(unittest.TestCase):
    def setUp(self):
        self._saved = dict(d.ADDRESSES)
        d._warned.clear()
        d.ADDRESSES.clear()
        d.ADDRESSES.update(btc=BTC_OK[0], usdt=ETH_MIXED[0])

    def tearDown(self):
        d.ADDRESSES.clear()
        d.ADDRESSES.update(self._saved)

    def test_perfil_y_repo_llevan_boton_tarjeta_y_qr(self):
        for lang in d.LANGS:
            profile, repo = d.render(lang), d.render(lang, repo=True)
            self.assertIn(f'src="./assets/donate-{lang}.svg"', profile)
            self.assertIn(f'src="./assets/donate-card-{lang}.svg"', profile)
            self.assertEqual(profile.count('<img src="./assets/qr/'), 2)
            self.assertNotIn("./assets/donate/", profile)
            for name in (f"card-{lang}", f"button-{lang}", "btc", "usdt"):
                self.assertIn(f'src="./assets/donate/{name}.svg"', repo)
            self.assertNotIn("./assets/qr/", repo)
            for text in (profile, repo):
                self.assertIn("<!-- donate:btc -->", text)
                self.assertEqual(text.count("```\n") // 2, 2)
                self.assertIn(BTC_OK[0], text)
                self.assertIn(ETH_MIXED[0], text)
                self.assertIn("ERC-20", text)
                self.assertIn("<details>", text)

    def test_el_repo_no_redirige_al_perfil(self):
        for lang in d.LANGS:
            repo = d.render(lang, repo=True)
            self.assertNotIn("github.com", repo)
            self.assertNotIn("href", repo)
            self.assertNotIn("](", repo)                         # ningún enlace Markdown
            self.assertIn(html.escape(d.INTRO_REPO[lang], quote=True), repo)   # «esta herramienta», no «mis herramientas»
            self.assertIn(d.EARMARK_REPO[lang].format(email=f"`{d.EMAIL_ADDR}`"), repo)
            self.assertNotIn(html.escape(d.INTRO[lang], quote=True), repo)

    def test_solo_btc_y_usdt(self):
        for lang in d.LANGS:
            text = d.render(lang) + d.render(lang, repo=True)
            for old in ("Monero", "XMR", "Zcash", "ZEC", "Tron", "TRC-20", "barra", "progress"):
                self.assertNotIn(old, text)

    def test_la_tarjeta_de_repo_lleva_el_texto_de_repo(self):
        for lang, word in (("es", "Esta herramienta"), ("en", "This tool")):
            self.assertIn(word, d.card_svg(lang, d.INTRO_REPO[lang]))
            self.assertNotIn(word, d.card_svg(lang))

    def test_la_tarjeta_habla_el_idioma_de_su_comando(self):
        for lang, mine, other in (("es", "donar", "donate"), ("en", "donate", "donar")):
            svg = d.card_svg(lang)
            self.assertIn(f">{d.CARD_USER}: ~/{mine}<", svg)
            self.assertIn(f">{d.CARD_USER}:~/{mine}$<", svg)
            self.assertNotIn(other, svg)
            self.assertIn(f"`$ ./{mine}.sh`", d.render(lang))

    def test_las_imagenes_del_perfil_son_las_que_genera_el_script(self):
        # si cambias un texto o el diseño y no ejecutas `sync --write`, el SVG publicado queda viejo
        for lang in d.LANGS:
            for name, svg in ((f"donate-{lang}.svg", d.button_svg(d.BUTTON_TEXT[lang])), (f"donate-card-{lang}.svg", d.card_svg(lang))):
                f = d.ROOT / "assets" / name
                if not f.is_file():
                    self.skipTest(f"falta assets/{name}")
                self.assertEqual(f.read_text(encoding="utf-8"), svg, f"assets/{name} está desfasado: python3 scripts/donate.py sync --write")

    def test_sin_direcciones_no_genera_nada(self):
        d.ADDRESSES.clear()
        self.assertEqual(d.render("es"), "")
        self.assertEqual(d.render("es", repo=True), "")

    def test_direccion_con_errata_detiene_la_generacion(self):
        d.ADDRESSES["btc"] = BTC_OK[0][:-1] + "5"
        with self.assertRaises(SystemExit):
            d.render("es")
        d.ADDRESSES["btc"] = BTC_OK[0]
        d.ADDRESSES["usdt"] = ETH_MIXED[0][:-1] + "0"
        with self.assertRaises(SystemExit):
            d.render("es")

    def test_un_aviso_no_detiene_y_sale_una_vez(self):
        d.ADDRESSES["usdt"] = ETH_LOWER[0]
        err = io.StringIO()
        with redirect_stderr(err):
            self.assertIn(ETH_LOWER[0], d.render("es"))
            d.render("en")
        self.assertEqual(err.getvalue().count("AVISO"), 1)

    def test_check_con_una_moneda_retirada_falla(self):
        d.ADDRESSES["xmr"] = "x"
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(d.cmd_check(None), 1)
        self.assertIn("Monero", out.getvalue())

    def test_check_ok_y_con_errata(self):
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(d.cmd_check(None), 0)
        self.assertIn("Todo correcto", out.getvalue())
        d.ADDRESSES["usdt"] = ETH_MIXED[0][:-1] + "0"
        with redirect_stdout(io.StringIO()):
            self.assertEqual(d.cmd_check(None), 1)

    def test_inject_idempotente_y_antes_de_contacto(self):
        block = d.render("es")
        once = d.inject_text(PROFILE, block)
        self.assertLess(once.index(d.START), once.index("./contacto.sh"))
        self.assertEqual(d.inject_text(once, block), once)
        changed = d.inject_text(once, block.replace("Apoyar", "Respaldar"))
        self.assertEqual(changed.count(d.START), 1)

    def test_marked_y_inject_conviven(self):
        marked = d.render("es", marked=True)
        readme = "a\n\n" + marked + "\n\n## `$ ./contacto.sh`\n"
        self.assertEqual(d.inject_text(readme, d.render("es")), readme)

    def test_marca_suelta_se_rechaza(self):
        with self.assertRaises(SystemExit):
            d.inject_text(f"x\n{d.START}\ny\n", "b")

    def test_ancho_del_banner(self):
        self.assertEqual(d._banner_width(PROFILE), 480)
        self.assertEqual(d._banner_width('<img width="900" src="./assets/banner2.svg">'), 800)   # tope
        self.assertIsNone(d._banner_width("sin banner"))


class Colocacion(unittest.TestCase):
    """Dónde y cómo se inserta el bloque en un README: encabezado de verdad y saltos de línea."""

    def test_un_encabezado_dentro_de_un_bloque_de_codigo_no_cuenta(self):
        casos = {"```": "```md\n## `$ ./contacto.sh`\n```", "~~~": "~~~\n## `$ ./contacto.sh`\n~~~",
                 "valla larga": "````md\n```\n## `$ ./contacto.sh`\n```\n````"}   # el ``` de dentro no cierra una valla de 4
        for nombre, code in casos.items():
            text = f"# P\n\n{code}\n\n## `$ ./contacto.sh`\n\ncorreo\n"
            out = d.inject_text(text, "BLOQUE")
            self.assertGreater(out.index(d.START), out.index(code) + len(code), nombre)       # fuera del código…
            self.assertLess(out.index(d.START), out.rindex("## `$ ./contacto.sh`"), nombre)   # …y antes del contacto de verdad
            self.assertEqual(d.inject_text(out, "BLOQUE"), out, nombre)

    def test_una_valla_cerrada_no_oculta_los_encabezados_posteriores(self):
        text = "# P\n\n```\ncódigo\n```\n\n## `$ ./contact.sh`\n\nx\n"
        out = d.inject_text(text, "BLOQUE")
        self.assertLess(out.index(d.START), out.index("./contact.sh"))
        self.assertGreater(out.index(d.START), out.index("código"))

    def test_sin_encabezado_de_contacto_va_al_final(self):
        out = d.inject_text("# P\n\ntexto", "BLOQUE")
        self.assertTrue(out.rstrip().endswith(d.END))
        self.assertEqual(d.inject_text(out, "BLOQUE"), out)

    def test_los_saltos_de_linea_crlf_se_respetan(self):
        for text in ("# X\r\n\r\n## `$ ./contact.sh`\r\n\r\nx\r\n", "# X\r\n\r\ntexto sin contacto ni salto final"):
            out = d.inject_text(text, "uno\ndos")
            self.assertNotIn("\n", out.replace("\r\n", ""), text)         # ningún LF suelto
            self.assertEqual(d.inject_text(out, "uno\ndos"), out, text)   # idempotente
        self.assertNotIn("\r", d.inject_text("# X\n\n## `$ ./contact.sh`\n\nx\n", "uno\ndos"))   # LF sigue en LF
        viejo = "# X\r\n\r\n" + "a\r\n" * 8 + f"{d.START}\nviejo\n{d.END}\r\n"                   # LF dentro de un CRLF
        self.assertNotIn("\n", d.inject_text(viejo, "nuevo").replace("\r\n", ""))


class Perfil(unittest.TestCase):
    """Tu perfil tal como está en disco (con tus direcciones reales): ni README ni QR pueden quedar desfasados."""

    def test_los_readme_y_las_paginas_son_lo_que_genera_build_py(self):
        # Los README y los bloques de contacto de Únete/Join no se editan a mano: cambia build.py y ejecútalo.
        try:
            import build
        except ImportError:
            self.skipTest("falta scripts/build.py")
        for lang, name in build.FILES.items():
            f = d.ROOT / name
            if f.is_file():
                self.assertEqual(f.read_text(encoding="utf-8"), build.render(lang), f"{name} está desfasado: python3 scripts/build.py")
            page = d.ROOT / build.PAGES[lang]
            if page.is_file():
                text = page.read_text(encoding="utf-8")
                want = build.PAGE_BLOCK.sub(lambda m: f"{m.group(1)}\n{build.page_contact(lang)}\n{m.group(2)}", text)
                self.assertEqual(text, want, f"{page.name}: el bloque de contacto está desfasado: python3 scripts/build.py")

    def test_readme_qr_y_kit_coinciden_con_direcciones_ini(self):
        # verify incluye el kit de los repos (../DONACIONES-REPOS) si existe; si no, solo README y QR del perfil
        with redirect_stdout(io.StringIO()) as out:
            code = d.cmd_verify(None)
        self.assertEqual(code, 0, out.getvalue())

    def test_los_qr_en_disco_se_leen_y_son_los_de_direcciones_ini(self):
        # verify solo compara la huella escrita en el SVG; aquí se decodifica el dibujo, a su tamaño real en pantalla
        folders = (d.ROOT / "assets" / "qr", d.kit_dir() / d.KIT_ASSETS)
        qrs = [(key, f / f"{key}.svg") for f in folders for key in d.ADDRESSES if (f / f"{key}.svg").is_file()]
        if not qrs:
            self.skipTest("no hay QR en disco")
        for key, svg in qrs:
            self.assertEqual(decode_qr(svg), [d.ADDRESSES[key]], str(svg))


@unittest.skipUnless(d._has_segno(), "segno no instalado (solo lo usan los QR)")
class Sync(unittest.TestCase):
    """`sync` y `verify` sobre una carpeta temporal: nunca tocan tu perfil."""

    def setUp(self):
        self._saved = (dict(d.ADDRESSES), d.ROOT, d._has_segno)
        self.tmp = Path(tempfile.mkdtemp())
        for name in ("README.md", "README.es.md"):
            (self.tmp / name).write_text(PROFILE, encoding="utf-8")
        d.ROOT = self.tmp
        d._warned.clear()
        d.ADDRESSES.clear()
        d.ADDRESSES.update(btc=BTC_OK[0], usdt=ETH_MIXED[0])

    def tearDown(self):
        d.ADDRESSES.clear()
        d.ADDRESSES.update(self._saved[0])
        d.ROOT, d._has_segno = self._saved[1], self._saved[2]
        shutil.rmtree(self.tmp, ignore_errors=True)

    def sync(self, write=True):
        with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()):
            code = d.cmd_sync(type("A", (), {"write": write})())
        return code, out.getvalue()

    def verify(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return d.cmd_verify(None)

    def test_simulacion_no_escribe_nada(self):
        before = sorted(p.name for p in self.tmp.rglob("*"))
        code, out = self.sync(write=False)
        self.assertEqual(code, 0)
        self.assertEqual(sorted(p.name for p in self.tmp.rglob("*")), before)
        self.assertEqual((self.tmp / "README.md").read_text(encoding="utf-8"), PROFILE)

    def test_write_deja_todo_verificado_y_repetirlo_no_cambia_nada(self):
        self.assertEqual(self.sync()[0], 0)
        self.assertEqual(sorted(p.name for p in (self.tmp / "assets" / "qr").glob("*.svg")), ["btc.svg", "usdt.svg"])
        for name in ("README.md", "README.es.md"):
            text = (self.tmp / name).read_text(encoding="utf-8")
            self.assertIn(BTC_OK[0], text)
            self.assertLess(text.index(d.START), text.index("./contacto.sh"))
        self.assertEqual(self.verify(), 0)
        snap = {p.name: p.read_bytes() for p in self.tmp.rglob("*") if p.is_file()}
        self.assertEqual(self.sync()[0], 0)
        self.assertEqual({p.name: p.read_bytes() for p in self.tmp.rglob("*") if p.is_file()}, snap)

    def test_la_tarjeta_usa_el_ancho_del_banner(self):
        self.sync()
        self.assertIn('donate-card-en.svg" width="480"', (self.tmp / "README.md").read_text(encoding="utf-8"))

    def test_verify_detecta_una_direccion_cambiada_a_mano(self):
        self.sync()
        f = self.tmp / "README.md"
        f.write_text(f.read_text(encoding="utf-8").replace(BTC_OK[0], BTC_OK[0][:-1] + "5"), encoding="utf-8")
        self.assertEqual(self.verify(), 1)
        self.assertEqual(self.sync()[0], 0)                  # y sync la repara
        self.assertEqual(self.verify(), 0)

    def test_verify_detecta_un_qr_viejo(self):
        self.sync()
        d.ADDRESSES["usdt"] = ETH_MIXED[1]
        self.assertEqual(self.verify(), 1)

    def test_verify_detecta_un_qr_de_otro_tamano_y_sync_lo_repara(self):
        with mock.patch.object(d, "QR_SCALE", 1):   # el tamaño que tenían los QR antes de existir QR_SCALE
            self.sync()
        self.assertEqual(self.verify(), 1)
        self.assertEqual(self.sync()[0], 0)
        self.assertEqual(self.verify(), 0)

    def test_sin_segno_se_detiene_antes_de_escribir_nada(self):
        d._has_segno = lambda: False
        with self.assertRaises(SystemExit):
            self.sync()
        self.assertEqual(sorted(p.name for p in self.tmp.rglob("*")), ["README.es.md", "README.md"])

    def test_con_direcciones_vacias_no_escribe_nada(self):
        d.ADDRESSES.clear()
        code, out = self.sync()
        self.assertEqual(code, 0)
        self.assertIn("nada que insertar", out)
        self.assertEqual((self.tmp / "README.md").read_text(encoding="utf-8"), PROFILE)
        self.assertFalse((self.tmp / "assets").exists())


@unittest.skipUnless(d._has_segno(), "segno no instalado (solo lo usan los QR)")
class Kit(unittest.TestCase):
    """Kit de los repos (`repos`) en una carpeta temporal: nunca toca tu perfil ni tu kit real."""

    NAMES = sorted(["bloque-es.md", "bloque-en.md", *(f"assets/donate/{n}" for n in (
        "button-es.svg", "button-en.svg", "card-es.svg", "card-en.svg", "btc.svg", "usdt.svg"))])

    def setUp(self):
        self._saved = (dict(d.ADDRESSES), d.ROOT, d._has_segno)
        self.tmp = Path(tempfile.mkdtemp())
        self.out = self.tmp / "kit"
        d.ROOT = self.tmp / "perfil"          # sin README ni QR: verify solo mira el kit
        d._warned.clear()
        d.ADDRESSES.clear()
        d.ADDRESSES.update(btc=BTC_OK[0], usdt=ETH_MIXED[0])

    def tearDown(self):
        d.ADDRESSES.clear()
        d.ADDRESSES.update(self._saved[0])
        d.ROOT, d._has_segno = self._saved[1], self._saved[2]
        shutil.rmtree(self.tmp, ignore_errors=True)

    def repos(self, write=True):
        with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()):
            code = d.cmd_repos(type("A", (), {"write": write, "out": str(self.out)})())
        return code, out.getvalue()

    def verify(self, *repos):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return d.cmd_verify(type("A", (), {"out": str(self.out), "repo": [str(r) for r in repos]})())

    def make_repo(self):
        """Un repo de herramienta tal como lo deja el kit: assets/ copiada y cada bloque pegado en su README."""
        self.repos()
        repo = self.tmp / "herramienta"
        shutil.copytree(self.out / "assets", repo / "assets")
        for lang, readme in (("es", "README.es.md"), ("en", "README.md")):
            (repo / readme).write_text("# Herramienta\n\n" + (self.out / f"bloque-{lang}.md").read_text(encoding="utf-8"), encoding="utf-8")
        return repo

    def files(self):
        return {str(p.relative_to(self.out)): p.read_bytes() for p in self.out.rglob("*") if p.is_file()}

    def test_la_carpeta_por_defecto_esta_junto_al_perfil_no_dentro(self):
        self.assertEqual(d.kit_dir(), d.ROOT.parent / d.KIT_NAME)
        self.assertNotIn(d.ROOT, d.kit_dir().parents)

    def test_simulacion_no_escribe_nada(self):
        code, out = self.repos(write=False)
        self.assertEqual(code, 0)
        self.assertFalse(self.out.exists())
        self.assertIn("se crearía", out)

    def test_write_crea_el_kit_completo_y_verify_lo_da_por_bueno(self):
        self.assertEqual(self.repos()[0], 0)
        self.assertEqual(sorted(self.files()), self.NAMES)
        self.assertEqual(self.verify(), 0)

    def test_todas_las_imagenes_de_los_bloques_estan_en_el_kit(self):
        import re
        self.repos()
        for lang in d.LANGS:
            text = (self.out / f"bloque-{lang}.md").read_text(encoding="utf-8")
            srcs = re.findall(r'src="\./([^"]+)"', text)
            self.assertEqual(len(srcs), 4, srcs)                     # tarjeta, botón y dos QR
            for src in srcs:
                self.assertTrue((self.out / src).is_file(), f"bloque-{lang}.md apunta a {src}, que no está en el kit")

    def test_repetirlo_no_cambia_nada(self):
        self.repos()
        snap = self.files()
        code, out = self.repos()
        self.assertEqual((code, self.files()), (0, snap))
        self.assertNotIn("nuevo", out)
        self.assertNotIn("actualizado", out)

    def test_el_bloque_del_kit_es_el_que_se_pega_en_el_repo(self):
        self.repos()
        for lang in d.LANGS:
            self.assertEqual((self.out / f"bloque-{lang}.md").read_text(encoding="utf-8"),
                             d.render(lang, repo=True, marked=True) + "\n")

    def test_verify_detecta_una_direccion_cambiada_en_un_bloque(self):
        self.repos()
        f = self.out / "bloque-en.md"
        f.write_text(f.read_text(encoding="utf-8").replace(BTC_OK[0], BTC_OK[0][:-1] + "5"), encoding="utf-8")
        self.assertEqual(self.verify(), 1)
        self.assertEqual(self.repos()[0], 0)                          # `repos --write` lo repara
        self.assertEqual(self.verify(), 0)

    def test_verify_detecta_un_qr_viejo_y_un_archivo_que_falta(self):
        self.repos()
        d.ADDRESSES["usdt"] = ETH_MIXED[1]                            # cambia la dirección y no el kit
        self.assertEqual(self.verify(), 1)
        d.ADDRESSES["usdt"] = ETH_MIXED[0]
        self.assertEqual(self.verify(), 0)
        (self.out / "assets" / "donate" / "btc.svg").unlink()
        self.assertEqual(self.verify(), 1)

    def test_verify_repo_da_por_bueno_el_que_copia_el_kit(self):
        repo = self.make_repo()
        before = {str(p.relative_to(repo)): p.read_bytes() for p in repo.rglob("*") if p.is_file()}
        self.assertEqual(self.verify(repo), 0)
        self.assertEqual({str(p.relative_to(repo)): p.read_bytes() for p in repo.rglob("*") if p.is_file()}, before)   # solo lectura

    def test_verify_repo_detecta_qr_antiguo_direccion_cambiada_y_bloque_que_falta(self):
        repo = self.make_repo()
        qr = repo / "assets" / "donate" / "btc.svg"
        good = qr.read_text(encoding="utf-8")
        with mock.patch.object(d, "QR_SCALE", 1):                      # el QR de antes del 75 %
            qr.write_text(d.qr_svg(COIN["btc"], BTC_OK[0]), encoding="utf-8")
        self.assertEqual(self.verify(repo), 1)
        qr.write_text(good, encoding="utf-8")
        self.assertEqual(self.verify(repo), 0)
        readme = repo / "README.md"
        text = readme.read_text(encoding="utf-8")
        readme.write_text(text.replace(ETH_MIXED[0], ETH_MIXED[1]), encoding="utf-8")
        self.assertEqual(self.verify(repo), 1)
        readme.write_text("# Herramienta\n", encoding="utf-8")         # sin bloque de donaciones
        self.assertEqual(self.verify(repo), 1)

    def test_verify_repo_con_ruta_inexistente_o_sin_readme_falla(self):
        self.assertEqual(self.verify(self.tmp / "no-existe"), 1)
        (self.tmp / "vacio").mkdir()
        self.assertEqual(self.verify(self.tmp / "vacio"), 1)

    def test_verify_detecta_un_qr_de_otro_tamano_y_repos_lo_repara(self):
        with mock.patch.object(d, "QR_SCALE", 1):   # el tamaño que tenían los QR antes de existir QR_SCALE
            self.repos()
        self.assertEqual(self.verify(), 1)
        self.assertEqual(self.repos()[0], 0)
        self.assertEqual(self.verify(), 0)

    def test_verify_detecta_una_imagen_desfasada_y_un_bloque_que_falta(self):
        self.repos()
        f = self.out / "assets" / "donate" / "card-es.svg"
        f.write_text(f.read_text(encoding="utf-8").replace("herramienta", "cosa"), encoding="utf-8")
        self.assertEqual(self.verify(), 1)
        self.repos()
        (self.out / "bloque-es.md").unlink()
        self.assertEqual(self.verify(), 1)

    def test_sin_segno_o_sin_direcciones_se_detiene_antes_de_escribir(self):
        d._has_segno = lambda: False
        with self.assertRaises(SystemExit):
            self.repos()
        d._has_segno = self._saved[2]
        d.ADDRESSES.clear()
        with self.assertRaises(SystemExit):
            self.repos()
        self.assertFalse(self.out.exists())

    def test_los_qr_del_kit_se_leen_con_un_decodificador_independiente(self):
        self.repos()
        for key, addr in d.ADDRESSES.items():
            for scale in (1, 3):   # 1 = tamaño real en pantalla; 3 = pantalla de alta densidad
                self.assertEqual(decode_qr(self.out / "assets" / "donate" / f"{key}.svg", scale), [addr], f"{key} a {scale}x")

    def test_el_qr_se_muestra_a_qr_scale_de_su_viewbox(self):
        import re
        for key, addr in d.ADDRESSES.items():
            head = re.search(r"<svg[^>]*>", d.qr_svg(COIN[key], addr)).group(0)
            w, h = (float(re.search(rf' {a}="([\d.]+)"', head).group(1)) for a in ("width", "height"))
            vw, vh = map(float, re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', head).groups())
            self.assertAlmostEqual(w, vw * d.QR_SCALE, places=2, msg=key)
            self.assertAlmostEqual(h, vh * d.QR_SCALE, places=2, msg=key)


if __name__ == "__main__":
    unittest.main(verbosity=1)
