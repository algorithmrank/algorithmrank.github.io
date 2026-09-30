"""Builds site_data.json for the AR Poll site from the v9 engine."""
import json, math, csv
import numpy as np
from ar_engine import Season, load_games, soft, DEFAULTS
from teams2026 import CONF_ORDER, CONFS
import backtest as B

P = dict(DEFAULTS, prior_weight=1.5, half_life=6, soft_k=100, win_bonus=12.0, hfa_shrink=250, neutral_frac=0.0, line_scale=0.75)
SIG = 15.0
fbs = [t for c in CONF_ORDER for t in CONFS[c]]
conf = {t: c for c in CONF_ORDER for t in CONFS[c]}
games = load_games(['data/games_2026.csv'])
s = Season(games, fbs, conf)
prior = json.load(open('prior2026.json'))
meta = json.load(open('team_meta.json'))
G6 = {'American', 'CUSA', 'MAC', 'Mountain West', 'Pac-12', 'Sun Belt'}
ncdf = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
qual = lambda x: 1 / (1 + math.exp(-x / 8.0))
LAST = int(s.wk[s.played].max())          # last completed week
ASOF = list(range(0, LAST + 1))           # 0 = preseason

gl = []
for i, g in enumerate(games):
    gl.append(dict(id=g['Id'], d=g['StartDate'][:16].replace('T', ' '), wk=int(g['Week']), h=g['HomeTeam'], a=g['AwayTeam'],
                   n=0 if s.home[i] else 1, hp=None if np.isnan(s.hp[i]) else int(s.hp[i]),
                   ap=None if np.isnan(s.ap[i]) else int(s.ap[i]), v=B.LINES.get(g['Id'])))
# pregame AR lines (ratings from games before that week)
cache = {}
def rate(w):
    if w not in cache: cache[w] = s.rate(w, prior, P)
    return cache[w]
byweek = {}
for i, g in enumerate(gl):
    S, hfa = rate(g['wk'] - 1)
    ln = float(s.line(S, hfa, i, g['wk'])); g['line'] = round(ln, 1); g['hwp'] = round(ncdf(ln / SIG), 3)
    if g['hp'] is not None and g['h'] in conf and g['a'] in conf:
        m = g['hp'] - g['ap']; ok = (ln > 0) == (m > 0)
        b = byweek.setdefault(g['wk'], dict(r=0, x=0, n=0, ae=0.0, vr=0, vn=0, vae=0.0, aev=0.0))
        b['r' if ok else 'x'] += 1; b['n'] += 1; b['ae'] += abs(ln - m)
        if g['v'] is not None:
            b['vn'] += 1; b['vr'] += (g['v'] > 0) == (m > 0); b['vae'] += abs(g['v'] - m); b['aev'] += abs(ln - m)
        g['upset'] = 1 if (not ok) and abs(ln) >= 7 else 0

from ar_engine import NW
DM = 0.5 ** (np.abs(np.arange(NW)[:, None] - np.arange(NW)[None, :]) / P['half_life'])
LS = P['line_scale']
weeks = {}
for w in ASOF:
    S, hfa = rate(w)
    cur = min(w + 1, S.shape[1] - 1)
    strength = {n: float(S[s.idx[n], cur]) for n in s.names}
    rank_now = {n: k + 1 for k, n in enumerate(sorted(fbs, key=lambda t: -strength[t]))}
    pw = P['prior_weight']
    rows = {n: dict(w=0, l=0, cw=0, cl=0, os=[], allos=[], rest=[], restos=[], c=dict(opp=0.0, margin=0.0, site=0.0, win=0.0), wsum=pw,
                    t25=[0, 0], wins=[], losses=[]) for n in fbs}
    det = {}
    for i, g in enumerate(gl):
        for side, t, o in (('h', g['h'], g['a']), ('a', g['a'], g['h'])):
            if t not in rows: continue
            r = rows[t]; played = g['hp'] is not None and g['wk'] <= w
            os_then = float(S[s.idx[o], g['wk']])
            isconf = o in conf and conf[o] == conf[t] and conf[t] != 'Independent'
            r['allos'].append(strength[o])
            loc = 0 if g['n'] else (1 if side == 'h' else -1)
            if played:
                pf, pa = (g['hp'], g['ap']) if side == 'h' else (g['ap'], g['hp'])
                raw = pf - pa; win = raw > 0
                r['w' if win else 'l'] += 1
                if isconf: r['cw' if win else 'cl'] += 1
                mc = float(soft(np.array(raw), P['soft_k']))
                sa = float(soft(np.array(raw - hfa * loc), P['soft_k'])) - mc
                wb = P['win_bonus'] * (1 if win else -1)
                gs = os_then + mc + sa + wb
                wt = DM[cur, g['wk']]
                for k, v in (('opp', os_then), ('margin', mc), ('site', sa), ('win', wb)): r['c'][k] += wt * v
                r['wsum'] += wt; r['os'].append(os_then)
                ork = rank_now.get(o)
                if ork and ork <= 25: r['t25'][0 if win else 1] += 1
                (r['wins'] if win else r['losses']).append((ork or 999, g['id']))
                det.setdefault(t, []).append([g['id'], round(os_then, 1), round(gs, 1), round(mc, 1), round(sa, 1), wb])
            else:
                m = LS * (strength[t] - strength[o]) + hfa * loc
                r['rest'].append((ncdf(m / SIG), isconf)); r['restos'].append(strength[o])
                det.setdefault(t, []).append([g['id'], round(os_then, 1), None, None, None, None])
    out = []
    for n, r in rows.items():
        pwin = r['w'] + sum(p for p, _ in r['rest']); tot = r['w'] + r['l'] + len(r['rest'])
        pcw = r['cw'] + sum(p for p, c in r['rest'] if c); pcg = r['cw'] + r['cl'] + sum(1 for _, c in r['rest'] if c)
        c = {k: v / r['wsum'] for k, v in r['c'].items()}
        c['pre'] = pw * prior.get(n, 0.0) / r['wsum']; share = pw / r['wsum']
        best = min(r['wins'])[1] if r['wins'] else None; worst = max(r['losses'])[1] if r['losses'] else None
        out.append(dict(team=n, str=strength[n], w=r['w'], l=r['l'], cw=r['cw'], cl=r['cl'],
                        sos=np.mean(r['os']) if r['os'] else None, tsos=np.mean(r['allos']) if r['allos'] else None,
                        rsos=np.mean(r['restos']) if r['restos'] else None,
                        pw=pwin, pl=tot - pwin, pcw=pcw, pcl=pcg - pcw, c=c, share=share, t25=r['t25'], best=best, worst=worst))
    def rank(key, rev=True):
        v = sorted([(key(o), o['team']) for o in out if key(o) is not None], reverse=rev)
        return {t: k + 1 for k, (_, t) in enumerate(v)}
    ar = rank(lambda o: o['str']); sr = rank(lambda o: o['sos']); tr = rank(lambda o: o['tsos'])
    for o in out: o.update(ar=ar[o['team']], sr=sr.get(o['team']), tr=tr.get(o['team']))
    T = {o['team']: o for o in out}
    champs = {}
    for cn in ['ACC', 'Big Ten', 'Big 12', 'SEC']:
        mem = [o for o in out if conf[o['team']] == cn]
        champs[cn] = max(mem, key=lambda o: ((o['cw'] / (o['cw'] + o['cl'])) if o['cw'] + o['cl'] else 0) * 1000 + o['cw'] - o['ar'] / 1000)['team']
    g6 = min((o for o in out if conf[o['team']] in G6), key=lambda o: o['ar'])['team']
    auto = set(champs.values()) | {g6}
    if T['Notre Dame']['ar'] <= 12: auto.add('Notre Dame')
    order = sorted(out, key=lambda o: (0 if o['team'] in auto else 1, o['ar']))
    field = [o['team'] for o in order[:12]]
    seeds = sorted(field, key=lambda n: (1000 if (n in auto and T[n]['ar'] > 12) else 0) + T[n]['ar'])
    R = lambda x, d=2: None if x is None else round(float(x), d)
    weeks[w] = dict(hfa=round(hfa, 2),
                    teams=[[o['team'], R(o['str']), o['w'], o['l'], o['cw'], o['cl'], R(o['sos']), R(o['tsos']), R(o['rsos']),
                            o['ar'], o['sr'], o['tr'], R(o['pw']), R(o['pl']), R(o['pcw']), R(o['pcl']),
                            R(o['c']['opp']), R(o['c']['margin']), R(o['c']['site']), R(o['c']['win']), R(o['c']['pre']), R(o['share'], 3),
                            o['t25'][0], o['t25'][1], o['best'], o['worst']] for o in out],
                    power={n: round(v, 2) for n, v in strength.items()},
                    det=det, cfp=dict(champs=champs, g6=g6, auto=sorted(auto), seeds=seeds,
                                      out=[o['team'] for o in order[12:16]], nd=T['Notre Dame']['ar']))

import fit_prior as FP
_W = {y: FP.fit(tuple(x for x in (2022, 2023, 2024, 2025) if x != y)) for y in (2022, 2023, 2024, 2025)}
def _prior(y, PP):
    t = sorted(B.SEAS[y].fbs); return dict(zip(t, FP.predict(_W[y], y, t, FP.FINAL.get(y - 1, {})) * 1.3))
B.season_prior = _prior
bt = B.evaluate({k: v for k, v in P.items()}, detail=True)
seg = []
for lo, hi, lab in ((1, 4, 'Weeks 1-4'), (5, 8, 'Weeks 5-8'), (9, 16, 'Weeks 9+')):
    v = np.array([(r[2], r[3], r[4]) for r in bt['rows'] if lo <= r[1] <= hi and r[4] is not None])
    seg.append(dict(lab=lab, n=len(v), su=round(float(np.mean((v[:, 0] > 0) == (v[:, 1] > 0))), 3),
                    mae=round(float(np.mean(abs(v[:, 0] - v[:, 1]))), 2),
                    vsu=round(float(np.mean((v[:, 2] > 0) == (v[:, 1] > 0))), 3), vmae=round(float(np.mean(abs(v[:, 2] - v[:, 1]))), 2)))
backtest = dict(n=bt['n'], su=round(bt['su'], 3), mae=round(bt['mae'], 2), vsu=round(bt['vegas_su'], 3),
                vmae=round(bt['vegas_mae'], 2), ats=round(bt['ats'], 3), seg=seg)

teams_meta = {n: dict(ab=m['abbr'], c=m['color'], c2=m['alt_color'], ink=m['ink'], logo=m['logo'], m=m['mascot'])
              for n, m in meta['teams'].items()}
data = dict(season=2026, last=LAST, asof=ASOF, publish=4, sigma=SIG, games=gl, conf=conf, confs=CONF_ORDER,
            weeks=weeks, picks=byweek, meta=teams_meta, cmeta=meta['conferences'], backtest=backtest,
            params=dict(half_life=P['half_life'], prior_weight=P['prior_weight'], soft_k=P['soft_k'], win=P['win_bonus'], ls=LS))
js = json.dumps(data, separators=(',', ':'))
open('site_data.json', 'w').write(js)
W = weeks[LAST]
top = sorted(W['teams'], key=lambda r: r[9])[:25]
print('KB', len(js) // 1024, '| last week', LAST, '| HFA', W['hfa'])
print('Top 25:', ', '.join(f'{r[0]} {r[1]:.1f} ({r[2]}-{r[3]})' for r in top))
print('bt', data['backtest']['su'], data['backtest']['mae'])
print('CFP:', W['cfp']['seeds'])
print('picks:', {k: (v['r'], v['x'], round(v['ae'] / v['n'], 1), v['vn'], round(v['vae'] / v['vn'], 1) if v['vn'] else None) for k, v in sorted(byweek.items())})
