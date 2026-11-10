#!/usr/bin/env python3
"""Genera README.md (EN) y README.es.md (ES) desde una sola tabla de datos.

    python3 scripts/build.py

Además de los dos README, rellena el bloque de contacto de JOIN.md y UNETE.md (entre las marcas <!-- contact:start --> y
<!-- contact:end -->), para que correo y Session salgan siempre iguales en las cuatro páginas.

Solo biblioteca estándar. Edita DATOS y vuelve a ejecutar; no edites los README a mano.
Imágenes (ya ligeras; este script no las genera): iconos de herramientas en assets/icons/<id>.png|svg
(64 px, se muestran a 28), iconos de estado y categoría en assets/icons/*.svg y el botón de correo assets/email.svg.
"""
import re
import struct
import sys
from html import escape
from pathlib import Path
from urllib.parse import quote

sys.dont_write_bytecode = True  # antes de importar donate: no se crea scripts/__pycache__/ y el repo no necesita .gitignore

try:  # scripts/donate.py: sección «./donar.sh». Vacía mientras scripts/direcciones.ini esté vacío.
    import donate
except ImportError:  # sin donate.py, el perfil se genera igual, sin la sección
    donate = None

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


def status(lang):
    """Línea «Open to work · Remote · Relocation»: icono SVG + texto; el icono va como HTML, así que no pasa por inline()."""
    parts = [f"{img(f'./assets/icons/{i}.svg', width=22, height=22, align='absmiddle')} {inline(x[lang])}" for i, x in STATUS]
    return f'<p align="center">{" · ".join(parts)}</p>'


# ── DATOS ─────────────────────────────────────────────────────────────────────
# Cada texto es L(es=..., en=...): ES y EN juntos para no desincronizarlos.

BANNER = "./assets/banner2.svg"
BANNER_WIDTH = 480

# Presentación en tres niveles: rol (h3) → máster (negrita) → frase (normal)
ROLE = L(es="Filósofo de la tecnología & Builder",
         en="Philosopher of Technology & Builder")

MASTER = L(es="Máster Universitario en Filosofía Teórica y Práctica: Lógica, Historia y Filosofía de la Ciencia",
           en="MA in Theoretical and Practical Philosophy: Logic, History and Philosophy of Science")

TAGLINE = L(es="Convierto ideas y problemas complejos en herramientas funcionales, guiado por la filosofía KISS — LLMs, IA, interacción humano-IA, privacidad y open source.",
            en="I turn complex ideas and problems into functional tools, guided by the KISS philosophy — LLMs, AI, human-AI interaction, privacy, and open source.")

# (icono en assets/icons/<id>.svg, texto): se pintan en una sola línea, separados por « · ».
STATUS = [
    ("open-to-work", L(es="**Disponible para trabajar**", en="**Open to work**")),
    ("remote", L(es="**Remoto**: para cualquier empresa del mundo", en="**Remote**: for any company in the world")),
    ("relocation", L(es="**Reubicación**: a cualquier país", en="**Relocation**: any country")),
]

QUOTE = L(es="Quiero usar la tecnología, no que la tecnología me use a mí.",
      en="I want to use technology, not have technology use me.")

CMD = {
    "about": L(es="cat sobre-mi.md", en="cat about-me.md"),
    "tools": L(es="ls herramientas/", en="ls tools/"),
    "stack": L(es="cat stack.txt", en="cat stack.txt"),
    "stats": L(es="./estadisticas.sh", en="./stats.sh"),
    "contact": L(es="./contacto.sh", en="./contact.sh"),
}

# «Sobre mí» en 4 bloques; la **negrita** marca las frases clave (es Markdown normal, fuera de bloques HTML).
ABOUT = [
    L(es="Siempre me han interesado la tecnología, los medios de comunicación y la privacidad. Gran parte de mi carrera ha estado dedicada a investigar los avances tecnológicos que la humanidad ha ido incorporando en sus sociedades, y cómo estos la han ido transformando, para bien y para mal. Con el paso de los años y los sucesivos cambios, he aprendido a **usar la tecnología desde ángulos que no estaban previstos**, es decir, usar ese artefacto tecnológico de una nueva forma que sirva como solución ante una dificultad, problema o automatización. Porque las piezas para la solución estaban ahí, pero faltaba montar el puzzle completo para que la solución se hiciese realidad.",
      en="I've always been drawn to technology, media, and privacy. A large part of my career has been spent researching the technological advances humanity keeps weaving into its societies, and how they've reshaped it, for better and for worse. Over the years, through one change after another, I've learned to **look at technology from angles it wasn't originally built for**: taking a piece of tech and repurposing it to solve a difficulty, a problem, or something that needed automating. The pieces for the solution were already there, what was missing was putting the whole puzzle together to make it real."),
    L(es="Esta idea es una de mis líneas de pensamiento: **se pueden construir soluciones increíbles con pocos recursos** si se sabe utilizarlos correctamente. Al mismo tiempo, esa misma filosofía KISS se traduce en **permitir que el usuario elija lo que quiera**, sin que esa elección le perjudique después. Estas ideas han repercutido en cómo están diseñadas las herramientas que te comparto. Lo hago de este modo porque es exactamente lo que hubiese necesitado cuando era un niño, ya que recuerdo lo que era abrir un programa en un idioma extraño, con una jerga técnica, plagado de opciones y menús, y sentirme abrumado por no saber qué hacer pese a saber que se pueden hacer innumerables cosas.",
      en="That's one of my core lines of thinking: **incredible solutions can be built with very few resources**, if you know how to use them right. At the same time, that same KISS philosophy translates into **letting the user choose what they want** without that choice working against them later. These ideas are what have shaped how the tools I share here are designed. I build them this way because it's exactly what I would have needed as a kid, I remember opening a program in an unfamiliar language, full of technical jargon, menus, and options, and feeling completely overwhelmed, unsure what to do despite knowing countless things were possible."),
    L(es="Ese tipo de impedimentos son los que trato de solventar cuando diseño una solución; el proceso para llegar a ella es lo que más me motiva, pues **disfruto aprendiendo, explorando todo lo que desconozco** y me encanta mejorar lo que ya sé. Eso es justo lo que me guía en la vida. La programación, la IA y la automatización son otro modo que he encontrado para trasladar mis ideas a la realidad; al mismo tiempo, me han dado una actividad placentera en la que puedo pasar muchas horas concentrado.",
      en="Those kinds of obstacles are exactly what I try to solve when I design something; the process of getting there is what motivates me most, since **I love learning, exploring what I don't yet know**, and getting better at what I already know. That's what guides me in life. Programming, AI, and automation are another way I've found to turn my ideas into reality, and at the same time, they've given me an activity I genuinely enjoy, one I can lose many focused hours in."),
    L(es="Y ahora quiero dar un paso más: voy a **fundar una startup** en torno a la privacidad, la seguridad, la inteligencia artificial, la automatización y la construcción de herramientas. Además de colaboraciones y oportunidades laborales, busco **aliados** para el *founding team*: personas con talento que entiendan el trabajo y las ideas que hay detrás de mis proyectos y compartan mi visión. Prefiero que el proceso sea personal: de tú a tú, sin CV ni bots que los clasifiquen, para que nos conozcamos. El porqué completo, en [Únete](./UNETE.md).",
      en="And now, the next step: I'm going to **found a startup** around privacy, security, artificial intelligence, automation, and tool-building. Beyond collaborations and job opportunities, I'm looking for **allies** for the *founding team*: talented people who understand the work and the ideas behind my projects and share my vision. I'd rather keep the process personal: one-on-one, with no CVs piling up and no bots ranking them, so we can get to know each other. The full why is in [Join](./JOIN.md)."),
]

COLS = L(es=('Herramienta', 'Qué hace'), en=('Tool', 'What it does'))
# Espacios duros a cada lado de la cabecera: GitHub dimensiona cada tabla por su contenido, y así la 1.ª columna mide
# lo mismo en todas y no se parten los nombres. Con el icono sobre el nombre queda en ≈ 164 px (ES) / 161 px (EN) con
# Inter y 151–154 px con Roboto.
COL_PAD = L(es="&nbsp;" * 7, en="&nbsp;" * 14)

# Guion blando (&shy;): sin él, una palabra larga ensancha la columna de texto y la tabla se desplaza en horizontal en
# móvil. Criterio: palabras con su puntuación («AutoHotkey.» mide 81 px) de > ~78 px en Inter 14 px; a 360 px la columna
# admite ≈ 88 px en ES y 91 px en EN. Se parten hacia el centro (cada trozo + el guion, < ~70 px). El guion se dibuja
# solo si la palabra se parte al final de línea, aunque quepa entera en la siguiente. Si una tabla se desplaza en
# horizontal en el móvil, añade aquí la palabra que la ensancha.
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
             es="Un solo panel para ver y controlar todo lo que arranca solo —apps, servicios systemd y tareas cron— con una casilla por elemento y avisos antes de desactivar algo crítico.",
             en="One panel to see and control everything that starts on its own — apps, systemd services, and cron jobs — with one checkbox per item and warnings before you disable anything critical."),
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
        tool("Bitacora-Dev", "devlog",
             es="Conserva la historia y el contexto de un proyecto —versiones, decisiones, notas, pendientes— desde el navegador. Un asistente de IA opcional maneja todo el programa como lo harías tú, y un agente también puede controlarlo.",
             en="Preserves a project's history and context — versions, decisions, notes, pending tasks — in the browser. An optional AI assistant operates the whole program just as you would, and an agent can control it too.",
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
# 832 útiles, menos el hueco entre imágenes y algo de margen): si no, baja SCREEN_HEIGHT.
# Se omite `height` para que escalen sin deformarse en móvil (donde se apilan).
# Vacía a propósito: assets/screens/ no existe en el repo y el README publicado no lleva esta fila. Para activarla,
# crea assets/screens/ con los PNG y añade aquí las entradas, p. ej.:
#     ("PhoneCam", "phonecam-en.png", L(es="Menú de PhoneCam", en="PhoneCam menu")),
#     ("Renombrador", "renombrador-en.png", L(es="Menú de Renombrador", en="Renombrador menu")),
SCREEN_HEIGHT = 270
SCREENS = []

def badge(alt, text, color, logo=None, logo_color="white"):
    """Etiqueta de shields.io (alt, url). `text` se escapa solo; `logo` es un slug de Simple Icons (si shields no lo
    conoce, la etiqueta sale igual, sin logo). Colores del perfil: verde 7EE787, ámbar E3B341."""
    label = quote(text.replace("-", "--").replace("_", "__"), safe="")
    url = f"https://img.shields.io/badge/-{label}-{color}?style=flat-square"
    if logo:
        url += f"&logo={logo}&logoColor={logo_color}"
    return (alt, url)


# Una fila (un <p align="center">) por grupo. Para añadir o quitar una etiqueta, toca solo su línea.
STACK = [
    [   # lenguajes
        badge("Bash", "Bash", "4EAA25", "gnubash"),
        badge("Python", "Python", "3776AB", "python"),
        badge("HTML5", "HTML5", "E34F26", "html5"),
        badge("CSS3", "CSS3", "1572B6", "css"),
        badge("JavaScript", "JavaScript", "F7DF1E", "javascript", "black"),
    ],
    [   # Linux y escritorio
        badge("Linux", "Linux", "FCC624", "linux", "black"),
        badge("Linux Mint", "Linux Mint", "87CF3E", "linuxmint"),
        badge("GTK/Zenity", "GTK / Zenity", "4A86CF", "gnome"),
        badge("Git", "Git", "F05032", "git"),
    ],
    [   # IA y agentes
        badge("LLMs", "LLMs", "7C3AED"),
        badge("AI Agents", "AI Agents", "7C3AED"),
        badge("MCP", "MCP", "7C3AED", "modelcontextprotocol"),
        badge("Local AI", "Local AI", "7C3AED"),
    ],
    [   # automatización y arquitectura
        badge("Automation", "Automation", "E3B341", None, "black"),
        badge("Architecture Design", "Architecture Design", "7EE787", None, "black"),
    ],
]

STATS = [
    ("https://github-stats-extended.vercel.app/api?username=filonux&show_icons=true&hide_border=true&bg_color=0D1117&title_color=7EE787&icon_color=E3B341&text_color=C9D1D9",
     L(es="Estadísticas de GitHub de filonux", en="filonux's GitHub stats")),
    ("https://github-stats-extended.vercel.app/api/top-langs/?username=filonux&layout=compact&hide_border=true&bg_color=0D1117&title_color=7EE787&text_color=C9D1D9",
     L(es="Lenguajes más usados por filonux", en="filonux's most used languages")),
]

CONTACT = L(es="Abierto a roles como `AI Product Engineer`, `Founding AI Engineer` y afines — impacto social de la tecnología, construcción de producto o interacción humano-IA — además de colaboraciones.\n\n**Busco aliados para mi futura startup** de privacidad, seguridad, IA, automatización y herramientas. Si entiendes mi trabajo y las ideas que hay detrás de mis proyectos, escríbeme por correo o por Session: de tú a tú, sin CV ni formularios, hablamos. El porqué, en [Únete](./UNETE.md).",
      en="Open to roles like `AI Product Engineer`, `Founding AI Engineer`, and similar — tech's social impact, product building, or human-AI interaction — plus collabs.\n\n**I'm looking for allies for my future startup** in privacy, security, AI, automation, and tools. If you understand my work and the ideas behind my projects, write to me by email or Session: one-on-one, no CVs, no forms, we just talk. The why, in [Join](./JOIN.md).")

TAGS = "`AI Tools` · `Local AI` · `MCP` · `Automation`"

EMAIL_ADDR = "filonux@proton.me"
# Botón de 222×44 px (44 px de alto para pulsarlo bien en móvil); el alt es la dirección, para lectores de pantalla.
EMAIL = f'<a href="mailto:{EMAIL_ADDR}">{img("./assets/email.svg", EMAIL_ADDR, width=222, height=44)}</a>'

# Session ID: 66 caracteres hexadecimales, empieza por 05. Vacío = no se publica Session en ninguna página.
SESSION_ID = "05a6d7103c5f6214527ca7538c4b5d3f878651112afac165a992775c360fcbf353"
SESSION_NOTE = L(es="mensajería cifrada de extremo a extremo, sin número de teléfono", en="end-to-end encrypted messenger, no phone number")


def session_id():
    """El Session ID validado, o \"\" si está vacío. Se valida el formato para no publicar una errata."""
    if SESSION_ID and not re.fullmatch(r"05[0-9a-f]{64}", SESSION_ID):
        raise SystemExit("SESSION_ID no tiene el formato de un Session ID (66 caracteres hexadecimales que empiezan por 05)")
    return SESSION_ID


def session_block(lang):
    """README: «**Session** — nota:» y el ID en un bloque de código (botón de copiar; sin desbordar en móvil). \"\" si no hay."""
    sid = session_id()
    return f"**Session** — {SESSION_NOTE[lang]}:\n\n```\n{sid}\n```" if sid else ""


# Bloque de contacto de JOIN.md y UNETE.md: lo rellena main() entre las marcas <!-- contact:start/end -->.
PAGES = {"en": "JOIN.md", "es": "UNETE.md"}
PAGE_HEAD = L(es=("Escríbeme por correo o por Session, la que prefieras:", "Escríbeme por correo:"),
              en=("Write to me by email or Session, whichever you prefer:", "Write to me by email:"))
PAGE_EMAIL = L(es="Correo", en="Email")
PAGE_TAIL = L(es="Cuéntame qué te trae, qué sabes hacer o qué te gustaría aprender y cómo prefieres que hablemos. No te contestará una máquina: te contestaré personalmente, tomándome el tiempo de estudiar tu trabajo en GitHub o lo que me quieras enseñar.",
              en="Tell me what brings you here, what you can do or what you'd like to learn, and how you'd prefer to talk. No machine will answer you: I'll reply personally, taking the time to study your work on GitHub or whatever you'd like to show me.")


def page_contact(lang):
    sid = session_id()
    items = [f"- **{PAGE_EMAIL[lang]}:** [`{EMAIL_ADDR}`](mailto:{EMAIL_ADDR})"]
    if sid:
        items.append(f"- **Session** ({SESSION_NOTE[lang]}):\n  ```\n  {sid}\n  ```")
    return f"{PAGE_HEAD[lang][0 if sid else 1]}\n\n" + "\n".join(items) + f"\n\n{PAGE_TAIL[lang]}"


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
         status(lang), centered(f"*{t(QUOTE)}*"),
         h2("about"), *map(t, ABOUT), h2("tools")]

    if SCREENS:
        b.append(center(f'<a href="https://github.com/filonux/{repo}">{img(f"./assets/screens/{f}", t(alt), width=screen_width(f))}</a>'
                        for repo, f, alt in SCREENS))

    for c in CATEGORIES:
        icon = img(f"./assets/icons/{c['icon']}.svg", width=22, height=22, align="absmiddle")
        b.append(f"### {icon} {t(c['title'])}")
        head = t(COLS)
        rows = [f'| [{tool_icon(x["icon"])}<br>**{t(x["name"])}**](https://github.com/filonux/{x["repo"]}) | {soft(x[lang])} |'
                for x in c["tools"]]
        b.append("\n".join([f"| {t(COL_PAD)}{head[0]}{t(COL_PAD)} | {head[1]} |", "|:---:|:---|", *rows]))

    b += [h2("stack"), *(center(img(u, a) for a, u in row) for row in STACK),
          h2("stats"), center(img(u, t(a)) for u, a in STATS)]
    if donate:  # «./donar.sh», entre «stats» y «contact»; "" mientras direcciones.ini esté vacío
        d = donate.render(lang, marked=True, width=BANNER_WIDTH)
        if d:
            b.append(d)
    b += [h2("contact"), t(CONTACT), TAGS, EMAIL]
    if session_block(lang):
        b.append(session_block(lang))
    b.append(PROMPT)
    return "\n\n".join(b) + "\n"


PAGE_BLOCK = re.compile(r"(<!-- contact:start -->).*?(<!-- contact:end -->)", re.S)


def fill_page(lang):
    """Rellena el bloque de contacto de JOIN.md / UNETE.md. Si la página o las marcas no existen, no hace nada."""
    path = ROOT / PAGES[lang]
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    new, n = PAGE_BLOCK.subn(lambda m: f"{m.group(1)}\n{page_contact(lang)}\n{m.group(2)}", text)
    if n and new != text:
        path.write_text(new, encoding="utf-8")
        print("actualizado", PAGES[lang])


def main():
    for lang, name in FILES.items():
        (ROOT / name).write_text(render(lang), encoding="utf-8")
        print("escrito", name)
        fill_page(lang)


if __name__ == "__main__":
    main()
