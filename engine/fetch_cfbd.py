"""Download 2026 games and betting lines from the CollegeFootballData API into data/.

Needs the environment variable CFBD_API_KEY (set as a GitHub secret).
Writes data/games_2026.csv and data/lines_2026.csv in the same format as the CFBD Exporter.
"""
import csv, json, os, sys, urllib.request

YEAR = int(os.environ.get('SEASON', '2026'))
KEY = os.environ.get('CFBD_API_KEY', '').strip()
BASE = 'https://api.collegefootballdata.com'

def get(path):
    req = urllib.request.Request(BASE + path, headers={'Authorization': f'Bearer {KEY}', 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8'))

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

if __name__ == '__main__':
    if not KEY: sys.exit('CFBD_API_KEY is not set')
    games = get(f'/games?year={YEAR}&seasonType=regular&classification=fbs')
    if not games: sys.exit('No games returned; leaving data unchanged')
    games_csv(games, 'data/games_2026.csv')
    try:
        lines_csv(get(f'/lines?year={YEAR}&seasonType=regular'), 'data/lines_2026.csv')
    except Exception as e:
        print('Lines download failed, keeping the old lines file:', e)
    print(f'Saved {len(games)} games, {sum(1 for g in games if g.get("homePoints") is not None)} completed')
