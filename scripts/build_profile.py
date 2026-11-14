"""Build the GitHub profile: light + dark SVG cards in assets/profile/ and README.md.

Stdlib only. Content: profile.config.json. Live numbers: assets/data/stats.json
(refresh with scripts/fetch_stats.py). Run:  python3 scripts/build_profile.py
"""
import base64
import html
import itertools
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "profile.config.json").read_text())
STATS_FILE = ROOT / "assets" / "data" / "stats.json"
STATS = json.loads(STATS_FILE.read_text()) if STATS_FILE.exists() else {}
OUT = ROOT / "assets" / "profile"
FONTS = ROOT / "assets" / "fonts"
METRICS = json.loads((FONTS / "metrics.json").read_text())
FONT_DATA = {n: base64.b64encode((FONTS / f"{n}.woff2").read_bytes()).decode() for n in METRICS}
FAMILY = {"sans-400": ("S", 400), "sans-600": ("S", 600), "mono-500": ("M", 500)}

W = 900
PAD = 32

# One accent (indigo), green only for "live/current" status, everything else neutral.
THEMES = {
    "dark": {
        "card": "#0b0f17", "border": "#222936", "text": "#eef2f7", "muted": "#9aa4b2", "subtle": "#6b7686",
        "pill": "#121823", "dot": "#ffffff", "dot_op": ".05",
        "accent": "#8b93f8", "accent_soft": "#4f46e5", "accent2_soft": "#1d4ed8", "aurora_op": ".30",
        "tint": ".12", "tint_stroke": ".35", "green": "#3fb950",
        "name_from": "#ffffff", "name_to": "#c7cbfd",
    },
    "light": {
        "card": "#ffffff", "border": "#e1e4ea", "text": "#141922", "muted": "#566070", "subtle": "#8a93a2",
        "pill": "#f6f7f9", "dot": "#000000", "dot_op": ".05",
        "accent": "#4f46e5", "accent_soft": "#a5b4fc", "accent2_soft": "#bfdbfe", "aurora_op": ".40",
        "tint": ".08", "tint_stroke": ".30", "green": "#1a7f37",
        "name_from": "#141922", "name_to": "#4338ca",
    },
}

# brand colours, used only as small dots on the stack pills (None = theme text colour)
BRAND = {
    "React": "#61dafb", "Next.js": None, "TypeScript": "#3178c6", "Tailwind CSS": "#38bdf8", "Material UI": "#007fff",
    "React Native": "#61dafb", "Expo": None, "iOS": None, "Android": "#3ddc84", "Node.js": "#5fa04e",
    "Express": None, "Python": "#f2c230", "PostgreSQL": "#4169e1", "Supabase": "#3ecf8e", "MySQL": "#4479a1",
    "SQL Server": "#cc2927", "Docker": "#2496ed", "Linux": "#e8b512", "GitHub Actions": "#2088ff",
}

_ids = itertools.count()


def uid(p="i"):
    return f"{p}{next(_ids)}"


def esc(s):
    return html.escape(str(s), quote=True)


def tw(text, font, size, tracking=0.0):
    m = METRICS[font]
    return sum(m.get(ch, 0.6) for ch in text) * size + tracking * len(text)


def wrap(text, font, size, width):
    lines, cur = [], ""
    for word in text.split():
        cand = f"{cur} {word}".strip()
        if cur and tw(cand, font, size) > width:
            lines.append(cur)
            cur = word
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


def fit(text, font, size, width):
    if tw(text, font, size) <= width:
        return text
    while text and tw(text + "…", font, size) > width:
        text = text[:-1]
    return text.rstrip() + "…"


def css(fonts):
    faces = "".join(
        f"@font-face{{font-family:{FAMILY[n][0]};font-weight:{FAMILY[n][1]};"
        f"src:url(data:font/woff2;base64,{FONT_DATA[n]}) format('woff2')}}"
        for n in sorted(fonts)
    )
    return faces + """
text{font-family:S,-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,Roboto,sans-serif}
.m{font-family:M,ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-weight:500}
.b{font-weight:600}
.fu{animation:fu .9s cubic-bezier(.16,1,.3,1) both}
@keyframes fu{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.pulse{transform-box:fill-box;transform-origin:center;animation:pulse 2.4s cubic-bezier(0,0,.2,1) infinite}
@keyframes pulse{0%{transform:scale(1);opacity:.5}80%,100%{transform:scale(2.8);opacity:0}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}.pulse{opacity:0}}
"""


class Doc:
    """Collects the body of one SVG plus the fonts it needs."""

    def __init__(self, t):
        self.t = t
        self.parts = []
        self.defs = []
        self.fonts = set()

    def c(self, name):
        return self.t.get(name, name)

    def text(self, x, y, s, size, font="sans-400", color="text", anchor=None, tracking=0, cls="", style=""):
        self.fonts.add(font)
        classes = " ".join(filter(None, ["m" if font.startswith("mono") else "", "b" if font == "sans-600" else "", cls]))
        attrs = f' class="{classes}"' if classes else ""
        if anchor:
            attrs += f' text-anchor="{anchor}"'
        if tracking:
            attrs += f' letter-spacing="{tracking}"'
        if style:
            attrs += f' style="{style}"'
        self.parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{self.c(color)}"{attrs}>{s}</text>')

    def raw(self, s):
        self.parts.append(s)

    def label(self, x, y, s):
        self.raw(f'<rect x="{x}" y="{y - 10}" width="3" height="13" rx="1.5" fill="{self.t["accent"]}"/>')
        self.text(x + 12, y, esc(s.upper()), 11, "mono-500", "subtle", tracking=1.4)

    def pill(self, x, y, s, size=11, h=22, dot=None, text_color="muted"):
        w = tw(s, "mono-500", size) + (30 if dot else 20)
        self.raw(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{h}" rx="{h / 2}" fill="{self.t["pill"]}" stroke="{self.t["border"]}"/>')
        tx = x + 10
        if dot:
            self.raw(f'<circle cx="{x + 12:.1f}" cy="{y + h / 2}" r="3.2" fill="{dot}"/>')
            tx = x + 21
        self.text(tx, y + h / 2 + size * 0.36, esc(s), size, "mono-500", text_color)
        return w

    def status(self, x, y, s, size=11, h=21):
        col = self.t["green"]
        w = tw(s, "mono-500", size) + 30
        self.raw(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{h}" rx="{h / 2}" fill="{col}" fill-opacity="{self.t["tint"]}" '
                 f'stroke="{col}" stroke-opacity="{self.t["tint_stroke"]}"/><circle cx="{x + 12:.1f}" cy="{y + h / 2}" r="3" fill="{col}"/>')
        self.text(x + 21, y + h / 2 + size * 0.36, esc(s), size, "mono-500", col)
        return w

    def svg(self, w, h, label, card=True):
        cid = uid("cl")
        bg = border = ""
        body = "".join(self.parts)
        if card:
            bg = f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="14" fill="{self.t["card"]}"/>'
            border = f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="14" fill="none" stroke="{self.t["border"]}"/>'
            self.defs.append(f'<clipPath id="{cid}"><rect width="{w}" height="{h}" rx="14"/></clipPath>')
            body = f'<g clip-path="url(#{cid})">{body}</g>'
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" '
            f'aria-label="{esc(label)}"><title>{esc(label)}</title><style>{css(self.fonts)}</style>'
            f'<defs>{"".join(self.defs)}</defs>{bg}{body}{border}</svg>'
        )


def delay(i, base=0.0, step=0.06):
    return f"animation-delay:{base + i * step:.2f}s"


# ---------------------------------------------------------------- icons (24x24 grid, stroked)
ICONS = {
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3a14 14 0 0 1 0 18a14 14 0 0 1 0-18"/>',
    "linkedin": '<rect x="3" y="3" width="18" height="18" rx="3"/><path d="M8 10v7"/><path d="M8 7v.01"/>'
                '<path d="M12 17v-7"/><path d="M12 13a3 3 0 0 1 6 0v4"/>',
    "x": '<path d="M4 4l16 16"/><path d="M20 4L4 20"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6l9-6"/>',
    "arrow": '<path d="M7 17L17 7"/><path d="M8 7h9v9"/>',
    "star": '<path d="M12 3.5l2.6 5.3l5.9.9l-4.25 4.1l1 5.8L12 16.9l-5.25 2.7l1-5.8L3.5 9.7l5.9-.9z"/>',
}


def icon(name, x, y, size, color, sw=1.8, fill="none"):
    s = size / 24
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({s:.3f})" fill="{fill}" stroke="{color}" '
            f'stroke-width="{sw / s:.2f}" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</g>')


def fmt(n):
    return f"{int(n):,}"


# ---------------------------------------------------------------- cards
def hero(t):
    d = Doc(t)
    h = 292
    # static soft glow in the top-right + faint dot grid
    fid, pid, gid, mid = uid("f"), uid("p"), uid("g"), uid("m")
    d.defs.append(
        f'<filter id="{fid}" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="60"/></filter>'
        f'<pattern id="{pid}" width="18" height="18" patternUnits="userSpaceOnUse">'
        f'<circle cx="2" cy="2" r="1" fill="{t["dot"]}" fill-opacity="{t["dot_op"]}"/></pattern>'
        f'<linearGradient id="{gid}" x1="0" x2="1"><stop offset=".3" stop-color="#fff" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="#fff"/></linearGradient>'
        f'<mask id="{mid}"><rect width="{W}" height="{h}" fill="url(#{gid})"/></mask>'
    )
    d.raw(f'<g filter="url(#{fid})" opacity="{t["aurora_op"]}">'
          f'<circle cx="760" cy="10" r="170" fill="{t["accent_soft"]}"/>'
          f'<circle cx="900" cy="200" r="120" fill="{t["accent2_soft"]}"/></g>')
    d.raw(f'<rect width="{W}" height="{h}" fill="url(#{pid})" mask="url(#{mid})"/>')

    st = CFG["status"]
    pw = tw(st, "sans-400", 13) + 42
    d.raw(f'<g class="fu" style="{delay(0)}">'
          f'<rect x="{PAD}" y="{PAD}" width="{pw:.1f}" height="28" rx="14" fill="{t["pill"]}" stroke="{t["border"]}"/>'
          f'<circle class="pulse" cx="{PAD + 16}" cy="{PAD + 14}" r="4" fill="{t["green"]}"/>'
          f'<circle cx="{PAD + 16}" cy="{PAD + 14}" r="4" fill="{t["green"]}"/></g>')
    d.text(PAD + 28, PAD + 18.5, esc(st), 13, "sans-400", "muted", cls="fu", style=delay(0))

    ng = uid("ng")
    name_w = tw(CFG["name"], "sans-600", 48, -1.4)
    d.defs.append(
        f'<linearGradient id="{ng}" gradientUnits="userSpaceOnUse" x1="{PAD}" y1="0" x2="{PAD + name_w}" y2="0">'
        f'<stop offset=".35" stop-color="{t["name_from"]}"/><stop offset="1" stop-color="{t["name_to"]}"/></linearGradient>'
    )
    d.text(PAD - 2, 124, esc(CFG["name"]), 48, "sans-600", f"url(#{ng})", tracking=-1.4, cls="fu", style=delay(1))
    d.text(PAD, 157, f'{esc(CFG["role"])}<tspan fill="{t["subtle"]}">  ·  {esc(CFG["focus"])}</tspan>', 17,
           "sans-400", "muted", cls="fu", style=delay(2))

    year = STATS.get("year", "")
    stats = [(STATS.get("repos", 0), "repositories"),
             (STATS.get("commits_year", 0), f"commits in {year}"),
             (STATS.get("prs_year", 0), f"pull requests in {year}"),
             (STATS.get("commits_total", 0), "commits all-time")]
    x = PAD
    for i, (n, lbl) in enumerate(stats):
        num = fmt(n)
        cw = max(tw(num, "sans-600", 24, -0.5), tw(lbl, "sans-400", 12)) + 36
        d.raw(f'<g class="fu" style="{delay(i, 0.25)}">'
              f'<rect x="{x}" y="192" width="{cw:.1f}" height="68" rx="12" fill="{t["pill"]}" fill-opacity=".7" stroke="{t["border"]}"/></g>')
        d.text(x + 18, 225, esc(num), 24, "sans-600", tracking=-0.5, cls="fu", style=delay(i, 0.25))
        d.text(x + 18, 245, esc(lbl), 12, "sans-400", "muted", cls="fu", style=delay(i, 0.25))
        x += cw + 10
    d.text(W - PAD, 245, esc(f"{CFG['location']} · {CFG['website']}"), 12, "mono-500", "subtle", anchor="end",
           cls="fu", style=delay(5, 0.25))

    label = (f"{CFG['name']}: {CFG['role']}, {CFG['focus']}. {CFG['status']}. "
             + ", ".join(f"{fmt(n)} {l}" for n, l in stats) + ".")
    return d.svg(W, h, label), label


def about(t):
    d = Doc(t)
    size, lh = 16, 27
    lines = wrap(CFG["about"], "sans-400", size, W - 2 * PAD)
    full = " ".join(lines)
    ranges = []
    for p in CFG.get("about_highlights", []):
        j = full.find(p)
        if j != -1:
            ranges.append((j, j + len(p)))

    def lit(pos):
        return any(a <= pos < b for a, b in ranges)

    d.label(PAD, PAD + 10, "About")
    off, y = 0, PAD + 46
    for i, line in enumerate(lines):
        segs, k = [], 0
        while k < len(line):
            on = lit(off + k)
            j = k
            while j < len(line) and lit(off + j) == on:
                j += 1
            seg = esc(line[k:j])
            segs.append(f'<tspan fill="{t["text"]}">{seg}</tspan>' if on else seg)
            k = j
        d.text(PAD, y, "".join(segs), size, "sans-400", "muted", cls="fu", style=delay(i, 0.05))
        off += len(line) + 1
        y += lh
    y += 8
    d.raw(f'<line x1="{PAD}" y1="{y}" x2="{W - PAD}" y2="{y}" stroke="{t["border"]}"/>')
    y += 22
    d.text(PAD, y + 16, "OFF THE CLOCK", 11, "mono-500", "subtle", tracking=1.4)
    x = PAD + tw("OFF THE CLOCK", "mono-500", 11, 1.4) + 18
    d.raw(f'<g class="fu" style="{delay(len(lines), 0.05)}">')
    for it in CFG.get("interests", []):
        x += d.pill(x, y, it["label"], 12, 24) + 8
    d.raw("</g>")
    h = y + 24 + PAD - 4
    interests = ", ".join(i["label"] for i in CFG.get("interests", []))
    return d.svg(W, h, f"{CFG['about']} Off the clock: {interests}."), CFG["about"]


def experience(t):
    d = Doc(t)
    rows = CFG["experience"]
    rh = 64
    d.label(PAD, PAD + 10, "Experience")
    y0 = PAD + 26
    lx = PAD + 6
    top, bot = y0 + 26, y0 + (len(rows) - 1) * rh + 26
    rg = uid("rg")
    d.defs.append(f'<linearGradient id="{rg}" gradientUnits="userSpaceOnUse" x1="0" y1="{top}" x2="0" y2="{bot}">'
                  f'<stop offset="0" stop-color="{t["accent"]}"/><stop offset="1" stop-color="{t["border"]}"/></linearGradient>')
    d.raw(f'<line x1="{lx}" y1="{top}" x2="{lx}" y2="{bot}" stroke="url(#{rg})" stroke-width="2" stroke-linecap="round"/>')
    for i, r in enumerate(rows):
        y = y0 + i * rh
        st = delay(i, 0.05)
        cy = y + 26
        cur = r.get("current")
        col = t["green"] if cur else t["accent"]
        node = (f'<circle cx="{lx}" cy="{cy}" r="6" fill="{t["card"]}" stroke="{col}" stroke-width="2"/>'
                f'<circle cx="{lx}" cy="{cy}" r="2.5" fill="{col}"/>')
        if cur:
            node = f'<circle class="pulse" cx="{lx}" cy="{cy}" r="5" fill="{col}"/>' + node
        d.raw(f'<g class="fu" style="{st}">{node}</g>')
        x = PAD + 30
        d.text(x, y + 31, esc(r["company"]), 15, "sans-600", cls="fu", style=st)
        if cur:
            cx = x + tw(r["company"], "sans-600", 15) + 10
            d.raw(f'<g class="fu" style="{st}">')
            d.status(cx, y + 16, "Now", 10.5, 20)
            d.raw("</g>")
        period_w = tw(r["period"], "mono-500", 12)
        role = fit(r["role"], "sans-400", 14, W - x - PAD - period_w - 30)
        d.text(x, y + 52, esc(role), 14, "sans-400", "muted", cls="fu", style=st)
        d.text(W - PAD, y + 31, esc(r["period"]), 12, "mono-500", "subtle", anchor="end", cls="fu", style=st)
    h = y0 + len(rows) * rh + PAD - 20
    label = "Experience: " + "; ".join(f"{r['company']}, {r['role']} ({r['period']})" for r in rows)
    return d.svg(W, h, label), label


def section_title(t, text):
    d = Doc(t)
    up = text.upper()
    gid = uid("st")
    d.defs.append(f'<linearGradient id="{gid}"><stop offset="0" stop-color="{t["accent"]}" stop-opacity=".7"/>'
                  f'<stop offset=".5" stop-color="{t["border"]}"/><stop offset="1" stop-color="{t["border"]}" stop-opacity="0"/></linearGradient>')
    d.text(2, 22, esc(up), 11, "mono-500", "subtle", tracking=1.4)
    lx = 2 + tw(up, "mono-500", 11, 1.4) + 14
    d.raw(f'<rect x="{lx:.1f}" y="18" width="{W - lx:.1f}" height="1" fill="url(#{gid})"/>')
    return d.svg(W, 32, text, card=False)


def project(t, p, i):
    d = Doc(t)
    h = 100
    a = t["accent"]
    d.fonts.add("sans-600")
    d.raw(f'<g class="fu">'
          f'<rect x="{PAD}" y="28" width="44" height="44" rx="12" fill="{a}" fill-opacity="{t["tint"]}" stroke="{a}" stroke-opacity="{t["tint_stroke"]}"/>'
          f'<text x="{PAD + 22}" y="57.5" font-size="19" class="b" fill="{a}" text-anchor="middle">{esc(p.get("glyph", p["name"][0]))}</text>'
          "</g>")
    x0 = PAD + 62
    stars = STATS.get("stars_by_repo", {}).get(p.get("repo", ""), 0)
    d.text(x0, 46, esc(p["name"]), 16, "sans-600", cls="fu")
    x = x0 + tw(p["name"], "sans-600", 16) + 12
    if p.get("status"):
        d.raw('<g class="fu">')
        d.status(x, 31, p["status"])
        d.raw("</g>")
    if stars:
        d.raw(f'<g class="fu">{icon("star", x, 33, 15, t["muted"], 1.6)}</g>')
        d.text(x + 20, 45.5, fmt(stars), 13, "mono-500", "muted", cls="fu")
    tags_w = sum(tw(tg, "mono-500", 11) + 28 for tg in p["tags"]) - 8
    tx = W - PAD - 34 - tags_w
    d.raw('<g class="fu">')
    for tg in p["tags"]:
        tx += d.pill(tx, 31, tg) + 8
    d.raw("</g>")
    d.raw(f'<g class="fu">{icon("arrow", W - PAD - 16, 34, 16, t["subtle"], 1.8)}</g>')
    desc = fit(p["desc"], "sans-400", 14, W - x0 - PAD - 20)
    d.text(x0, 70, esc(desc), 14, "sans-400", "muted", cls="fu")
    label = f"{p['name']}: {p['desc']} ({', '.join(p['tags'])})"
    return d.svg(W, h, label), label


def stack(t):
    d = Doc(t)
    groups = CFG["stack"]
    rh = 42
    d.label(PAD, PAD + 10, "Stack")
    y0 = PAD + 32
    for i, g in enumerate(groups):
        y = y0 + i * rh
        st = delay(i, 0.05)
        d.text(PAD, y + 17.5, esc(g["group"]), 14, "sans-400", "subtle", cls="fu", style=st)
        x = PAD + 120
        d.raw(f'<g class="fu" style="{st}">')
        for it in g["items"]:
            x += d.pill(x, y, it, 12, 26, dot=BRAND.get(it) or t["muted"], text_color="text") + 8
        d.raw("</g>")
    h = y0 + len(groups) * rh + PAD - 16
    label = "Stack: " + "; ".join(f"{g['group']}: {', '.join(g['items'])}" for g in groups)
    return d.svg(W, h, label), label


def contact(t, c, i):
    d = Doc(t)
    w, h = 214, 56
    d.raw(f'<rect x="14" y="12" width="32" height="32" rx="9" fill="{t["pill"]}" stroke="{t["border"]}"/>'
          f'{icon(c["icon"], 20, 18, 20, t["text"], 1.7)}')
    d.text(58, 33, esc(c["label"]), 15, "sans-600")
    d.raw(icon("arrow", w - 32, 21, 14, t["subtle"], 1.8))
    return d.svg(w, h, c["label"])


# ---------------------------------------------------------------- README
def picture(name, alt, width="100%"):
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="assets/profile/{name}-dark.svg">'
            f'<img src="assets/profile/{name}-light.svg" width="{width}" alt="{esc(alt)}"></picture>')


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    alts = {}

    def emit(name, fn, *args):
        for theme, t in THEMES.items():
            content, alt = fn(t, *args)
            (OUT / f"{name}-{theme}.svg").write_text(content)
        alts[name] = alt

    emit("hero", hero)
    emit("about", about)
    emit("experience", experience)
    for i, p in enumerate(CFG["projects"]):
        emit(f"project-{i}", project, p, i)
    emit("stack", stack)
    for theme, t in THEMES.items():
        (OUT / f"title-work-{theme}.svg").write_text(section_title(t, "Selected work"))
        (OUT / f"title-contact-{theme}.svg").write_text(section_title(t, "Get in touch"))
        for i, c in enumerate(CFG["contacts"]):
            (OUT / f"contact-{c['id']}-{theme}.svg").write_text(contact(t, c, i))

    projects = "\n".join(
        f'<a href="{esc(p["url"])}">{picture(f"project-{i}", alts[f"project-{i}"])}</a>'
        for i, p in enumerate(CFG["projects"])
    )
    contacts = "\n".join(
        f'<a href="{esc(c["url"])}">{picture("contact-" + c["id"], c["label"], "24%")}</a>'
        for c in CFG["contacts"]
    )
    readme = f"""<!--
  GENERATED by scripts/build_profile.py. Do not edit by hand.
  Edit profile.config.json, then run:
      python3 scripts/fetch_stats.py && python3 scripts/build_profile.py
  The "Refresh profile" GitHub Action does this every day.
-->

<p align="center">
<a href="https://{esc(CFG['website'])}">{picture("hero", alts["hero"])}</a>
</p>

<p align="center">
{picture("about", alts["about"])}
</p>

<p align="center">
{picture("title-work", "Selected work")}
{projects}
</p>

<p align="center">
{picture("experience", alts["experience"])}
</p>

<p align="center">
{picture("stack", alts["stack"])}
</p>

<p align="center">
{picture("title-contact", "Get in touch")}
{contacts}
</p>
"""
    (ROOT / "README.md").write_text(readme)
    print(f"built {len(list(OUT.glob('*.svg')))} SVGs + README.md")


if __name__ == "__main__":
    main()
