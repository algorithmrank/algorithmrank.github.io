"""Fit the AR preseason prior: last season's AR rating + roster talent + returning production.

Target: each team's full-season AR rating in year Y (games only, no prior).
Features (all known before the season): rating in Y-1, 247 team talent in Y, returning production (PercentPPA) in Y.
Train on 2022-2024, validate on 2025, then refit on 2022-2025 for the 2026 prior.
"""
import csv, glob, json, numpy as np
import backtest as B

def read(pattern_header, folders=('data', 'data2')):
    rows = []
    for f in sum([glob.glob(f'{d}/*.csv') for d in folders], []):
        h = open(f, encoding='utf-8-sig').readline()
        if pattern_header in h: rows += list(csv.DictReader(open(f, encoding='utf-8-sig')))
    return rows

TAL = {}
for r in read('"Talent"'):
    v = float(r['Talent']); TAL[(int(r['Year']), r['Team'])] = v if v > 50 else None   # service academies report 0
RET = {}
for r in read('"PercentPPA"'):
    v = float(r['PercentPPA']); tot = float(r['TotalPPA'])
    RET[(int(r['Season']), r['Team'])] = None if (v == 0 and tot == 0) else float(np.clip(v, 0, 1.1))

P = dict(B.DEFAULTS, prior_weight=0.001, half_life=50, soft_k=60)
FINAL = {y: B.final_ratings(y, P) for y in B.SEAS}           # games-only season ratings

def features(y, teams, last):
    """Rows of [last, last*ret, talent_z, has_last, has_tal] for season y."""
    tv = [TAL.get((y, t)) for t in teams if TAL.get((y, t))]
    mu, sd = np.mean(tv), np.std(tv)
    lm = np.mean(list(last.values()))
    X = []
    for t in teams:
        l = last.get(t); ret = RET.get((y, t)); tal = TAL.get((y, t))
        has_l = l is not None; lv = (l - lm) if has_l else 0.0
        r = ret if ret is not None else 0.55
        z = (tal - mu) / sd if tal else 0.0
        X.append([lv, lv * (r - 0.55), z, 0.0 if has_l else 1.0, 1.0 if tal else 0.0])
    return np.array(X)

def dataset(years):
    X, Y, meta = [], [], []
    for y in years:
        teams = sorted(FINAL[y]); last = FINAL.get(y - 1, {})
        F = features(y, teams, last)
        ym = np.mean(list(FINAL[y].values()))
        for t, f in zip(teams, F):
            X.append(f); Y.append(FINAL[y][t] - ym); meta.append((y, t))
    return np.array(X), np.array(Y), meta

def fit(years, ridge=1.0):
    X, Y, _ = dataset(years)
    Xb = np.c_[X, np.ones(len(X))]
    w = np.linalg.solve(Xb.T @ Xb + ridge * np.eye(Xb.shape[1]), Xb.T @ Y)
    return w

def predict(w, y, teams, last):
    return np.c_[features(y, teams, last), np.ones(len(teams))] @ w

NAMES = ['last season', 'last season x returning', 'talent (z)', 'no last season (new FBS)', 'has talent', 'intercept']

if __name__ == '__main__':
    # 1) preseason projection accuracy (team level)
    for lab, tr, te in (('validate 2025', (2022, 2023, 2024), 2025),):
        w = fit(tr); teams = sorted(FINAL[te]); pr = predict(w, te, teams, FINAL[te - 1])
        act = np.array([FINAL[te][t] for t in teams]); act -= act.mean()
        base = np.array([0.9 * (FINAL[te - 1].get(t, np.nan) - np.mean(list(FINAL[te - 1].values()))) for t in teams])
        ok = ~np.isnan(base)
        print(f'{lab}: preseason team-rating error  new prior {np.mean(abs(pr - act)):.2f} pts | last-season-only {np.mean(abs(base[ok] - act[ok])):.2f} pts')
    w = fit((2022, 2023, 2024, 2025))
    print('weights (2022-25):', {n: round(float(v), 3) for n, v in zip(NAMES, w)})
    json.dump(dict(w=w.tolist(), names=NAMES), open('prior_model.json', 'w'), indent=1)
