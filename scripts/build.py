#!/usr/bin/env python3
"""Genera README.md (EN) y README.es.md (ES) desde una sola tabla de datos.

    python3 scripts/build.py

Solo biblioteca estándar. Edita DATOS y vuelve a ejecutar; no edites los README a mano.
Imágenes (ya ligeras; este script no las genera): iconos de herramientas en assets/icons/<id>.png|svg
(64 px, se muestran a 28), capturas en assets/screens/ (máx. 600 px de ancho) y el botón de correo assets/email.svg.
"""
import re
import struct
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = {"en": "README.md", "es": "README.es.md"}


def L(es, en):
    return {"es": es, "en": en}


def tool(repo, icon, es, en, name=None):
    return {"repo": repo, "icon": icon, "name": name or repo, "es": es, "en": en}


def cat(icon, title, tools):
    return {"icon": icon, "title": title, "tools": tools}


def esc(x):
    return escape(x, quote=False).replace('"', "&quot;")


def img(src, alt="", width=None, height=None, align=None):
    size = "".join(f' {k}="{v}"' for k, v in (("width", width), ("height", height), ("align", align)) if v)
    return f'<img src="{esc(src)}"{size} alt="{esc(alt)}">'


def center(imgs):
    return '<p align="center">\n' + "\n".join(f"  {i}" for i in imgs) + "\n</p>"


def tool_icon(name):
    f = next(iter(sorted((ROOT / "assets/icons").glob(f"{name}.*"))), None)
    if f is None:
        raise SystemExit(f"falta assets/icons/{name}.png|svg")
    return img(f"./assets/icons/{f.name}", width=28, height=28)


def screen_width(fname):
    """Ancho que da SCREEN_HEIGHT de alto, leído de la cabecera del PNG."""
    path = ROOT / "assets/screens" / fname
    if not path.is_file():
        hint = " (está en assets/icons/: muévela a assets/screens/)" if (ROOT / "assets/icons" / fname).is_file() else ""
        raise SystemExit(f"falta assets/screens/{fname}{hint}")
    w, h = struct.unpack(">II", path.read_bytes()[16:24])
    return round(SCREEN_HEIGHT * w / h)


def inline(s):
    """**negrita**, *cursiva* y `código` → HTML, para texto dentro de bloques HTML (donde GitHub no interpreta Markdown)."""
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", esc(s))
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", s)


def centered(s, tag="p"):
    return f'<{tag} align="center">{inline(s)}</{tag}>'


# ── DATOS ─────────────────────────────────────────────────────────────────────
# Cada texto es L(es=..., en=...): ES y EN juntos para no desincronizarlos.

BANNER = "./assets/banner2.svg"
BANNER_WIDTH = 600

# Presentación en tres niveles: rol (h3) → máster (negrita) → frase (normal)
ROLE = L(es="Filósofo de la tecnología & Builder",
         en="Philosopher of Technology & Builder")

MASTER = L(es="Máster Universitario en Filosofía Teórica y Práctica: Lógica, Historia y Filosofía de la Ciencia",
           en="MA in Theoretical and Practical Philosophy: Logic, History and Philosophy of Science")

TAGLINE = L(es="Convierto ideas y problemas complejos en herramientas funcionales, guiado por la filosofía KISS — LLMs, IA, interacción humano-IA, privacidad y open source.",
            en="I turn complex ideas and problems into functional tools, guided by the KISS philosophy — LLMs, AI, human-AI interaction, privacy, and open source.")

STATUS = L(es="🟢 **Disponible para trabajar** · 💻 **Remoto**: para cualquier empresa del mundo · 🌍 **Reubicación**: a cualquier país",
      en="🟢 **Open to work** · 💻 **Remote**: for any company in the world · 🌍 **Relocation**: any country")

QUOTE = L(es="Quiero usar la tecnología, no que la tecnología me use a mí.",
      en="I want to use technology, not have technology use me.")

CMD = {
    "about": L(es="cat sobre-mi.md", en="cat about-me.md"),
    "tools": L(es="ls herramientas/", en="ls tools/"),
    "stack": L(es="cat stack.txt", en="cat stack.txt"),
    "stats": L(es="./estadisticas.sh", en="./stats.sh"),
    "contact": L(es="./contacto.sh", en="./contact.sh"),
}

# «Sobre mí» en 3 bloques; la **negrita** marca las frases clave (es Markdown normal, fuera de bloques HTML).
ABOUT = [
    L(es="Siempre me han interesado la tecnología, los medios de comunicación y la privacidad. Gran parte de mi carrera ha estado dedicada a investigar los avances tecnológicos que la humanidad ha ido incorporando en sus sociedades, y cómo estos la han ido transformando, para bien y para mal. Con el paso de los años y los sucesivos cambios, he aprendido a **usar la tecnología desde ángulos que no estaban previstos**, es decir, usar ese artefacto tecnológico de una nueva forma que sirva como solución ante una dificultad, problema o automatización. Porque las piezas para la solución estaban ahí, pero faltaba montar el puzzle completo para que la solución se hiciese realidad.",
      en="I've always been drawn to technology, media, and privacy. A large part of my career has been spent researching the technological advances humanity keeps weaving into its societies, and how they've reshaped it, for better and for worse. Over the years, through one change after another, I've learned to **look at technology from angles it wasn't originally built for**: taking a piece of tech and repurposing it to solve a difficulty, a problem, or something that needed automating. The pieces for the solution were already there, what was missing was putting the whole puzzle together to make it real."),
    L(es="Esta idea es una de mis líneas de pensamiento: **se pueden construir soluciones increíbles con pocos recursos** si se sabe utilizarlos correctamente. Al mismo tiempo, esa misma filosofía KISS se traduce en **permitir que el usuario elija lo que quiera**, sin que esa elección le perjudique después. Estas ideas han repercutido en cómo están diseñadas las herramientas que te comparto. Lo hago de este modo porque es exactamente lo que hubiese necesitado cuando era un niño, ya que recuerdo lo que era abrir un programa en un idioma extraño, con una jerga técnica, plagado de opciones y menús, y sentirme abrumado por no saber qué hacer pese a saber que se pueden hacer innumerables cosas.",
      en="That's one of my core lines of thinking: **incredible solutions can be built with very few resources**, if you know how to use them right. At the same time, that same KISS philosophy translates into **letting the user choose what they want** without that choice working against them later. These ideas are what have shaped how the tools I share here are designed. I build them this way because it's exactly what I would have needed as a kid, I remember opening a program in an unfamiliar language, full of technical jargon, menus, and options, and feeling completely overwhelmed, unsure what to do despite knowing countless things were possible."),
    L(es="Ese tipo de impedimentos son los que trato de solventar cuando diseño una solución; el proceso para llegar a ella es lo que más me motiva, pues **disfruto aprendiendo, explorando todo lo que desconozco** y me encanta mejorar lo que ya sé. Eso es justo lo que me guía en la vida. La programación, la IA y la automatización son otro modo que he encontrado para trasladar mis ideas a la realidad; al mismo tiempo, me han dado una actividad placentera en la que puedo pasar muchas horas concentrado.",
      en="Those kinds of obstacles are exactly what I try to solve when I design something; the process of getting there is what motivates me most, since **I love learning, exploring what I don't yet know**, and getting better at what I already know. That's what guides me in life. Programming, AI, and automation are another way I've found to turn my ideas into reality, and at the same time, they've given me an activity I genuinely enjoy, one I can lose many focused hours in."),
]

COLS = L(es=('Herramienta', 'Qué hace'), en=('Tool', 'What it does'))
# Espacios duros a cada lado de la cabecera: GitHub dimensiona cada tabla por su contenido, y así la 1.ª columna mide
# lo mismo en todas y no se parten los nombres. Con el icono sobre el nombre queda en ≈ 164 px (ES) / 161 px (EN) con
# Inter y 151–154 px con Roboto. Calibrado con scripts/check.py --render.
COL_PAD = L(es="&nbsp;" * 7, en="&nbsp;" * 14)

# Guion blando (&shy;): sin él, una palabra larga ensancha la columna de texto y la tabla se desplaza en horizontal en
# móvil. Criterio: palabras con su puntuación («AutoHotkey.» mide 81 px) de > ~78 px en Inter 14 px; a 360 px la columna
# admite ≈ 88 px en ES y 91 px en EN. Se parten hacia el centro (cada trozo + el guion, < ~70 px). El guion se dibuja
# solo si la palabra se parte al final de línea, aunque quepa entera en la siguiente. Si check.py da scroll, añade aquí
# la palabra que indica.
SOFT_HYPHEN = {
    "AutoHotkey": "Auto&shy;Hotkey",
    "automatically": "automat&shy;ically",
    "automáticamente": "automáti&shy;camente",
    "automatizadas": "automati&shy;zadas",
    "configuración": "configura&shy;ción",
    "dependencias": "depen&shy;dencias",
    "dependencies": "depen&shy;dencies",
    "navegadores": "navega&shy;dores",
    "preinstalado": "preinsta&shy;lado",
    "resincronización": "resincro&shy;nización",
}


def soft(s):
    for word, hyphenated in SOFT_HYPHEN.items():
        s = s.replace(word, hyphenated)
    return s

# cat(icono de categoría, título, [herramientas]);  tool(repo, icono, es=, en=, name=)
CATEGORIES = [
    cat("maintenance", L(es="Mantenimiento del sistema", en="System maintenance"), [
        tool("Autostart_Manager", "autostart-manager",
             es="Junta en un panel las apps, servicios systemd y tareas cron que arrancan al iniciar sesión, con más control que Mint de serie.",
             en="Brings together, in one panel, every app, systemd service, and cron job that launches on login — with more control than stock Mint."),
        tool("Mint-Doctor", "mint-doctor",
             es="Revisa Linux Mint en busca de los problemas más habituales y los repara automáticamente, bajo tu aprobación en cada paso.",
             en="Scans Linux Mint for the most common issues and fixes them automatically, with your approval at every step."),
    ]),
    cat("customization", L(es="Personalización y multimedia", en="Customization & multimedia"), [
        tool("Color-Mint", "color-mint",
             es="Personaliza Cinnamon —temas, panel, escritorio, terminal y fuentes— desde una sola ventana, con copia de seguridad antes de cada cambio.",
             en="Customizes Cinnamon — themes, panel, desktop, terminal, and fonts — from a single window, with a backup before every change."),
        tool("PhoneCam", "phonecam",
             es="Usa la cámara y el micrófono de tu Android como webcam y micrófono de Linux por USB — 100% local y sin instalar nada en el móvil.",
             en="Use your Android phone's camera and mic as a webcam and microphone on Linux over USB — 100% local, nothing to install on the phone."),
    ]),
    cat("backups", L(es="Copias de seguridad y configuración", en="Backups & configuration"), [
        tool("Mint-Setup", "mint-setup",
             es="Guarda la configuración de tu escritorio y tus apps —paneles, temas, Wi-Fi, Docker, LUKS...— y la restaura en una instalación nueva.",
             en="Saves your desktop and app setup — panels, themes, Wi-Fi, Docker, LUKS... — and restores it on a fresh install."),
        tool("Simple-Backup", "simple-backup",
             es="Copias de seguridad, resincronización de carpetas y tareas automatizadas, todo en un script de Bash.",
             en="Backups, folder resyncing, and automated tasks, all in a single Bash script."),
    ]),
    cat("security", L(es="Seguridad y privacidad", en="Security & privacy"), [
        tool("Enkripta", "enkripta",
             es="Cifra carpetas y archivos con AES-256, integrado en Nemo y el escritorio —doble clic, botón derecho— como parte del sistema.",
             en="Encrypts folders and files with AES-256, built into Nemo and the desktop — double-click, right-click — as if part of the system."),
        tool("Browser-Cleaner", "browser-cleaner",
             es="Limpia 14 navegadores distintos de la forma más simple, práctica y rápida posible.",
             en="Cleans 14 different browsers in the simplest, most practical, and fastest way possible."),
        tool("VPN-NetGuard", "vpn-netguard",
             es="Kill switch, reconexión automática y anonimato de red para tu VPN en Linux, con instalación en 1 clic.",
             en="Kill switch, auto-reconnect and network privacy for your Linux VPN, with one-click setup.",
         name="VPN NetGuard"),
    ]),
    cat("software-files", L(es="Gestión de software y archivos", en="Software & file management"), [
        tool("MintApp_Remover", "mintapp-remover",
             es="Desinstala de forma segura cualquier programa de Linux Mint, también el preinstalado, y limpia las dependencias huérfanas.",
             en="Safely uninstalls any program on Linux Mint, preinstalled ones included, and cleans up orphaned dependencies."),
        tool("Renombrador", "renombrador",
             es="Renombra archivos y carpetas por lotes, con vista previa y opción de deshacer, desde la terminal o el botón derecho en Nemo.",
             en="Batch-renames files and folders, with a preview and undo option, from the terminal or the right-click menu in Nemo."),
    ]),
    cat("development", L(es="Desarrollo", en="Development"), [
        tool("LinuxMint-Scripter", "linuxmint-scripter",
             es="Web de un solo archivo para generar y auditar scripts de Bash o Python con IA, con tu propia clave de API y sin servidor intermedio.",
             en="Single-file web app to generate and audit Bash or Python scripts with AI — your own API key, no middleman server."),
        tool("Bitacora-Dev", "bitacora-dev",
             es="Conserva la historia y el contexto de un proyecto —versiones, decisiones, notas, pendientes— desde el navegador, con IA contextual opcional.",
             en="Preserves a project's history and context — versions, decisions, notes, pending tasks — in the browser, with optional contextual AI.",
         name=L(es="Bitácora Dev", en="Dev Log")),
    ]),
    cat("automation", L(es="Automatización e integración", en="Automation & integration"), [
        tool("Scriptya", "scriptya",
             es="Convierte cualquier script en una app con icono propio e integración en el menú de Cinnamon o el escritorio.",
             en="Turns any script into an app with its own icon and integration into the Cinnamon menu or desktop."),
        tool("Mi-Lanzador", "mi-lanzador",
             es="Secuencias de pasos que abren programas, webs o comandos, colocan ventanas, simulan clics y pulsan teclas — como una macro de AutoHotkey.",
             en="Chained steps that open programs, web pages, or commands, arrange windows, and simulate clicks and keys — like an AutoHotkey macro."),
    ]),
]

# Capturas destacadas, en una fila bajo el título de herramientas: (repo, archivo en assets/screens/, alt).
# Todas con la misma altura; el ancho sale del PNG. La suma de anchos debe quedar por debajo de ~815 px (GitHub da
# 832 útiles, menos el hueco entre imágenes y algo de margen): si no, baja SCREEN_HEIGHT; check.py avisa.
# Se omite `height` para que escalen sin deformarse en móvil (donde se apilan).
SCREEN_HEIGHT = 270
SCREENS = [
    ("PhoneCam", "phonecam-en.png", L(es="Menú de PhoneCam", en="PhoneCam menu")),
    ("Renombrador", "renombrador-en.png", L(es="Menú de Renombrador", en="Renombrador menu")),
]

STACK = [
    ("Bash", "https://img.shields.io/badge/-Bash-4EAA25?style=flat-square&logo=gnubash&logoColor=white"),
    ("Python", "https://img.shields.io/badge/-Python-3776AB?style=flat-square&logo=python&logoColor=white"),
    ("HTML5", "https://img.shields.io/badge/-HTML5-E34F26?style=flat-square&logo=html5&logoColor=white"),
    ("CSS3", "https://img.shields.io/badge/-CSS3-1572B6?style=flat-square&logo=css3&logoColor=white"),
    ("JavaScript", "https://img.shields.io/badge/-JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black"),
    ("Linux Mint", "https://img.shields.io/badge/-Linux%20Mint-87CF3E?style=flat-square&logo=linuxmint&logoColor=white"),
    ("GTK/Zenity", "https://img.shields.io/badge/-GTK%20%2F%20Zenity-4A86CF?style=flat-square&logo=gnome&logoColor=white"),
    ("Git", "https://img.shields.io/badge/-Git-F05032?style=flat-square&logo=git&logoColor=white"),
]

STATS = [
    ("https://github-stats-extended.vercel.app/api?username=filonux&show_icons=true&hide_border=true&bg_color=0D1117&title_color=7EE787&icon_color=E3B341&text_color=C9D1D9",
     L(es="Estadísticas de GitHub de filonux", en="filonux's GitHub stats")),
    ("https://github-stats-extended.vercel.app/api/top-langs/?username=filonux&layout=compact&hide_border=true&bg_color=0D1117&title_color=7EE787&text_color=C9D1D9",
     L(es="Lenguajes más usados por filonux", en="filonux's most used languages")),
]

CONTACT = L(es="Abierto a roles como `AI Product Engineer`, `Founding AI Engineer` y afines — impacto social de la tecnología, construcción de producto o interacción humano-IA — además de colaboraciones.",
      en="Open to roles like `AI Product Engineer`, `Founding AI Engineer`, and similar — tech's social impact, product building, or human-AI interaction — plus collabs.")

TAGS = "`AI Tools` · `Local AI`"

EMAIL_ADDR = "filonux@proton.me"
# Botón de 222×44 px (44 px de alto para pulsarlo bien en móvil); el alt es la dirección, para lectores de pantalla.
# Debajo, la dirección en texto: una imagen no se puede copiar y, sin cliente de correo, el clic no hace nada.
EMAIL = (f'<a href="mailto:{EMAIL_ADDR}">{img("./assets/email.svg", EMAIL_ADDR, width=222, height=44)}</a>'
         f"<br>\n`{EMAIL_ADDR}`")

PROMPT = "```\nfilonux@nix:~$ _\n```"


# ── RENDER ────────────────────────────────────────────────────────────────────

def render(lang):
    t = lambda v: v[lang] if isinstance(v, dict) else v
    h2 = lambda key: f"## `$ {t(CMD[key])}`"

    switch = " · ".join(
        f"<strong>{code}</strong>" if code.lower() == lang else f'<a href="./{FILES[code.lower()]}">{code}</a>'
        for code in ("ES", "EN"))
    b = [f'<p align="right"><sub>{switch}</sub></p>',
         center([img(BANNER, "FILONUX TOOLS", width=BANNER_WIDTH)]),
         centered(t(ROLE), "h3"), centered(f"**{t(MASTER)}**"), centered(t(TAGLINE)),
         centered(t(STATUS)), centered(f"*{t(QUOTE)}*"),
         h2("about"), *map(t, ABOUT), h2("tools")]

    b.append(center(f'<a href="https://github.com/filonux/{repo}">{img(f"./assets/screens/{f}", t(alt), width=screen_width(f))}</a>'
                    for repo, f, alt in SCREENS))

    for c in CATEGORIES:
        icon = img(f"./assets/icons/{c['icon']}.svg", width=22, height=22, align="absmiddle")
        b.append(f"### {icon} {t(c['title'])}")
        head = t(COLS)
        rows = [f'| [{tool_icon(x["icon"])}<br>**{t(x["name"])}**](https://github.com/filonux/{x["repo"]}) | {soft(x[lang])} |'
                for x in c["tools"]]
        b.append("\n".join([f"| {t(COL_PAD)}{head[0]}{t(COL_PAD)} | {head[1]} |", "|:---:|:---|", *rows]))

    b += [h2("stack"), center(img(u, a) for a, u in STACK),
          h2("stats"), center(img(u, t(a)) for u, a in STATS),
          h2("contact"), t(CONTACT), TAGS, EMAIL, PROMPT]
    return "\n\n".join(b) + "\n"


def main():
    for lang, name in FILES.items():
        (ROOT / name).write_text(render(lang), encoding="utf-8")
        print("escrito", name)


if __name__ == "__main__":
    main()
