"""Download 2026 games and betting lines from the CollegeFootballData API into data/.

Needs the environment variable CFBD_API_KEY (set as a GitHub secret).
Writes data/games_2026.csv and data/lines_2026.csv in the same format as the CFBD Exporter.
"""
import csv, json, os, sys, time, urllib.request, urllib.error

YEAR = int(os.environ.get('SEASON', '2026'))
KEY = os.environ.get('CFBD_API_KEY', '').strip()
BASE = 'https://api.collegefootballdata.com'

class KeyRejected(Exception): pass

def get(path, tries=4):
    """GET with retries: waits 15s, 45s, 90s between attempts on outages, rate limits or timeouts."""
    req = urllib.request.Request(BASE + path, headers={'Authorization': f'Bearer {KEY}', 'Accept': 'application/json'})
    for k in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code in (401, 403): raise KeyRejected(f'HTTP {e.code}')
            err = f'HTTP {e.code}'
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            err = repr(e)
        print(f'Attempt {k + 1} of {tries} for {path} failed: {err}')
        if k < tries - 1: time.sleep((15, 45, 90)[k])
    raise RuntimeError(f'{path} failed after {tries} attempts ({err})')

def cap(k): return k[:1].upper() + k[1:]

def cell(v):
    if v is None: return ''
    if isinstance(v, bool): return 'true' if v else 'false'
    if isinstance(v, list): return ','.join(str(x) for x in v)
    return v

def games_csv(rows, path):
    keys = []
    for r in rows:
        for k in r:
            if k not in keys: keys.append(k)
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh); w.writerow([cap(k) for k in keys])
        for r in rows: w.writerow([cell(r.get(k)) for k in keys])

def lines_csv(rows, path):
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh); w.writerow(['Id', 'HomeTeam', 'HomeScore', 'AwayTeam', 'AwayScore', 'LineProvider', 'Spread'])
        for g in rows:
            for ln in g.get('lines') or []:
                if ln.get('spread') is None: continue
                w.writerow([g['id'], g.get('homeTeam'), cell(g.get('homeScore')), g.get('awayTeam'), cell(g.get('awayScore')), ln.get('provider'), ln['spread']])

def num(v):
    try: return float(v)
    except (TypeError, ValueError): return None

def adv_csv(rows, path):
    """CFBD advanced game stats -> one row per team per game (offense and defense efficiency)."""
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh); w.writerow(['GameId', 'Season', 'Week', 'Team', 'Opponent', 'Plays', 'PPA', 'TotalPPA', 'SuccessRate', 'DefPPA', 'DefSuccessRate'])
        n = 0
        for r in rows:
            o = r.get('offense') or {}; d = r.get('defense') or {}
            plays, ppa, tot = num(o.get('plays')), num(o.get('ppa')), num(o.get('totalPPA'))
            if tot is None and ppa is not None and plays: tot = ppa * plays
            if tot is None: continue
            w.writerow([r.get('gameId', r.get('game_id')), r.get('season', ''), r.get('week', ''), r.get('team'), r.get('opponent'),
                        cell(plays), cell(ppa), round(tot, 3), cell(num(o.get('successRate'))), cell(num(d.get('ppa'))), cell(num(d.get('successRate')))])
            n += 1
    return n

def fetch_adv():
    """Per-game efficiency (PPA) for 2021 to now. Past seasons download once; this season every run."""
    for y in range(2021, YEAR + 1):
        path = f'data/adv_{y}.csv'
        if y < YEAR and os.path.exists(path): continue
        try:
            n = adv_csv(get(f'/stats/game/advanced?year={y}&seasonType=regular'), path)
            print(f'Saved {n} efficiency rows for {y}')
        except Exception as e:
            print(f'::warning::Efficiency stats for {y} not downloaded ({e}); will try again next run.')

def fetch_logos():
    """Save team and conference logos into the site (../logos) once, so graphics can be downloaded with one click."""
    meta = json.load(open('team_meta.json'))
    want = [(m.get('logo'), 'teams') for m in meta['teams'].values()] + [(m.get('logo'), 'conf') for m in meta['conferences'].values()]
    got = miss = 0
    for url, kind in want:
        if not url: continue
        path = f'../logos/{kind}/{url.rsplit("/", 1)[-1]}'
        if os.path.exists(path): continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (AR Poll site builder)'})
            with urllib.request.urlopen(req, timeout=30) as r: data = r.read()
            if data[:4] != b'\x89PNG': raise ValueError('not a PNG')
            open(path, 'wb').write(data); got += 1
        except Exception as e:
            miss += 1; print(f'Logo not saved {url}: {e}')
    print(f'Logos: {got} new, {miss} missing')

if __name__ == '__main__':
    if not KEY: sys.exit('CFBD_API_KEY is not set')
    try:
        games = get(f'/games?year={YEAR}&seasonType=regular&classification=fbs')
    except KeyRejected as e:
        sys.exit(f'::error::CollegeFootballData rejected the API key ({e}). Check the CFBD_API_KEY secret in Settings > Secrets and variables > Actions.')
    except Exception as e:
        # outage or rate limit: keep last saved games so the site still rebuilds; the next scheduled run catches up
        print(f'::warning::CollegeFootballData download failed ({e}). Rebuilding with the last saved games.')
        sys.exit(0)
    if not isinstance(games, list) or not games:
        print('::warning::No games returned; rebuilding with the last saved games.'); sys.exit(0)
    games_csv(games, 'data/games_2026.csv')
    try:
        lines_csv(get(f'/lines?year={YEAR}&seasonType=regular'), 'data/lines_2026.csv')
    except Exception as e:
        print('Lines download failed, keeping the old lines file:', e)
    print(f'Saved {len(games)} games, {sum(1 for g in games if g.get("homePoints") is not None)} completed')
    for extra in (fetch_adv, fetch_logos):   # extras never stop the weekly update
        try: extra()
        except Exception as e: print(f'::warning::{extra.__name__} skipped: {e}')
