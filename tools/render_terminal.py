#!/usr/bin/env python3
"""
Renders assets/boot.svg -- an animated terminal session for the profile README.

No dependencies. Run it:      python3 tools/render_terminal.py
Refresh with live GitHub data: GITHUB_TOKEN=... GITHUB_USER=vwdshka python3 tools/render_terminal.py

Why a generator instead of hand-written SVG: the file is ~500 lines of computed
keyframes. Editing the content should mean editing SESSION below, not the SVG.
"""

import html
import json
import os
import urllib.request
from pathlib import Path

# --------------------------------------------------------------------------
# Content. Edit this, not the SVG.
# --------------------------------------------------------------------------

PROMPT = "~/vwdshka $ "

# ("cmd", text)              -> typed out character by character, in accent colour
# ("out", text)              -> printed instantly, body colour
# ("row", left, right)       -> printed instantly, two columns
# ("hi",  text)              -> printed instantly, highlight colour
# ("gap",)                   -> blank line
SESSION = [
    ("cmd", "whoami"),
    ("out", "David Gavriilidis - BSc Software Development, University of Bolton"),
    ("gap",),
    ("cmd", "cat focus.md"),
    ("out", "Backend and data extraction. Python, C#, JavaScript."),
    ("dim", "Drawn to problems where the input is hostile and the schema is a lie."),
    ("gap",),
    ("cmd", "ls -1 projects/"),
    ("row", "openchartexcavator", "headless extraction from JS-rendered pages"),
    ("row", "llm-fake-news-detector", "classification over noisy, scraped text"),
    ("row", "cozychatnoui", "a chat server with no UI to hide behind"),
    ("gap",),
    ("cmd", "status"),
    ("hi", "● Open to junior backend / data roles - Greece or EU remote"),
]

# --------------------------------------------------------------------------
# Look. A considered terminal, not a hacker-movie one: deep slate-blue ground,
# aegean cyan for the things you typed, amber reserved for the single line that
# is actually asking the reader for something.
# --------------------------------------------------------------------------

C = {
    "ground": "#101922",
    "chrome": "#18232f",
    "edge":   "#26333f",
    "dim":    "#62778a",
    "body":   "#d7e0e8",
    "bright": "#f2f6fa",
    "accent": "#7fd1d8",
    "amber":  "#e8b563",
}
DOTS = ["#3f4d5a", "#4a5a68", "#556676"]

FONT = ("ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, "
        "'DejaVu Sans Mono', monospace")

FS = 13.0            # font size
CW = FS * 0.6        # monospace advance width
LH = 22.0            # line height
PAD_X = 26.0
BAR_H = 34.0
PAD_TOP = 20.0
PAD_BOT = 22.0
WIDTH = 720.0
COL2 = 26            # column where the right-hand description starts

TYPE_PER_CHAR = 0.055
PAUSE_AFTER_CMD = 0.35
PAUSE_AFTER_OUT = 0.20
HOLD_AT_END = 3.4

# --------------------------------------------------------------------------


def live_repos(user, token):
    """Newest 3 pushed repos, as (name, description). Best effort."""
    req = urllib.request.Request(
        f"https://api.github.com/users/{user}/repos?sort=pushed&per_page=12",
        headers={"Accept": "application/vnd.github+json",
                 "Authorization": f"Bearer {token}",
                 "User-Agent": "profile-readme"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        repos = json.load(r)
    out = []
    for repo in repos:
        if repo.get("fork") or repo.get("archived"):
            continue
        desc = (repo.get("description") or "").strip()
        if not desc:
            continue          # a repo with no description does not deserve a slot
        out.append((repo["name"], desc))
        if len(out) == 3:
            break
    return out


def apply_live(session):
    token, user = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_USER")
    if not (token and user):
        return session
    try:
        rows = live_repos(user, token)
    except Exception as exc:               # never let the cron break the README
        print(f"live refresh skipped: {exc}")
        return session
    if not rows:
        return session
    out, replaced = [], False
    for line in session:
        if line[0] == "row":
            if not replaced:
                replaced = True
                for name, desc in rows:
                    out.append(("row", name[:COL2 - 2], desc[:60]))
            continue
        out.append(line)
    return out


def esc(s):
    return html.escape(s, quote=False)


def build():
    session = apply_live(SESSION)

    # ---- lay the session out on a timeline -------------------------------
    rows, t = [], 0.4
    for line in session:
        kind = line[0]
        if kind == "gap":
            rows.append({"kind": "gap"})
            continue
        if kind == "cmd":
            text = line[1]
            dur = len(text) * TYPE_PER_CHAR
            rows.append({"kind": "cmd", "text": text, "start": t,
                         "dur": dur, "chars": len(text)})
            t += dur + PAUSE_AFTER_CMD
        elif kind == "row":
            rows.append({"kind": "row", "left": line[1], "right": line[2],
                         "start": t, "dur": 0.28})
            t += PAUSE_AFTER_OUT
        else:
            rows.append({"kind": kind, "text": line[1], "start": t, "dur": 0.28})
            t += PAUSE_AFTER_OUT

    cursor_start = t + 0.1
    total = t + HOLD_AT_END
    height = BAR_H + PAD_TOP + (len(rows) + 1) * LH + PAD_BOT

    def pct(seconds):
        return round(max(0.0, min(100.0, seconds / total * 100)), 4)

    # ---- keyframes -------------------------------------------------------
    keyframes, classes = [], []
    for i, r in enumerate(rows):
        if r["kind"] == "gap":
            continue
        a, b = pct(r["start"]), pct(r["start"] + r["dur"])
        if r["kind"] == "cmd":
            keyframes.append(
                f"@keyframes t{i}{{0%,{a}%{{clip-path:inset(0 100% 0 0)}}"
                f"{b}%,100%{{clip-path:inset(0 0 0 0)}}}}")
            classes.append(
                f".t{i}{{animation:t{i} {total}s steps({r['chars']},end) infinite}}")
        else:
            keyframes.append(
                f"@keyframes t{i}{{0%,{a}%{{opacity:0}}{b}%,100%{{opacity:1}}}}")
            classes.append(f".t{i}{{animation:t{i} {total}s linear infinite}}")

    cs = pct(cursor_start)
    keyframes.append(
        f"@keyframes appear{{0%,{cs}%{{opacity:0}}"
        f"{min(cs + 0.01, 100)}%,100%{{opacity:1}}}}")
    keyframes.append("@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}")

    # ---- body ------------------------------------------------------------
    body, y = [], BAR_H + PAD_TOP + FS
    prompt_w = len(PROMPT) * CW

    def text(x, y, s, fill, cls="", weight="400", extra=""):
        w = round(len(s) * CW, 2)
        return (f'<text x="{round(x,2)}" y="{round(y,2)}" fill="{fill}" '
                f'font-weight="{weight}" textLength="{w}" lengthAdjust="spacing"'
                f'{f" class=\"{cls}\"" if cls else ""}{extra}>{esc(s)}</text>')

    for i, r in enumerate(rows):
        if r["kind"] == "gap":
            y += LH
            continue
        if r["kind"] == "cmd":
            body.append(text(PAD_X, y, PROMPT.rstrip() + " ", C["dim"],
                             cls=f"o{i}"))
            body.append(text(PAD_X + prompt_w, y, r["text"], C["accent"],
                             cls=f"t{i}", weight="500"))
            keyframes.append(
                f"@keyframes o{i}{{0%,{pct(r['start'] - 0.12)}%{{opacity:0}}"
                f"{pct(r['start'])}%,100%{{opacity:1}}}}")
            classes.append(f".o{i}{{animation:o{i} {total}s linear infinite}}")
        elif r["kind"] == "row":
            body.append(text(PAD_X, y, r["left"], C["body"], cls=f"t{i}"))
            body.append(text(PAD_X + COL2 * CW, y, r["right"], C["dim"],
                             cls=f"t{i}"))
        elif r["kind"] == "dim":
            body.append(text(PAD_X, y, r["text"], C["dim"], cls=f"t{i}"))
        elif r["kind"] == "hi":
            body.append(text(PAD_X, y, r["text"], C["amber"], cls=f"t{i}",
                             weight="500"))
        else:
            body.append(text(PAD_X, y, r["text"], C["bright"], cls=f"t{i}"))
        y += LH

    # final idle prompt with a blinking block cursor
    body.append(text(PAD_X, y, PROMPT.rstrip() + " ", C["dim"], cls="appear"))
    cursor_y = y - FS + 2
    body.append(
        f'<g class="appear"><rect class="cursor" x="{round(PAD_X + prompt_w, 2)}" '
        f'y="{round(cursor_y,2)}" width="{round(CW,2)}" height="{FS}" '
        f'fill="{C["accent"]}" opacity="0.9"/></g>')
    y += LH

    dots = "".join(
        f'<circle cx="{22 + n*17}" cy="{BAR_H/2}" r="5" fill="{c}"/>'
        for n, c in enumerate(DOTS))

    title = ("<title>Terminal session: David Gavriilidis, software development "
             "graduate, open to junior backend and data roles.</title>")

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH:.0f} {height:.0f}" width="{WIDTH:.0f}" height="{height:.0f}" role="img">
{title}
<style>
text {{ font-family: {FONT}; font-size: {FS}px; white-space: pre; }}
.appear {{ animation: appear {total}s linear infinite; }}
.cursor {{ animation: blink 1.06s steps(1,end) infinite; }}
{chr(10).join(keyframes)}
{chr(10).join(classes)}
@media (prefers-reduced-motion: reduce) {{
  text, .cursor, .appear {{ animation: none !important; clip-path: none !important; opacity: 1 !important; }}
}}
</style>
<rect x="0.5" y="0.5" width="{WIDTH-1:.0f}" height="{height-1:.0f}" rx="10" fill="{C['ground']}" stroke="{C['edge']}"/>
<path d="M0.5 10.5a10 10 0 0 1 10-10h{WIDTH-21:.0f}a10 10 0 0 1 10 10v{BAR_H-10:.0f}H0.5z" fill="{C['chrome']}"/>
<line x1="0.5" y1="{BAR_H}" x2="{WIDTH-0.5:.0f}" y2="{BAR_H}" stroke="{C['edge']}"/>
{dots}
<text x="{WIDTH/2:.0f}" y="{BAR_H/2 + 4:.0f}" fill="{C['dim']}" font-size="11" text-anchor="middle">vwdshka - zsh</text>
{chr(10).join(body)}
</svg>
"""
    out = Path(__file__).resolve().parent.parent / "assets" / "boot.svg"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    print(f"wrote {out}  ({height:.0f}px tall, {total:.1f}s loop)")


if __name__ == "__main__":
    build()
