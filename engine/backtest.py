"""Backtest: predict every FBS-vs-FBS regular-season game using only games before it, vs Vegas."""
import csv, glob, math, json, sys, itertools
import numpy as np
from ar_engine import Season, load_games, NW, DEFAULTS

GAME_FILES = [f for f in glob.glob('data/*.csv') if 'HomeClassification' in open(f, encoding='utf-8-sig').readline()]
LINE_FILES = [f for f in glob.glob('data/*.csv') if 'LineProvider' in open(f, encoding='utf-8-sig').readline()]
PREF = ['consensus', 'ESPN Bet', 'DraftKings', 'William Hill (New Jersey)', 'Bovada', 'teamrankings']

def load_lines():
    by = {}
    for f in LINE_FILES:
        for r in csv.DictReader(open(f, encoding='utf-8-sig')):
            if r['Spread'] in ('', None): continue
            by.setdefault(r['Id'], {})[r['LineProvider']] = float(r['Spread'])
    out = {}
    for gid, d in by.items():
        for p in PREF:
            if p in d: out[gid] = -d[p]; break  # home predicted margin
        else: out[gid] = -next(iter(d.values()))
    return out

ALL = load_games(GAME_FILES)
seasons = {}
for g in ALL: seasons.setdefault(int(g['Season']), []).append(g)
SEAS = {y: Season(gs) for y, gs in sorted(seasons.items())}
LINES = load_lines()

def final_ratings(y, P, prior=None):
    s = SEAS[y]; S, _ = s.rate(99, prior, P)
    last = int(s.wk.max())
    return {n: float(S[s.idx[n], last]) for n in s.fbs}

def season_prior(y, P):
    """Prior for season y from season y-1 final ratings, regressed toward the mean."""
    if P.get('reg', 0) == 0 or (y - 1) not in SEAS: return None
    base = PRIORS_CACHE.setdefault((y - 1, P['half_life'], P['soft_k']), final_ratings(y - 1, dict(P, prior_weight=0.001, half_life=50)))
    mu = np.mean(list(base.values()))
    newfbs = P.get('new_fbs', -12.0)
    pri = {n: P['reg'] * (v - mu) for n, v in base.items()}
    for n in SEAS[y].fbs:
        if n not in pri: pri[n] = newfbs
    return pri
PRIORS_CACHE = {}

def evaluate(P, years=(2022, 2023, 2024, 2025), weeks=range(1, 17), detail=False):
    P = dict(DEFAULTS, **P)
    res = []
    for y in years:
        s = SEAS[y]; pri = season_prior(y, P)
        for w in weeks:
            gi = np.where(s.played & (s.wk == w))[0]
            gi = [i for i in gi if s.names[s.h[i]] in s.fbs and s.names[s.a[i]] in s.fbs]
            if not gi: continue
            S, hfa = s.rate(w - 1, pri, P)
            for i in gi:
                ln = s.line(S, hfa, i, w); m = s.hp[i] - s.ap[i]
                res.append((y, w, ln, m, LINES.get(s.ids[i])))
    arr = np.array([(r[2], r[3]) for r in res])
    su = np.mean((arr[:, 0] > 0) == (arr[:, 1] > 0)); mae = np.mean(np.abs(arr[:, 0] - arr[:, 1]))
    out = dict(n=len(res), su=su, mae=mae)
    v = [r for r in res if r[4] is not None]
    if v:
        vv = np.array([(r[2], r[3], r[4]) for r in v])
        out['n_v'] = len(v); out['vegas_su'] = np.mean((vv[:, 2] > 0) == (vv[:, 1] > 0)); out['vegas_mae'] = np.mean(np.abs(vv[:, 2] - vv[:, 1]))
        out['ar_mae_same'] = np.mean(np.abs(vv[:, 0] - vv[:, 1]))
        edge = vv[:, 0] - vv[:, 2]; cover = vv[:, 1] - vv[:, 2]
        k = (np.abs(edge) >= 0) & (cover != 0)
        out['ats'] = np.mean(np.sign(edge[k]) == np.sign(cover[k]))
        k3 = (np.abs(edge) >= 3) & (cover != 0); out['ats3'] = np.mean(np.sign(edge[k3]) == np.sign(cover[k3])); out['n3'] = int(k3.sum())
    if detail: out['rows'] = res
    return out

def fmt(o):
    s = f"n={o['n']} SU {o['su']:.1%} MAE {o['mae']:.2f}"
    if 'n_v' in o: s += f" | vs Vegas(n={o['n_v']}): Vegas SU {o['vegas_su']:.1%} MAE {o['vegas_mae']:.2f}; AR MAE {o['ar_mae_same']:.2f}; ATS {o['ats']:.1%}; ATS|edge>=3 {o['ats3']:.1%} (n={o['n3']})"
    return s

if __name__ == '__main__':
    print({y: (len(s.games), len(s.fbs)) for y, s in SEAS.items()}, 'lines', len(LINES))
    print('no prior      ', fmt(evaluate(dict(reg=0))))
    print('prior reg 0.6 ', fmt(evaluate(dict(reg=0.6))))
