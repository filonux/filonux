#!/usr/bin/env python3
"""Donaciones del perfil (ES/EN): Bitcoin y USDT en Ethereum, desde scripts/direcciones.ini.

    python3 scripts/donate.py check            # valida las direcciones
    python3 scripts/donate.py sync [--write]    # check → botón, tarjeta y QR → README del perfil → verify (sin --write, simula)
    python3 scripts/donate.py verify [--out CARPETA] [--repo CARPETA ...]   # ¿README, QR, kit y repos coinciden con direcciones.ini?
    python3 scripts/donate.py repos [--write] [--out CARPETA]   # kit para los repos: carpeta de imágenes + bloques de texto

Solo biblioteca estándar (los QR piden `segno`). Con direcciones.ini vacío no se genera nada.

DIRECCIONES
  Solo en scripts/direcciones.ini, sección [general]: `btc` y `usdt` (esta, red Ethereum: 0x…). Para cambiar una, edítala
  ahí y ejecuta `sync --write` y `repos --write`. Cada dirección se valida al generar (checksum bech32/Base58 en BTC;
  EIP-55 en USDT): ante una errata el script se detiene. Los AVISOS no bloquean: léelos. Nunca pongas aquí frases de
  recuperación ni claves.

REPOS DE TUS HERRAMIENTAS
  Cada repo lleva su propia sección de donaciones (botón, direcciones y QR), sin redirigir al perfil. `repos --write`
  prepara, junto a la carpeta del perfil (no dentro), la carpeta DONACIONES-REPOS/ con:
    assets/donate/   botón, tarjeta y QR (ES y EN): se sube a la carpeta assets/ de CADA repo
    bloque-es.md     texto para pegar al final de README.es.md
    bloque-en.md     texto para pegar al final de README.md
  Si el README ya lleva el bloque (cambio de dirección), sustitúyelo entero, marcas incluidas (<!-- donate:start/end -->).
  Los repos se editan a mano; este script no los toca. `verify --repo CARPETA ...` los comprueba sin modificarlos.

ENGANCHE EN build.py (ya hecho; build.py y `sync` producen el mismo README del perfil)
  d = donate.render(lang, marked=True, width=BANNER_WIDTH)   # \"\" mientras direcciones.ini esté vacío
"""
import argparse
import configparser
import hashlib
import html
import re
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INI_PATH = Path(__file__).resolve().with_name("direcciones.ini")


def L(es, en):
    return {"es": es, "en": en}


# ── DATOS ─────────────────────────────────────────────────────────────────────

COINS = [
    {"key": "btc", "kind": "btc", "name": "Bitcoin", "ticker": "BTC",
     "network": L("red Bitcoin", "Bitcoin network"),
     "warn": L("Envía solo BTC por la red Bitcoin.", "Send only BTC on the Bitcoin network.")},
    {"key": "usdt", "kind": "eth", "name": "Tether", "ticker": "USDT",
     "network": L("red Ethereum (ERC-20)", "Ethereum network (ERC-20)"),
     "warn": L("Envía solo USDT por la red Ethereum (ERC-20); por otra red podrían perderse los fondos.",
               "Send only USDT on the Ethereum network (ERC-20); other networks could lose the funds.")},
]
RETIRED = {"xmr": "Monero", "zec": "Zcash"}   # monedas quitadas de momento: `check` avisa si siguen en el .ini
USDT_CONTRACT = "0xdac17f958d2ee523a2206206994597c13d831ec7"   # contrato de USDT: no es un monedero


def _fail(msg):
    raise SystemExit(f"donate.py: {msg}")


def load_ini(path=None):
    """Claves de [general] en direcciones.ini. Falta el archivo → {}: no se genera nada."""
    path = Path(path or INI_PATH)
    if not path.is_file():
        return {}
    cp = configparser.ConfigParser(interpolation=None, inline_comment_prefixes=("#", ";"), strict=True)
    try:
        cp.read_string(path.read_text(encoding="utf-8-sig"), source=path.name)
    except configparser.Error as e:
        _fail(f"{path.name} no se puede leer (cada línea debe ser «clave = valor»): {' '.join(str(e).split())}")
    general = {}
    for name in cp.sections():
        if name.lower() != "general":
            _fail(f"{path.name}: solo existe la sección [general]; borra [{name}] (los repos se editan a mano, con `repos`).")
        general = {k: v.strip() for k, v in cp.items(name)}
    return general


ADDRESSES = load_ini()   # lo sustituyen las pruebas. Vacío = se omite.

EMAIL_ADDR = "filonux@proton.me"

# ── TEXTOS (editables; son el compromiso que asumes: revísalos una vez con tu gestor) ────────────────────────────
# El perfil habla de «mis herramientas»; cada repo, de «esta herramienta» (INTRO_REPO, EARMARK_REPO).
CMD = L(es="./donar.sh", en="./donate.sh")
INTRO = L(es="Mis herramientas son gratuitas. Si te ahorran tiempo, puedes apoyarlas: es voluntario y no se espera nada a cambio.",
          en="My tools are free. If they save you time, you can support them — it's voluntary and nothing is expected in return.")
INTRO_REPO = L(es="Esta herramienta es gratuita. Si te ahorra tiempo, puedes apoyarla: es voluntario y no se espera nada a cambio.",
               en="This tool is free. If it saves you time, you can support it — it's voluntary and nothing is expected in return.")
BUTTON_TEXT = L(es="Apoyar mi trabajo", en="Support my work")   # el mismo botón en el perfil y en los repos
TERMS = L(es="Las donaciones son voluntarias y no reembolsables.", en="Donations are voluntary and non-refundable.")
EARMARK = L(es="¿Quieres destinarlas a un proyecto concreto? Escríbeme a {email} con el nombre del proyecto y el hash de la transacción (opcional).",
            en="Want it to go to a specific project? Email {email} with the project name and the transaction hash (optional).")
EARMARK_REPO = L(es="¿Quieres destinarlas a este proyecto? Escríbeme a {email} con el nombre del proyecto y el hash de la transacción (opcional).",
                 en="Want it to go to this project? Email {email} with the project name and the transaction hash (optional).")
QR_ALT = L(es="QR de {name}", en="{name} QR code")

# ── ASPECTO (los mismos valores que assets/banner2.svg y assets/email.svg del perfil) ───────────────────────────
CARD_USER = "filonux@nix"   # el prompt del banner. Su carpeta sale de CMD (./donar.sh → ~/donar · ./donate.sh → ~/donate)
CARD_COLS = 45              # caracteres por línea tras «# »: caben en los 440 px de la tarjeta a 14 px
CARD_WIDTH = 480            # ancho por defecto de la tarjeta; `sync` lo lee del banner del README para igualar la escala
BUTTON_W = 222              # como assets/email.svg
QR_SCALE = 0.75             # tamaño del QR respecto a su viewBox: 1 = el de diseño, 0.75 = un 25 % menos

START, END = "<!-- donate:start -->", "<!-- donate:end -->"
LANGS = ("es", "en")

# ── KIT DE LOS REPOS ──────────────────────────────────────────────────────────
# Imágenes y rutas de cada README. El perfil las tiene en assets/ y assets/qr/; cada repo, en su propia carpeta
# assets/donate/ (la del kit), para no pisar nada de lo que el repo ya tenga en assets/.
KIT_NAME = "DONACIONES-REPOS"   # carpeta del kit, junto a la del perfil
KIT_ASSETS = "assets/donate"    # dentro del kit y dentro de cada repo
PROFILE_IMG = {"button": "./assets/donate-{lang}.svg", "card": "./assets/donate-card-{lang}.svg", "qr": "./assets/qr/{key}.svg"}
REPO_IMG = {"button": f"./{KIT_ASSETS}/button-{{lang}}.svg", "card": f"./{KIT_ASSETS}/card-{{lang}}.svg",
            "qr": f"./{KIT_ASSETS}/{{key}}.svg"}


# ── HASH: Keccak-256 ──────────────────────────────────────────────────────────
# Ethereum usa el Keccak original (NO es SHA3-256: otro relleno) y hashlib no lo trae. Solo para el checksum EIP-55;
# comprobado contra vectores conocidos en scripts/test_donate.py.

_RC = (0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000, 0x000000000000808B,
       0x0000000080000001, 0x8000000080008081, 0x8000000000008009, 0x000000000000008A, 0x0000000000000088,
       0x0000000080008009, 0x000000008000000A, 0x000000008000808B, 0x800000000000008B, 0x8000000000008089,
       0x8000000000008003, 0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
       0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008)
_ROT = ((0, 36, 3, 41, 18), (1, 44, 10, 45, 2), (62, 6, 43, 15, 61), (28, 55, 25, 21, 56), (27, 20, 39, 8, 14))
_M64 = (1 << 64) - 1


def _rol(v, n):
    n %= 64
    return ((v << n) | (v >> (64 - n))) & _M64 if n else v


def _keccak_f(a):
    for rc in _RC:
        c = [a[x][0] ^ a[x][1] ^ a[x][2] ^ a[x][3] ^ a[x][4] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rol(c[(x + 1) % 5], 1) for x in range(5)]
        a = [[a[x][y] ^ d[x] for y in range(5)] for x in range(5)]
        b = [[0] * 5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                b[y][(2 * x + 3 * y) % 5] = _rol(a[x][y], _ROT[x][y])
        a = [[b[x][y] ^ (~b[(x + 1) % 5][y] & b[(x + 2) % 5][y]) for y in range(5)] for x in range(5)]
        a[0][0] ^= rc
    return a


def keccak256(data):
    rate = 136
    msg = bytearray(data) + b"\x01"
    msg += b"\x00" * (-len(msg) % rate)
    msg[-1] |= 0x80
    st = [[0] * 5 for _ in range(5)]
    for off in range(0, len(msg), rate):
        for i in range(rate // 8):
            st[i % 5][i // 5] ^= int.from_bytes(msg[off + 8 * i: off + 8 * i + 8], "little")
        st = _keccak_f(st)
    return b"".join(st[i % 5][i // 5].to_bytes(8, "little") for i in range(4))


# ── VALIDACIÓN ────────────────────────────────────────────────────────────────
# Cada validador devuelve (nivel, mensaje): "ok", "error" (se detiene) o "warn" (se avisa y se sigue).

_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_B32 = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
OK = ("ok", "")


def _b58_int(s):
    n = 0
    for ch in s:
        i = _B58.find(ch)
        if i < 0:
            return None
        n = n * 58 + i
    return n


def _base58check(addr, prefixes):
    """Base58Check de Bitcoin (1… y 3…): prefijo + hash de 20 bytes + 4 de checksum (doble SHA-256)."""
    n = _b58_int(addr)
    if n is None:
        return False
    try:
        raw = n.to_bytes(len(next(iter(prefixes))) + 20 + 4, "big")
    except OverflowError:
        return False
    # Los «1» iniciales equivalen a bytes cero: si no cuadran, la cadena no es la codificación canónica.
    if len(addr) - len(addr.lstrip("1")) != len(raw) - len(raw.lstrip(b"\0")):
        return False
    if not any(raw.startswith(p) for p in prefixes):
        return False
    return hashlib.sha256(hashlib.sha256(raw[:-4]).digest()).digest()[:4] == raw[-4:]


def _polymod(values):
    gen = (0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3)
    chk = 1
    for v in values:
        top = chk >> 25
        chk = ((chk & 0x1FFFFFF) << 5) ^ v
        for i in range(5):
            if (top >> i) & 1:
                chk ^= gen[i]
    return chk


def _bech32(addr, hrp, spec, maxlen=90):
    """Valores de 5 bits (sin checksum) si `addr` es Bech32 o Bech32m válida con ese hrp; si no, None."""
    if addr != addr.lower() and addr != addr.upper():
        return None
    a = addr.lower()
    pos = a.rfind("1")
    if (maxlen and len(a) > maxlen) or pos < 1 or len(a) - pos - 1 < 6 or a[:pos] != hrp:
        return None
    if any(c not in _B32 for c in a[pos + 1:]):
        return None
    vals = [_B32.find(c) for c in a[pos + 1:]]
    expand = [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]
    const = 1 if spec == "bech32" else 0x2BC830A3
    return vals[:-6] if _polymod(expand + vals) == const else None


def _convertbits(data, frombits, tobits, pad):
    acc = bits = 0
    out, maxv, max_acc = [], (1 << tobits) - 1, (1 << (frombits + tobits - 1)) - 1
    for v in data:
        if v < 0 or v >> frombits:
            return None
        acc = ((acc << frombits) | v) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            out.append((acc >> bits) & maxv)
    if pad:
        if bits:
            out.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or (acc << (tobits - bits)) & maxv:
        return None
    return out


def _check_btc(addr):
    if addr.lower().startswith("bc1"):
        for spec in ("bech32", "bech32m"):
            vals = _bech32(addr, "bc", spec)
            if not vals:
                continue
            prog = _convertbits(vals[1:], 5, 8, False)
            ver = vals[0]
            if prog is None or ver > 16 or not 2 <= len(prog) <= 40:
                break
            if (ver == 0 and (spec != "bech32" or len(prog) not in (20, 32))) or (ver > 0 and spec != "bech32m"):
                break
            return OK
        return ("error", "el checksum de bc1... no cuadra (¿errata o dirección cortada?)")
    if _base58check(addr, {b"\x00", b"\x05"}):  # mainnet: P2PKH (1...) y P2SH (3...)
        return OK
    return ("error", "no es una dirección Bitcoin válida (mainnet) o tiene una errata")


def _check_eth(addr):
    """Dirección Ethereum (la del USDT ERC-20): 0x + 40 hex. Con mayúsculas y minúsculas mezcladas debe cumplir EIP-55."""
    if not re.fullmatch(r"0x[0-9a-fA-F]{40}", addr):
        return ("error", "una dirección Ethereum es «0x» + 40 caracteres hexadecimales (¿es de otra red, como Tron «T…» o Bitcoin?)")
    body = addr[2:]
    if addr.lower() == USDT_CONTRACT:
        return ("error", "es el contrato del token USDT, no un monedero: los fondos enviados ahí se pierden")
    if body in (body.lower(), body.upper()):
        return ("warn", "no lleva mayúsculas y minúsculas mezcladas (checksum EIP-55): es válida, pero el script no puede detectar erratas; "
                        "cópiala del monedero con «Copiar»")
    digest = keccak256(body.lower().encode()).hex()
    good = "".join(ch.upper() if int(digest[i], 16) >= 8 else ch for i, ch in enumerate(body.lower()))
    return OK if body == good else ("error", "el checksum EIP-55 (mayúsculas/minúsculas) no cuadra (¿errata?)")


_CHECKS = {"btc": _check_btc, "eth": _check_eth}


def check_address(coin, addr):
    """(nivel, mensaje) de una dirección ya limpia de espacios laterales."""
    return _CHECKS[coin["kind"]](addr)


def _style_note(coin, addr):
    """Aviso de forma (no de validez) sobre una dirección que ya pasó el checksum; \"\" si no hay nada que decir."""
    if coin["kind"] == "btc" and addr.startswith("BC1"):
        return "está en MAYÚSCULAS: es válida, pero se lee peor y los monederos la muestran en minúsculas; pásala a minúsculas"
    return ""


def _validate(coin, addr):
    level, msg = check_address(coin, addr)
    if level == "ok" and _style_note(coin, addr):
        return "warn", _style_note(coin, addr)
    return level, msg


_warned = set()


def general_addresses():
    """[(moneda, dirección)] de las monedas con dirección. Si alguna no es válida, se detiene (los avisos salen una vez)."""
    out = []
    for c in COINS:
        a = str(ADDRESSES.get(c["key"], "")).strip()
        if not a:
            continue
        level, msg = _validate(c, a)
        if level == "error":
            raise SystemExit(f"donate.py: la dirección de {c['name']} no es válida: {msg}. Corrígela en {INI_PATH.name}.")
        if level == "warn" and (c["key"], a) not in _warned:
            _warned.add((c["key"], a))
            print(f"donate.py: AVISO — {c['name']}: {msg}.", file=sys.stderr)
        out.append((c, a))
    return out


def fingerprint(addr):
    """Huella corta de una dirección. Va dentro de su QR: si cambias la dirección y no el QR, `verify` lo detecta."""
    return hashlib.sha256(addr.strip().encode("utf-8")).hexdigest()[:8]


# ── RENDER ────────────────────────────────────────────────────────────────────

def _coin_block(c, addr, lang, qr_src):
    """Una moneda: etiqueta `[BTC]`, dirección sola en su bloque de código (GitHub añade el botón de copiar) y su QR
    (`qr_src` es la ruta de la imagen). La marca <!-- donate:btc --> es invisible: solo sirve a `verify`."""
    title = f"`[{c['ticker']}]` **{c['name']}** · {c['network'][lang]}"
    alt = html.escape(QR_ALT[lang].format(name=c["name"]), quote=True)
    # Sin width/height: el tamaño lo fija el propio SVG (QR_SCALE), así cada módulo mide siempre lo mismo y se sigue escaneando
    return "\n".join([f"<!-- donate:{c['key']} -->", title, "", "```", addr, "```", "",
                      f'<p align="center"><img src="{qr_src.format(key=c["key"])}" alt="{alt}"></p>', "",
                      f"<sub>{c['warn'][lang]}</sub>", ""])


def _head(lang):
    return f"## `$ {CMD[lang]}`"


def _details(summary, body):
    """Desplegable. El <br> tras el <summary> da aire entre el botón y la primera moneda (GitHub no deja margen)."""
    return f"<details>\n<summary>{summary}</summary>\n\n<br>\n\n{body}\n</details>"


def _render_section(lang, coins, repo, width=None):
    """Sección de donaciones: tarjeta de terminal con la salida del comando del encabezado y, debajo, el botón que
    despliega las direcciones con su QR. Perfil y repos tienen el mismo diseño; cambian el texto («mis herramientas» /
    «esta herramienta») y la carpeta de las imágenes. Ningún bloque enlaza a otra página: cada README se basta solo."""
    img = REPO_IMG if repo else PROFILE_IMG
    intro, earmark = (INTRO_REPO, EARMARK_REPO) if repo else (INTRO, EARMARK)
    blocks = "\n".join(_coin_block(c, a, lang, img["qr"]) for c, a in coins)
    card = (f'<p align="center"><img src="{img["card"].format(lang=lang)}" width="{width or CARD_WIDTH}" '
            f'alt="{html.escape(intro[lang], quote=True)}"></p>')
    # align="absmiddle": el triángulo del <summary> queda a la altura del centro del botón, no de su base
    button = (f'<img src="{img["button"].format(lang=lang)}" width="{BUTTON_W}" height="44" align="absmiddle" '
              f'alt="{html.escape(BUTTON_TEXT[lang], quote=True)}">')
    email = f"`{EMAIL_ADDR}`"
    foot = f"<sub>{TERMS[lang]}<br>{earmark[lang].format(email=email)}</sub>\n"
    return "\n\n".join([_head(lang), card, f'<div align="center">\n\n{_details(button, blocks + chr(10) + foot)}\n\n</div>'])


def render(lang, repo=False, marked=False, width=None):
    """Bloque Markdown/HTML de la sección; vacío si no hay direcciones.

    repo=False  → perfil (imágenes en assets/ y assets/qr/).
    repo=True   → README de un repo (imágenes en assets/donate/; es el contenido de bloque-es.md y bloque-en.md).
    marked=True → envuelto entre las marcas que usan `sync`, `verify` y quien sustituya el bloque a mano.
    width       → ancho en px de la tarjeta; por defecto CARD_WIDTH. En el perfil, pon el del banner.
    """
    coins = general_addresses()
    if not coins:
        return ""
    body = _render_section(lang, coins, repo, width)
    return f"{START}\n{body}\n{END}" if marked else body


def _banner_width(text):
    """Ancho (px) al que un README muestra su banner, o None. La tarjeta se pinta a ese mismo ancho: así las dos
    imágenes (mismo SVG de 440 px) tienen la misma escala y el mismo tamaño de letra."""
    m = (re.search(r'<img\b[^>]*\bsrc="[^"]*banner[^"]*"[^>]*\bwidth="(\d+)"', text)
         or re.search(r'<img\b[^>]*\bwidth="(\d+)"[^>]*\bsrc="[^"]*banner[^"]*"', text))
    return min(max(int(m.group(1)), 320), 800) if m else None


_CONTACT_HEAD = re.compile(r"## `\$ \./contact")   # encabezado de contacto del perfil (./contact.sh · ./contacto.sh)
_FENCE = re.compile(r" {0,3}(`{3,}|~{3,})(.*)")


def _first_heading(text, head):
    """Posición de la primera línea de `text` que empieza como `head` y NO está dentro de un bloque de código vallado
    (``` o ~~~): un encabezado dentro de un ejemplo no es el de verdad, y colar ahí el bloque rompería el README."""
    fence, pos = None, 0
    for line in text.split("\n"):
        body = line.rstrip("\r")
        m = _FENCE.fullmatch(body)
        if fence:
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= fence[1] and not m.group(2).strip():
                fence = None
        elif m and not (m.group(1)[0] == "`" and "`" in m.group(2)):   # la «info» de una valla ``` no puede llevar «`»
            fence = (m.group(1)[0], len(m.group(1)))
        elif head.match(body):
            return pos
        pos += len(line) + 1
    return None


def _newline(text):
    """Salto de línea que usa `text`: CRLF si domina (README guardado en Windows), LF si no."""
    return "\r\n" if text.count("\r\n") * 2 > text.count("\n") else "\n"


def inject_text(text, block):
    """Reemplaza lo que hay entre las marcas o, si no existen, inserta el bloque antes del encabezado de contacto (o al
    final si no hay). Idempotente. Usa el salto de línea del README (LF o CRLF)."""
    nl = _newline(text)
    wrapped = f"{START}\n{block}\n{END}".replace("\n", nl)
    has_s, has_e = START in text, END in text
    if has_s != has_e:
        raise SystemExit("donate.py: hay una marca de inicio o de fin, pero no las dos; arréglalo a mano.")
    if has_s:
        return re.sub(re.escape(START) + r".*?" + re.escape(END), lambda m: wrapped, text, count=1, flags=re.S)
    at = _first_heading(text, _CONTACT_HEAD)
    if at is not None:
        return text[:at] + wrapped + nl + nl + text[at:]
    return text.rstrip("\r\n") + nl + nl + wrapped + nl


# ── IMÁGENES SVG ──────────────────────────────────────────────────────────────
# Mismos colores, tipografía y construcción que assets/banner2.svg y assets/email.svg del perfil. Ninguna imagen lleva
# direcciones escritas (salvo el QR, que lleva su huella): así hay un solo sitio donde cambiarlas.

_MONO = "ui-monospace, 'SFMono-Regular', Menlo, Consolas, 'Liberation Mono', monospace"
_BG, _BAR, _LINE, _GREEN, _AMBER, _AMBER_HI, _TEXT, _MUTED = ("#0d1117", "#161b22", "#30363d", "#7ee787", "#e3b341",
                                                              "#f2cc60", "#c9d1d9", "#8b949e")


def button_svg(text):
    """Botón 222×44 con la construcción de assets/email.svg (borde verde + haz ámbar que rodea el borde) y, tras el
    texto, el cursor de bloque del banner."""
    cw = 9  # monoespaciada a 15 px; textLength fija el ancho real aunque cambie la fuente
    width = len(text) * cw
    total = 16 + 11 + width + 4 + 9  # corazón + hueco + texto + hueco + cursor
    if total > BUTTON_W - 24:
        raise SystemExit(f"donate.py: «{text}» no cabe en un botón de {BUTTON_W} px (máx. {(BUTTON_W - 24 - 40) // cw} caracteres).")
    x0 = (BUTTON_W - total) / 2
    hx, tx = x0 - 2, x0 + 27  # el corazón ocupa de x=2 a x=18 dentro de su caja de 20
    cx = tx + width + 4
    t = html.escape(text, quote=True)
    beam = 'class="beam" x="1" y="1" width="220" height="42" rx="10" ry="10"'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{BUTTON_W}" height="44" viewBox="0 0 {BUTTON_W} 44" font-family="{_MONO}" role="img" aria-labelledby="title">
  <title id="title">{t}</title>
  <!-- Mismo haz de luz que email.svg: una vuelta cada 8 s solo con stroke-dashoffset (sin JS).
       Perímetro del borde = 2×200 + 2×22 + 2×π×10 = 506.83; cada dasharray suma justo eso para que el bucle no dé saltos.
       El cursor parpadea como el del banner. Con prefers-reduced-motion se oculta el haz y el cursor queda fijo. -->
  <style>
    .beam {{ animation: orbit 8s linear infinite }}
    @keyframes orbit {{ to {{ stroke-dashoffset: -506.83 }} }}
    .cursor {{ animation: blink 1.1s step-end infinite }}
    @keyframes blink {{ 50% {{ opacity: 0 }} }}
    @media (prefers-reduced-motion: reduce) {{ .beam {{ display: none }} .cursor {{ animation: none }} }}
  </style>
  <defs>
    <clipPath id="edge">
      <rect x="0.25" y="0.25" width="221.5" height="43.5" rx="10.75" ry="10.75"/>
    </clipPath>
    <filter id="bloom" x="-10%" y="-60%" width="120%" height="220%">
      <feGaussianBlur stdDeviation="2"/>
    </filter>
  </defs>
  <rect x="1" y="1" width="220" height="42" rx="10" ry="10" fill="{_BG}" stroke="{_GREEN}" stroke-opacity="0.6" stroke-width="1.5"/>
  <g clip-path="url(#edge)">
    <g fill="none" stroke="{_AMBER}" stroke-width="4" filter="url(#bloom)">
      <rect {beam} stroke-opacity="0.2" stroke-dasharray="120 386.83"/>
      <rect {beam} stroke-opacity="0.26" stroke-dasharray="0 60 60 386.83"/>
      <rect {beam} stroke-opacity="0.42" stroke-dasharray="0 96 24 386.83"/>
    </g>
  </g>
  <rect {beam} fill="none" stroke="{_AMBER_HI}" stroke-width="1.5" stroke-dasharray="0 96 24 386.83"/>
  <g transform="translate({hx:g} 12.9)" fill="none" stroke="{_AMBER}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
    <path d="M10 16.2C10 16.2 2 11.4 2 6.2C2 3.8 3.9 2 6.1 2C7.7 2 9.2 2.9 10 4.3C10.8 2.9 12.3 2 13.9 2C16.1 2 18 3.8 18 6.2C18 11.4 10 16.2 10 16.2Z"/>
  </g>
  <text x="{tx:g}" y="27" font-size="15" fill="{_GREEN}" textLength="{width}" lengthAdjust="spacing">{t}</text>
  <rect class="cursor" x="{cx:g}" y="14.5" width="9" height="16" fill="{_GREEN}" shape-rendering="crispEdges"/>
</svg>
'''


def card_svg(lang, intro=None):
    """Tarjeta de terminal de 440 px con la carrocería del banner (barra con tres puntos, prompt verde, cursor de
    bloque). El encabezado del README ya es el comando (`## $ ./donar.sh` o `./donate.sh`, según el idioma, como en el
    resto del perfil): la tarjeta muestra su salida —`intro`, por defecto INTRO; los repos usan INTRO_REPO— y acaba en
    un prompt con cursor, en la carpeta de ese mismo comando (~/donar o ~/donate). Las líneas se «imprimen» una vez al
    cargar; si el sistema pide menos movimiento, o el visor no anima, se ve directamente el estado final."""
    cw = 8.4  # avance de carácter a 14 px, el del banner
    intro = intro or INTRO[lang]
    lines = textwrap.wrap(intro, CARD_COLS, break_long_words=False, break_on_hyphens=False)
    if any(len(s) > CARD_COLS for s in lines):
        raise SystemExit(f"donate.py: una palabra del texto de la tarjeta ({lang}) no cabe ({CARD_COLS} caracteres por línea).")
    x0, y0, pitch = 20, 60, 21
    ys = [y0 + i * pitch for i in range(len(lines))]
    py = ys[-1] + pitch + 6
    h = py + 24
    esc = lambda s: html.escape(s, quote=False)
    rows, covers, css, t = [], [], [], 0.45
    for i, (y, s) in enumerate(zip(ys, lines)):
        n = len(s) + 2
        dur = n * 0.014
        rows.append(f'<text x="{x0}" y="{y}" textLength="{n * cw:g}" lengthAdjust="spacing"><tspan fill="{_GREEN}">#</tspan> {esc(s)}</text>')
        covers.append(f'<rect class="cv r{i}" transform="scale(0 1)" x="{x0 - 0.5}" y="{y - 14}" width="{n * cw + 1:g}" height="19" fill="{_BG}"/>')
        css.append(f".r{i} {{ animation: print {dur:.2f}s steps({n}, end) {t:.2f}s backwards }}")
        t += dur + 0.12
    folder = "~/" + Path(CMD[lang]).stem    # la carpeta del prompt es la del comando del encabezado: ~/donar · ~/donate
    prompt = f"{CARD_USER}:{folder}$"
    pn = len(prompt) + 1
    covers.append(f'<rect class="cv rp" transform="scale(0 1)" x="{x0 - 0.5}" y="{py - 14}" width="{(pn + 2) * cw:g}" height="22" fill="{_BG}"/>')
    css.append(f".rp {{ animation: print 0.01s steps(1, end) {t:.2f}s backwards }}")
    title = f"{CARD_USER}: {folder}"
    alt = html.escape(intro, quote=False)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="440" height="{h}" viewBox="0 0 440 {h}" font-family="{_MONO}" role="img" aria-labelledby="title">
  <title id="title">{alt}</title>
  <!-- Misma carrocería que banner2.svg. Efecto de «impresión»: cada línea está tapada por un rectángulo del color del
       fondo que se encoge de derecha a izquierda en pasos de un carácter. El estado de reposo (transform=scale(0 1)) es
       el final, con todo a la vista, así que un visor que no anime también ve el texto completo. -->
  <style>
    .cursor {{ animation: blink 1.1s step-end infinite }}
    @keyframes blink {{ 50% {{ opacity: 0 }} }}
    .cv {{ transform-box: fill-box; transform-origin: 100% 50% }}
    @keyframes print {{ from {{ transform: scaleX(1) }} to {{ transform: scaleX(0) }} }}
    {chr(10).join("    " + c for c in css).strip()}
    @media (prefers-reduced-motion: reduce) {{ .cursor {{ animation: none }} .cv {{ display: none }} }}
  </style>
  <defs>
    <clipPath id="card">
      <rect x="1" y="1" width="438" height="{h - 2}" rx="14" ry="14"/>
    </clipPath>
  </defs>
  <rect x="1" y="1" width="438" height="{h - 2}" rx="14" ry="14" fill="{_BG}" stroke="{_LINE}" stroke-width="1"/>
  <g clip-path="url(#card)">
    <rect x="0" y="0" width="440" height="32" fill="{_BAR}"/>
    <line x1="0" y1="32" x2="440" y2="32" stroke="{_LINE}" stroke-width="1"/>
    <circle cx="20" cy="16" r="5" fill="#ff5f56"/>
    <circle cx="38" cy="16" r="5" fill="#ffbd2e"/>
    <circle cx="56" cy="16" r="5" fill="#27c93f"/>
  </g>
  <text x="220" y="20" font-size="12" fill="{_MUTED}" text-anchor="middle" textLength="{len(title) * 7.2:g}" lengthAdjust="spacing">{esc(title)}</text>
  <g font-size="14" fill="{_TEXT}">
    {chr(10).join("    " + r for r in rows).strip()}
  </g>
  <text x="{x0}" y="{py}" font-size="14" fill="{_GREEN}" textLength="{len(prompt) * cw:g}" lengthAdjust="spacing">{esc(prompt)}</text>
  <rect class="cursor" x="{x0 + pn * cw:g}" y="{py - 11.5}" width="10" height="15" fill="{_GREEN}" shape-rendering="crispEdges"/>
  {chr(10).join("  " + c for c in covers).strip()}
</svg>
'''


def _qr_size_attrs(w, h):
    """width y height de un QR cuyo viewBox mide w×h: los escribe `qr_svg` y los exige `verify`."""
    return f'width="{w * QR_SCALE:g}" height="{h * QR_SCALE:g}"'


def qr_svg(coin, addr):
    """QR de la dirección tal cual (sin esquema bitcoin:/ethereum:, para que cualquier cartera lo lea) sobre una loseta
    blanca con la zona de silencio completa (4 módulos), dentro de una tarjeta oscura con las esquinas verdes de un
    visor. La tarjeta es oscura en los dos temas de GitHub, como el resto de imágenes del perfil. Lleva la huella de
    la dirección en un comentario: `verify` la compara con la del README."""
    import segno  # solo aquí: el resto del script no la necesita
    q = segno.make(addr, error="m" if len(addr) <= 100 else "l")
    rows = [list(r) for r in q.matrix]
    n, s, quiet, pad = len(rows), 5, 4, 24
    tile = (n + 2 * quiet) * s
    w, h = tile + 2 * pad, tile + 2 * pad + 26   # medida de diseño (viewBox); width/height la reducen a QR_SCALE
    d = []
    for y, row in enumerate(rows):
        x = 0
        while x < n:
            if row[x]:
                x2 = x
                while x2 < n and row[x2]:
                    x2 += 1
                d.append(f"M{x} {y}h{x2 - x}v1h-{x2 - x}z")
                x = x2
            else:
                x += 1
    o, arm = pad - 9, 14  # esquinas del visor: 9 px por fuera de la loseta
    a, b = o, o + tile + 18
    corners = (f"M{a} {a + arm}V{a}H{a + arm} M{b - arm} {a}H{b}V{a + arm} "
               f"M{a} {b - arm}V{b}H{a + arm} M{b - arm} {b}H{b}V{b - arm}")
    ticker = html.escape(f"[{coin['ticker']}]", quote=False)
    title = html.escape(QR_ALT["en"].format(name=coin["name"]), quote=False)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" {_qr_size_attrs(w, h)} viewBox="0 0 {w} {h}" font-family="{_MONO}" role="img" aria-labelledby="title">
  <!-- donate-qr key={coin["key"]} fp={fingerprint(addr)} -->
  <title id="title">{title}</title>
  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="14" ry="14" fill="{_BG}" stroke="{_LINE}"/>
  <rect x="{pad}" y="{pad}" width="{tile}" height="{tile}" rx="3" fill="#ffffff"/>
  <path transform="translate({pad + quiet * s} {pad + quiet * s}) scale({s})" fill="#0a3d1f" shape-rendering="crispEdges" d="{"".join(d)}"/>
  <path d="{corners}" fill="none" stroke="{_GREEN}" stroke-width="2.5" stroke-linecap="square"/>
  <text x="{w / 2:g}" y="{h - 14}" font-size="13" fill="{_GREEN}" text-anchor="middle">{ticker}</text>
</svg>
'''


# ── COMANDOS ──────────────────────────────────────────────────────────────────

def _short(a):
    return a if len(a) <= 18 else f"{a[:10]}…{a[-6:]}"


def _profile_readmes():
    """[(ruta, idioma)] de los README del perfil que existen; el idioma sale del nombre."""
    return [(ROOT / n, lang) for n, lang in (("README.md", "en"), ("README.es.md", "es")) if (ROOT / n).is_file()]


def cmd_check(_):
    bad = warned = 0
    keys = {c["key"] for c in COINS}
    for k in ADDRESSES:
        if k not in keys:
            hint = (f"{RETIRED[k]} está retirada de momento: borra la línea" if k in RETIRED
                    else f"válidas: {', '.join(sorted(keys))}")
            print(f"  ERROR: [general] tiene una clave desconocida: {k!r} ({hint})")
            bad += 1
    for c in COINS:
        a = str(ADDRESSES.get(c["key"], "")).strip()
        label = f"{c['name']:<9}"
        if not a:
            print(f"  {label}vacía → se omite")
            continue
        level, msg = _validate(c, a)
        tag = {"ok": "OK", "warn": "AVISO", "error": "ERROR"}[level]
        print(f"  {label}{tag:<6}{_short(a)}" + (f"  {msg}" if msg else ""))
        bad += level == "error"
        warned += level == "warn"
    if not any(str(v).strip() for v in ADDRESSES.values()):
        print(f"\nNo hay ninguna dirección: no se generará la sección hasta que rellenes {INI_PATH.name}.")
    print(f"\n{'Hay errores: corrígelos antes de publicar.' if bad else 'Todo correcto.'}" + (f" ({warned} aviso/s)" if warned else ""))
    return 1 if bad else 0


def cmd_assets(_):
    out = ROOT / "assets"
    out.mkdir(parents=True, exist_ok=True)
    for lang in LANGS:
        for name, svg in ((f"donate-{lang}.svg", button_svg(BUTTON_TEXT[lang])), (f"donate-card-{lang}.svg", card_svg(lang))):
            (out / name).write_text(svg, encoding="utf-8")
            print("escrito", (out / name).relative_to(ROOT))
    return 0


NEED_SEGNO = ("falta la librería segno (solo la usan los QR; el resto del script no la necesita). En Linux Mint,\n"
              "`pip install segno` suele fallar con «externally-managed-environment»: usa un entorno aparte,\n"
              "    python3 -m venv ~/.venvs/donar && ~/.venvs/donar/bin/pip install segno\n"
              "y lanza el script con  ~/.venvs/donar/bin/python scripts/donate.py …  (si falta venv: sudo apt install python3-venv)")


def _has_segno():
    try:
        import segno  # noqa: F401
    except ImportError:
        return False
    return True


def cmd_qr(_):
    if not _has_segno():
        raise SystemExit("donate.py: " + NEED_SEGNO)
    out = ROOT / "assets" / "qr"
    out.mkdir(parents=True, exist_ok=True)
    for c, a in general_addresses():
        (out / f"{c['key']}.svg").write_text(qr_svg(c, a), encoding="utf-8")
        print("escrito", (out / f"{c['key']}.svg").relative_to(ROOT))
    return 0


def kit_dir(out=None):
    """Carpeta del kit de los repos: junto a la del perfil (no dentro, para que `git add -A` no la suba con él), salvo
    que se indique otra con --out."""
    return Path(out).expanduser().resolve() if out else ROOT.parent / KIT_NAME


def kit_files(with_qr=True):
    """{ruta dentro del kit: contenido} de todo lo que va a los repos: los dos bloques de texto y la carpeta
    assets/donate/ (botón y tarjeta en ES y EN, y un QR por moneda). Sin `segno` no se pueden hacer los QR."""
    files = {}
    for lang in LANGS:
        files[f"bloque-{lang}.md"] = render(lang, repo=True, marked=True) + "\n"
        files[f"{KIT_ASSETS}/button-{lang}.svg"] = button_svg(BUTTON_TEXT[lang])
        files[f"{KIT_ASSETS}/card-{lang}.svg"] = card_svg(lang, INTRO_REPO[lang])
    if with_qr:
        for c, a in general_addresses():
            files[f"{KIT_ASSETS}/{c['key']}.svg"] = qr_svg(c, a)
    return files


def _read(path):
    """Texto de un archivo tal cual (sin traducir saltos de línea), o None si no existe."""
    if not path.is_file():
        return None
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def cmd_repos(args):
    """Prepara el kit de los repos (ver KIT_NAME). Sin --write solo muestra qué haría. Si falta segno, se detiene ANTES
    de escribir nada."""
    if not general_addresses():
        raise SystemExit(f"No hay direcciones en {INI_PATH.name}: nada que preparar.")
    segno = _has_segno()
    if not segno:
        if args.write:
            raise SystemExit("donate.py: " + NEED_SEGNO + "\nNo se ha escrito nada.")
        print("AVISO: " + NEED_SEGNO + "\nCon --write el script se detendría antes de escribir nada.\n")
    out = kit_dir(args.out)
    print(f"Kit de los repos: {out}" + ("" if args.write else "  (simulación: añade --write para aplicar)"))
    for rel, content in sorted(kit_files(with_qr=segno).items()):
        old = _read(out / rel)
        if old == content:
            state = "sin cambios"
        elif args.write:
            state = "nuevo" if old is None else "actualizado"
            (out / rel).parent.mkdir(parents=True, exist_ok=True)
            with open(out / rel, "w", encoding="utf-8", newline="") as fh:
                fh.write(content)
        else:
            state = "se crearía" if old is None else "se actualizaría"
        print(f"  {rel:<28}{state}")
    if not segno:
        print("  (los QR no se muestran: falta segno)")
    if not args.write:
        print("\nNada escrito. Revisa lo anterior y repite con --write.")
        return 0
    print()
    code = cmd_verify(args)
    print("\nEn cada repo: sube la carpeta assets/ del kit a su raíz (se fusiona con la que ya tiene) y pega bloque-es.md al\n"
          "final de README.es.md y bloque-en.md al final de README.md; si ya llevan el bloque, sustitúyelo entero, con sus\n"
          "marcas. Detalle en la guía, apartados 5 y 6.\n"
          "Comprueba cada repo con `verify --repo CARPETA ...`.")
    return code


def _inject(write):
    """Inserta/actualiza el bloque en los README del perfil. Devuelve [README cambiados]."""
    changed = []
    for f, lang in _profile_readmes():
        with open(f, encoding="utf-8", newline="") as fh:
            old = fh.read()
        new = inject_text(old, render(lang, width=_banner_width(old)))
        state = "sin cambios" if new == old else ("actualizado" if write else "se actualizaría")
        if new != old:
            changed.append(f)
            if write:
                with open(f, "w", encoding="utf-8", newline="") as fh:
                    fh.write(new)
        print(f"  {f.name}  [{lang}]  {state}")
    return changed


# ── VERIFY: ¿siguen coincidiendo README, QR, kit de los repos y direcciones.ini? ─────────────────────────────────────
# Sirve sobre todo tras editar un README a mano: lee las direcciones que HAY en el README o en el bloque de un repo (cada
# una va en su bloque de código, tras su marca <!-- donate:xxx -->) y las compara con direcciones.ini y con la huella de
# su QR (que además debe estar a la escala QR_SCALE). Una errata aquí es dinero enviado a otra dirección: por eso cada
# discrepancia es un ERROR.

def _block_addresses(block):
    """{clave de moneda: dirección} de las marcas <!-- donate:xxx --> y el primer bloque de código que sigue a cada una."""
    out = {}
    parts = re.split(r"<!-- donate:(btc|usdt) -->", block)
    for key, seg in zip(parts[1::2], parts[2::2]):
        m = re.search(r"^```[^\n]*\n(.*?)\n```", seg, re.M | re.S)
        out[key] = m.group(1).strip() if m else ""
    return out


def _qr_fp(path):
    """Huella escrita en un QR generado por este script, o None si no la tiene."""
    m = re.search(r"donate-qr key=\w+ fp=([0-9a-f]{8})", path.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def _qr_at_scale(path):
    """¿El QR se pinta a QR_SCALE de su viewBox? Uno hecho con otro valor conserva el tamaño de entonces."""
    head = re.search(r"<svg\b[^>]*>", path.read_text(encoding="utf-8"))
    box = head and re.search(r'viewBox="0 0 (\d+) (\d+)"', head.group(0))
    return bool(box) and _qr_size_attrs(*map(int, box.groups())) in head.group(0)


class _Report:
    """Cuenta y muestra los errores de `verify`."""
    def __init__(self):
        self.bad = 0

    def err(self, msg):
        self.bad += 1
        print(f"  ERROR  {msg}")


def _verify_qrs(qrdir, expected, name, rep, fix, skip=()):
    """Huella de cada QR de la carpeta frente a la dirección de direcciones.ini. `skip`: prefijos de los SVG que no son
    QR (en el kit, el botón y la tarjeta comparten carpeta con ellos)."""
    qrs = sorted(f for f in qrdir.glob("*.svg") if not f.stem.startswith(skip)) if qrdir.is_dir() else []
    if not qrs:
        print(f"  (sin QR todavía: `{fix}`)")
    for f in qrs:
        fp, key = _qr_fp(f), f.stem
        if key not in expected:
            print(f"  AVISO  {f.name}: la dirección de {name.get(key, key)} ya no está en {INI_PATH.name}; borra el QR si ya no lo usas")
        elif fp is None:
            rep.err(f"{f.name}: no lleva huella (no lo hizo este script). Regénéralo: {fix}")
        elif fp != fingerprint(expected[key]):
            rep.err(f"{f.name}: el QR no corresponde a la dirección de {name[key]} de {INI_PATH.name}. Regénéralo: {fix}")
        elif not _qr_at_scale(f):
            rep.err(f"{f.name}: no está a la escala de QR_SCALE ({QR_SCALE:g}). Regénéralo: {fix}")
        else:
            print(f"  OK     {f.name}")


def _verify_block(label, block, imgdir, img_re, expected, name, rep, fix):
    """Un bloque de donaciones (el del README del perfil o uno de los bloque-xx.md): sus direcciones frente a
    direcciones.ini, y sus imágenes frente a `imgdir`. `img_re` captura el nombre (sin .svg) de cada imagen: si es el de una
    moneda, su QR debe corresponder a la dirección que se ve en el bloque; si no (botón, tarjeta), basta con que exista."""
    found = _block_addresses(block)
    before = rep.bad
    for key in sorted(set(expected) | set(found), key=[c["key"] for c in COINS].index):
        e, g = expected.get(key), found.get(key)
        if e is None:
            rep.err(f"{label}: lleva una dirección de {name[key]} que no está en {INI_PATH.name}")
        elif g is None:
            rep.err(f"{label}: falta la dirección de {name[key]}. Ejecuta `{fix}`")
        elif e != g:
            rep.err(f"{label}: la dirección de {name[key]} no coincide con {INI_PATH.name} (aquí {_short(g)} · ini {_short(e)}). "
                    f"Si la buena es la de {label}, cópiala a {INI_PATH.name}; si no, ejecuta `{fix}`")
    for stem in img_re.findall(block):
        f = imgdir / f"{stem}.svg"
        if not f.is_file():
            rep.err(f"{label}: apunta a {f.name}, que no existe. Ejecuta `{fix}`")
        elif stem in expected and _qr_fp(f) != fingerprint(found.get(stem, "")):
            rep.err(f"{label}: el QR de {name[stem]} no corresponde a la dirección que se ve en {label}. Ejecuta `{fix}`")
    if rep.bad == before:
        print(f"  OK     {label}")


def _between_marks(text):
    m = re.search(re.escape(START) + r"(.*?)" + re.escape(END), text, re.S)
    return m.group(1) if m else None


def _verify_kit_like(assets, docs, expected, name, rep, fix):
    """Lo que comparten el kit y cada repo: su carpeta de imágenes (`assets`) y, por idioma, el archivo con el bloque
    (`docs` = {idioma: ruta}: bloque-xx.md en el kit, README en un repo). Comprueba los QR, el bloque frente a
    direcciones.ini y el botón y la tarjeta frente a los textos del script."""
    _verify_qrs(assets, expected, name, rep, fix, skip=("button-", "card-"))
    for lang, f in docs.items():
        block = _between_marks(_read(f) or "")
        if block is None:
            rep.err(f"{f.name}: no existe o no lleva las marcas {START} … {END}. Ejecuta `{fix}`")
            continue
        _verify_block(f.name, block, assets, re.compile(rf'src="\./{re.escape(KIT_ASSETS)}/([\w-]+)\.svg"'),
                      expected, name, rep, fix)
        for stem, want in ((f"button-{lang}", button_svg(BUTTON_TEXT[lang])), (f"card-{lang}", card_svg(lang, INTRO_REPO[lang]))):
            if _read(assets / f"{stem}.svg") not in (None, want):   # si falta, ya lo dijo _verify_block
                rep.err(f"{KIT_ASSETS}/{stem}.svg está desfasado respecto a los textos del script. Ejecuta `{fix}`")


def cmd_verify(args):
    rep = _Report()
    name = {c["key"]: c["name"] for c in COINS}
    expected = {c["key"]: a for c, a in general_addresses()}
    sync_fix, repos_fix = "python3 scripts/donate.py sync --write", "python3 scripts/donate.py repos --write"

    print("QR")
    _verify_qrs(ROOT / "assets" / "qr", expected, name, rep, sync_fix)

    print("\nREADME")
    for f, _lang in _profile_readmes():
        block = _between_marks(f.read_text(encoding="utf-8"))
        if block is None:
            print(f"  --     {f.name}: sin sección de donaciones")
            continue
        _verify_block(f.name, block, ROOT / "assets" / "qr", re.compile(r'src="\./assets/qr/([\w-]+)\.svg"'),
                      expected, name, rep, sync_fix)

    kit = kit_dir(getattr(args, "out", None))
    if kit.is_dir():   # el kit solo existe si has ejecutado `repos --write`
        print(f"\nKit de los repos ({kit})")
        _verify_kit_like(kit / KIT_ASSETS, {lang: kit / f"bloque-{lang}.md" for lang in LANGS}, expected, name, rep, repos_fix)
    for repo in getattr(args, "repo", None) or []:   # solo lectura: los repos se editan a mano
        repo = Path(repo).expanduser().resolve()
        print(f"\nRepo {repo.name} ({repo})")
        docs = {lang: repo / n for lang, n in (("es", "README.es.md"), ("en", "README.md")) if (repo / n).is_file()}
        before = rep.bad
        if not repo.is_dir():
            rep.err("la carpeta no existe: revisa la ruta")
            continue
        if not docs:
            rep.err("no hay README.md ni README.es.md")
        else:
            _verify_kit_like(repo / KIT_ASSETS, docs, expected, name, rep, repos_fix)
        if rep.bad > before:
            print(f"  → arreglo: `{repos_fix}` y, en este repo, vuelve a copiar assets/ del kit y pegar su bloque")
    print("\n" +("Hay diferencias: corrígelas antes de publicar." if rep.bad else "Todo coincide."))
    return 1 if rep.bad else 0


def cmd_sync(args):
    """Valida, rehace imágenes y QR, actualiza los README del perfil y comprueba que todo coincide. Sin --write solo
    simula. Si falta segno, se detiene ANTES de escribir nada."""
    print(f"1/4 Direcciones{'' if args.write else '  (simulación: añade --write para aplicar)'}")
    if cmd_check(None):
        return 1
    if not general_addresses():
        print(f"\nNo hay direcciones en {INI_PATH.name}: nada que insertar.")
        return 0
    if not _has_segno():
        if args.write:
            raise SystemExit("donate.py: " + NEED_SEGNO + "\nNo se ha escrito nada.")
        print("\n  AVISO: " + NEED_SEGNO + "\n  Con --write el script se detendría antes de escribir nada.")
    print("\n2/4 Imágenes (botón, tarjeta y QR)" + ("" if args.write else ": se rehacen con --write"))
    if args.write:
        cmd_assets(None)
        cmd_qr(None)
    print("\n3/4 README del perfil")
    changed = _inject(args.write)
    if not args.write:
        print("\nNada escrito. Revisa lo anterior y repite con --write.")
        return 0
    print("\n4/4 Comprobación")
    code = cmd_verify(None)
    print(f"\n{len(changed)} README actualizados. Revisa con `git diff` y haz commit (git no se toca desde este script).")
    return code


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    p = sub.add_parser("verify", help="¿README, QR y kit de los repos coinciden con direcciones.ini?")
    p.add_argument("--out", metavar="CARPETA", help=f"carpeta del kit de los repos (por defecto, ../{KIT_NAME})")
    p.add_argument("--repo", nargs="+", metavar="CARPETA", help="repos de tus herramientas a comprobar (solo lectura; admite varios)")
    p.set_defaults(fn=cmd_verify)
    p = sub.add_parser("sync", help="check + imágenes + QR + README del perfil + verify")
    p.add_argument("--write", action="store_true")
    p.set_defaults(fn=cmd_sync)
    p = sub.add_parser("repos", help="kit para los repos: carpeta assets/donate/ + bloques de texto (sin --write, simula)")
    p.add_argument("--write", action="store_true")
    p.add_argument("--out", metavar="CARPETA", help=f"dónde crear el kit (por defecto, ../{KIT_NAME}, junto al perfil)")
    p.set_defaults(fn=cmd_repos)
    args = ap.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
