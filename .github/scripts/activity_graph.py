"""Draws the contribution activity graph for the profile README.

Runs inside the "Update stats cards" workflow. Pulls the contribution
calendar from GitHub's GraphQL API and writes profile/activity.svg in the
README's palette. No third-party server involved, so it can't go down.

Local preview with fake data:  python .github/scripts/activity_graph.py --demo
"""
import base64, datetime as dt, json, os, pathlib, random, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / 'profile' / 'activity.svg'
DAYS = 30

BG, SURF, LINE, LINES = '#130A18', '#1F1228', '#34213E', '#291A32'
HI, MID, LOW = '#F7EFF6', '#C4B2CC', '#8B7692'
PUR, PURD, PINK, GOLD = '#B594E3', '#7C51B4', '#E693AC', '#DAB56B'


def fetch(user, token):
    q = ('query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{'
         'totalContributions weeks{contributionDays{date contributionCount}}}}}}')
    req = urllib.request.Request(
        'https://api.github.com/graphql',
        data=json.dumps({'query': q, 'variables': {'login': user}}).encode(),
        headers={'Authorization': f'bearer {token}', 'Content-Type': 'application/json',
                 'User-Agent': 'profile-activity-graph'})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    if 'errors' in data:
        sys.exit(f'GraphQL error: {data["errors"]}')
    cal = data['data']['user']['contributionsCollection']['contributionCalendar']
    days = [(d['date'], d['contributionCount']) for w in cal['weeks'] for d in w['contributionDays']]
    return cal['totalContributions'], days


def demo():
    rnd = random.Random(7); today = dt.date.today(); days = []
    for i in range(365, -1, -1):
        d = today - dt.timedelta(days=i)
        days.append((d.isoformat(), max(0, int(rnd.gauss(4, 4)))))
    return sum(c for _, c in days), days


def font(name, file):
    b64 = base64.b64encode((ROOT / 'assets' / 'fonts' / file).read_bytes()).decode()
    return f"@font-face{{font-family:'{name}';src:url(data:font/woff2;base64,{b64}) format('woff2');}}"


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def smooth(pts):
    d = f'M{pts[0][0]:.1f} {pts[0][1]:.1f}'
    for i in range(len(pts) - 1):
        p0 = pts[max(i - 1, 0)]; p1 = pts[i]; p2 = pts[i + 1]; p3 = pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        # keep the curve from dipping below zero between points
        floor = max(p1[1], p2[1])
        c1 = (c1[0], min(c1[1], floor)); c2 = (c2[0], min(c2[1], floor))
        d += f' C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}'
    return d


def render(total, days):
    win = days[-DAYS:]
    counts = [c for _, c in win]
    # current streak (today may still be empty, so start from yesterday in that case)
    allc = [c for _, c in days]; i = len(allc) - 1
    if allc[i] == 0: i -= 1
    streak = 0
    while i >= 0 and allc[i] > 0: streak += 1; i -= 1
    best = max(counts); month_total = sum(counts)

    W, H = 1200, 400
    L, R, T, B = 78, 1158, 150, 340
    top = max(4, best); step = max(1, -(-top // 4)); top = step * 4
    xs = [L + i * (R - L) / (DAYS - 1) for i in range(DAYS)]
    ys = [B - c / top * (B - T) for c in counts]
    pts = list(zip(xs, ys))
    line = smooth(pts)

    o = []
    o.append(f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="18" fill="{BG}" stroke="{LINE}"/>')
    o.append(f'<rect class="grow" x="34" y="41.4" width="24" height="1.2" fill="{GOLD}" fill-opacity=".6"/>')
    o.append(f'<text class="m up" x="68" y="46" font-size="12.5" letter-spacing="2.4" fill="{GOLD}">CONTRIBUTIONS · LAST {DAYS} DAYS</text>')
    o.append(f'<text class="up" style="animation-delay:.12s" x="32" y="96" font-size="42"><tspan class="s" fill="{HI}">{total:,} contributions </tspan>'
             f'<tspan class="si" fill="{PINK}">in the last year</tspan></text>')
    stats = [(f'{month_total}', f'LAST {DAYS} DAYS'), (f'{best}', 'BEST DAY'), (f'{streak}', 'DAY STREAK')]
    x = W - 34
    for k, (n, lab) in enumerate(reversed(stats)):
        o.append(f'<g class="up" style="animation-delay:{.2 + k*.08:.2f}s"><text class="s" x="{x}" y="82" font-size="34" text-anchor="end" fill="{GOLD}">{n}</text>'
                 f'<text class="m" x="{x}" y="102" font-size="10" letter-spacing="1" text-anchor="end" fill="{LOW}">{lab}</text></g>')
        x -= 138
    for g in range(5):
        y = B - g * (B - T) / 4
        o.append(f'<line x1="{L}" x2="{R}" y1="{y:.1f}" y2="{y:.1f}" stroke="{LINES if g else LINE}" stroke-dasharray="{"0" if g == 0 else "2 5"}"/>')
        o.append(f'<text class="m" x="{L-14}" y="{y+4:.1f}" font-size="10.5" text-anchor="end" fill="{LOW}">{g*step}</text>')
    for i in range(0, DAYS, 5):
        d = dt.date.fromisoformat(win[i][0])
        o.append(f'<text class="m" x="{xs[i]:.1f}" y="{B+24}" font-size="10.5" text-anchor="middle" fill="{LOW}">{d.strftime("%b %d")}</text>')
    o.append(f'<path class="area" d="{line} L{R} {B} L{L} {B} Z" fill="url(#ar)"/>')
    o.append(f'<path class="draw" d="{line}" stroke="url(#ln)" stroke-width="2.6" stroke-linecap="round" fill="none" pathLength="1000"/>')
    for i, (x, y) in enumerate(pts):
        c = GOLD if counts[i] == best and best > 0 else PUR
        o.append(f'<circle class="pt" style="animation-delay:{.6 + i*.045:.2f}s" cx="{x:.1f}" cy="{y:.1f}" r="{4.2 if c == GOLD else 3.2}" fill="{BG}" stroke="{c}" stroke-width="2"/>')
    x, y = pts[-1]
    o.append(f'<circle class="rip" cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{PINK}"/><circle class="pt" style="animation-delay:2s" cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{PINK}"/>')

    css = (font('IS', 'serif.woff2') + font('ISI', 'serif-italic.woff2') + font('SM', 'mono.woff2') +
           ".s{font-family:'IS',Georgia,serif}.si{font-family:'ISI',Georgia,serif}.m{font-family:'SM','Courier New',monospace}"
           "text{white-space:pre}"
           ".up{animation:up .9s cubic-bezier(.22,1,.36,1) both}@keyframes up{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}"
           ".grow{transform-box:fill-box;transform-origin:left center;animation:grow 1s cubic-bezier(.22,1,.36,1) both}@keyframes grow{from{transform:scaleX(0)}}"
           ".draw{stroke-dasharray:1000;animation:draw 2.2s .3s cubic-bezier(.45,0,.2,1) both}@keyframes draw{from{stroke-dashoffset:1000}to{stroke-dashoffset:0}}"
           ".area{animation:fade 1.4s 1.2s ease both}@keyframes fade{from{opacity:0}}"
           ".pt{transform-box:fill-box;transform-origin:center;animation:pop .45s cubic-bezier(.34,1.56,.64,1) both}@keyframes pop{from{opacity:0;transform:scale(0)}}"
           ".rip{transform-box:fill-box;transform-origin:center;animation:rip 2.2s 2.2s ease-out infinite both}@keyframes rip{0%{opacity:.8;transform:scale(1)}100%{opacity:0;transform:scale(3.4)}}"
           "@media (prefers-reduced-motion:reduce){*{animation:none!important}}")
    defs = (f'<linearGradient id="ar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{PURD}" stop-opacity=".45"/><stop offset="1" stop-color="{PURD}" stop-opacity="0"/></linearGradient>'
            f'<linearGradient id="ln" x1="0" x2="1"><stop offset="0" stop-color="{PUR}"/><stop offset=".6" stop-color="{PINK}"/><stop offset="1" stop-color="{GOLD}"/></linearGradient>')
    title = f'{total} contributions in the last year; {month_total} in the last {DAYS} days'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" role="img" aria-label="{esc(title)}">'
            f'<title>{esc(title)}</title><defs><style>{css}</style>{defs}</defs>{"".join(o)}</svg>')


if __name__ == '__main__':
    if '--demo' in sys.argv:
        total, days = demo()
    else:
        total, days = fetch(os.environ['GH_USER'], os.environ['GH_TOKEN'])
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(render(total, days))
    print(f'wrote {OUT}')
