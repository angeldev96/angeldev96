"""Dev-only helper: build the embedded font subsets + glyph metrics used by build_profile.py.

Geist and Geist Mono (Vercel, SIL OFL 1.1), variable woff2 from Google Fonts. Requires fonttools + brotli:
    pip install fonttools brotli
    python3 scripts/subset_font.py path/to/geist.woff2 path/to/geistmono.woff2
Writes assets/fonts/{sans-400,sans-600,mono-500}.woff2 and assets/fonts/metrics.json.
"""
import json
import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

OUT = Path(__file__).resolve().parent.parent / "assets" / "fonts"
GLYPHS = "".join(chr(c) for c in range(0x20, 0x7F)) + "·—–…↗→←•★✓ñÑáéíóúÁÉÍÓÚ¿¡’“”"


def build(src, weight, name, metrics):
    font = TTFont(src)
    if "fvar" in font:
        font = instancer.instantiateVariableFont(font, {"wght": weight})
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern"]
    opts.name_IDs = ["*"]
    opts.notdef_outline = True
    s = subset.Subsetter(opts)
    s.populate(text=GLYPHS)
    s.subset(font)
    upm = font["head"].unitsPerEm
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    metrics[name] = {ch: round(hmtx[cmap[ord(ch)]][0] / upm, 4) for ch in GLYPHS if ord(ch) in cmap}
    font.flavor = "woff2"
    font.save(OUT / f"{name}.woff2")
    print(f"wrote {name}.woff2")


metrics = {}
build(sys.argv[1], 400, "sans-400", metrics)
build(sys.argv[1], 600, "sans-600", metrics)
build(sys.argv[2], 500, "mono-500", metrics)
(OUT / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, separators=(",", ":")))
print("wrote metrics.json")
