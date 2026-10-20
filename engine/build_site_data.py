"""Builds site_data.json for the AR Poll site from the v9 engine."""
import json, math, csv, glob, os
import numpy as np
from ar_engine import Season, load_games, load_eff, soft, DEFAULTS
from teams2026 import CONF_ORDER, CONFS
import backtest as B

P = dict(DEFAULTS, prior_weight=1.5, half_life=6, soft_k=100, win_bonus=12.0, hfa_shrink=250, neutral_frac=0.0, line_scale=0.75,
         eff_w=0.0)   # efficiency blend: 0 = final scores only (see Method); raise only if the backtest says so
SIG = 15.0
fbs = [t for c in CONF_ORDER for t in CONFS[c]]
conf = {t: c for c in CONF_ORDER for t in CONFS[c]}
games = load_games(['data/games_2026.csv'])
s = Season(games, fbs, conf).set_eff(load_eff(glob.glob('data/adv_2026.csv')))
prior = json.load(open('prior2026.json'))
meta = json.load(open('team_meta.json'))
G6 = {'American', 'CUSA', 'MAC', 'Mountain West', 'Pac-12', 'Sun Belt'}
ncdf = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
qual = lambda x: 1 / (1 + math.exp(-x / 8.0))
LAST = int(s.wk[s.played].max())          # last completed week
# conference title games (CFBD notes read e.g. "SEC Championship"); they never count as conference-record games
CCG = {}
for i, g in enumerate(games):
    if 'championship' in (g.get('Notes') or '').lower() and conf.get(g['HomeTeam']) and conf.get(g['HomeTeam']) == conf.get(g['AwayTeam']):
        CCG[conf[g['HomeTeam']]] = i
CCG_IDS = {games[i]['Id'] for i in CCG.values()}
TITLE_CONFS = [c for c in CONF_ORDER if c != 'Independent']
NEUTRAL_TITLE = {'ACC', 'Big Ten', 'Big 12', 'SEC', 'MAC'}          # others are hosted by the top seed
DIVISIONS = {'Sun Belt': [{'App State', 'Coastal Carolina', 'Georgia Southern', 'Georgia State', 'James Madison', 'Marshall', 'Old Dominion'},
                          {'Arkansas State', 'Louisiana', 'UL Monroe', 'Louisiana Tech', 'South Alabama', 'Southern Miss', 'Troy'}]}
NSIM = 2000
verf = np.vectorize(math.erf)
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
GL = {g['id']: g for g in gl}
DM = 0.5 ** (np.abs(np.arange(NW)[:, None] - np.arange(NW)[None, :]) / P['half_life'])
LS = P['line_scale']
# ---------- season simulation: title games + playoff odds ----------
PRI = np.full(s.T, P['lower_div'])
for n in s.fbs: PRI[s.idx[n]] = 0.0
for n, v in prior.items():
    if n in s.idx: PRI[s.idx[n]] = v
_W = np.arange(NW); DMAT = 0.5 ** (np.abs(_W[:, None] - _W[None, :]) / P['half_life'])
RAW = s.hp - s.ap
CCG_I = set(CCG.values())
CCW = max([int(s.wk[i]) for i in CCG_I] + [15])
FINAL_COL = min(CCW + 1, NW - 1)
FBS_I = np.array([s.idx[n] for n in fbs])
CMEM = {cn: np.array([s.idx[n] for n in CONFS[cn]]) for cn in CONF_ORDER}
ND_I = s.idx['Notre Dame']

def rate_arrays(h, a, wk, home, raw, hfa, mix=None):
    """Same solve as ar_engine.Season.rate with home field held fixed (checked equal to it)."""
    T = s.T; m = (raw if mix is None else mix) - hfa * (home == 1)
    base = soft(m, P['soft_k']); wb = P['win_bonus']
    sh = base + np.where(raw > 0, wb, -wb); sa = -base + np.where(raw < 0, wb, -wb)
    team = np.concatenate([h, a]); opp = np.concatenate([a, h]); w2 = np.concatenate([wk, wk]); s2 = np.concatenate([sh, sa])
    idx = team * NW + w2
    DN = np.bincount(idx, minlength=T * NW).reshape(T, NW) @ DMAT.T
    pw = P['prior_weight']; S = np.repeat(PRI[:, None], NW, 1)
    for _ in range(P['passes']):
        PS = np.bincount(idx, s2 + S[opp, w2], T * NW).reshape(T, NW)
        S = (pw * PRI[:, None] + PS @ DMAT.T) / (pw + DN)
    return S

def select_field(rank_of, champ_of):
    """rank_of: array over all teams (FBS ranks). champ_of: conf -> team index. Returns (seeds list, auto set)."""
    autos = {champ_of[cn] for cn in ('ACC', 'Big Ten', 'Big 12', 'SEC')}
    autos.add(min((champ_of[cn] for cn in G6), key=lambda i: rank_of[i]))
    if rank_of[ND_I] <= 12: autos.add(ND_I)
    order = sorted(FBS_I.tolist(), key=lambda i: (0 if i in autos else 1, rank_of[i]))[:12]
    seeds = sorted(order, key=lambda i: (1000 if (i in autos and rank_of[i] > 12) else 0) + rank_of[i])
    return seeds, autos

def simulate(w, strength, hfa, T):
    """Play out the rest of the season NSIM times. Each simulated game margin = AR line + random error (sd 15).
    Top two in conference win pct meet in the title game (Sun Belt: division winners; ties to the higher current AR Rating).
    Every simulated season is re-rated with the full AR engine, then the 12-team field is picked from those final ratings."""
    rng = np.random.default_rng(2026 + w)
    st = np.array([strength[n] for n in s.names])
    ccg_mask = np.zeros(len(s.h), bool); ccg_mask[list(CCG_I)] = True
    done = s.played & (s.wk <= w)
    rem = np.where(~done & ~ccg_mask)[0]
    ln = LS * (st[s.h[rem]] - st[s.a[rem]]) + hfa * (s.home[rem] == 1)
    M = ln + SIG * rng.standard_normal((NSIM, len(rem)))
    M[M == 0] = 0.5
    title = {}
    for cn in TITLE_CONFS:
        mem = CMEM[cn]; nt = len(mem); k = {int(i): j for j, i in enumerate(mem)}
        cw = np.array([T[s.names[i]]['cw'] for i in mem], float); cl = np.array([T[s.names[i]]['cl'] for i in mem], float)
        tot = cw + cl; wins = np.zeros((NSIM, nt))
        for c, gi in enumerate(rem):
            hh, aa = int(s.h[gi]), int(s.a[gi])
            if hh in k and aa in k:
                wins[:, k[hh]] += M[:, c] > 0; wins[:, k[aa]] += M[:, c] < 0; tot[k[hh]] += 1; tot[k[aa]] += 1
        key = (cw + wins) / np.maximum(tot, 1) * 1000 + st[mem] / 1000
        real = CCG.get(cn); real = real if real is not None and w >= s.wk[real] - 1 else None
        if real is not None:
            t1 = np.full(NSIM, int(s.h[real])); t2 = np.full(NSIM, int(s.a[real]))
            neutral = s.home[real] == 0
        else:
            if cn in DIVISIONS:
                d1, d2 = ([k[s.idx[n]] for n in d] for d in DIVISIONS[cn])
                a1 = np.array(d1)[np.argmax(key[:, d1], 1)]; a2 = np.array(d2)[np.argmax(key[:, d2], 1)]
                sw = key[np.arange(NSIM), a2] > key[np.arange(NSIM), a1]
                j1 = np.where(sw, a2, a1); j2 = np.where(sw, a1, a2)
            else:
                o = np.argsort(-key, 1); j1, j2 = o[:, 0], o[:, 1]
            t1, t2 = mem[j1], mem[j2]; neutral = cn in NEUTRAL_TITLE
        lc = LS * (st[t1] - st[t2]) + (0 if neutral else hfa)
        if real is not None and done[real]:
            mc = np.full(NSIM, RAW[real]); played_ccg = True
        else:
            mc = lc + SIG * rng.standard_normal(NSIM); mc[mc == 0] = 0.5; played_ccg = False
        champ = np.where(mc > 0, t1, t2)
        title[cn] = dict(t1=t1, t2=t2, mc=mc, champ=champ, neutral=bool(neutral), real=real, played=played_ccg)
    # re-rate every simulated season and pick the field
    base_i = np.where(done)[0]
    bh, ba, bw, bhm, br = s.h[base_i], s.a[base_i], s.wk[base_i], s.home[base_i], RAW[base_i]
    bmx = s.mixed(base_i, P)
    rh, ra, rw, rhm = s.h[rem], s.a[rem], s.wk[rem], s.home[rem]
    add = [cn for cn in TITLE_CONFS if not title[cn]['played']]
    cwk = np.array([int(s.wk[title[cn]['real']]) if title[cn]['real'] is not None else CCW for cn in add])
    chm = np.array([0 if title[cn]['neutral'] else 1 for cn in add])
    n_cfp = np.zeros(s.T); n_bye = np.zeros(s.T); n_ch = np.zeros(s.T)
    for i in range(NSIM):
        ch = np.array([title[cn]['t1'][i] for cn in add]); ca = np.array([title[cn]['t2'][i] for cn in add])
        cm = np.array([title[cn]['mc'][i] for cn in add])
        S = rate_arrays(np.concatenate([bh, rh, ch]).astype(int), np.concatenate([ba, ra, ca]).astype(int),
                        np.concatenate([bw, rw, cwk]).astype(int), np.concatenate([bhm, rhm, chm]),
                        np.concatenate([br, M[i], cm]), hfa, np.concatenate([bmx, M[i], cm]))
        fin = S[FBS_I, FINAL_COL]
        rank_of = np.zeros(s.T, int); rank_of[FBS_I[np.argsort(-fin)]] = np.arange(1, len(FBS_I) + 1)
        champ_of = {cn: int(title[cn]['champ'][i]) for cn in TITLE_CONFS}
        seeds, autos = select_field(rank_of, champ_of)
        n_cfp[seeds] += 1; n_bye[seeds[:4]] += 1
        for v in champ_of.values(): n_ch[v] += 1
    odds = {s.names[i]: [round(n_cfp[i] / NSIM, 3), round(n_bye[i] / NSIM, 3), round(n_ch[i] / NSIM, 3)]
            for i in FBS_I if n_cfp[i] or n_ch[i]}
    res = {}
    for cn in TITLE_CONFS:
        x = title[cn]; mem = [int(i) for i in CMEM[cn]]
        game = {i: 0 for i in mem}; won = {i: 0 for i in mem}; pairs = {}
        for a_, b_, c_ in zip(x['t1'].tolist(), x['t2'].tolist(), x['champ'].tolist()):
            game[a_] += 1; game[b_] += 1; won[c_] += 1; pairs[(a_, b_)] = pairs.get((a_, b_), 0) + 1
        (a, b), cnt = max(pairs.items(), key=lambda kv: kv[1])
        pa = 0.5 * (1 + math.erf((LS * (st[a] - st[b]) + (0 if x['neutral'] else hfa)) / SIG / math.sqrt(2)))
        win, wp = (s.names[a], pa) if pa >= .5 else (s.names[b], 1 - pa)
        if x['played']: win, wp = s.names[int(x['champ'][0])], 1.0
        top = sorted(mem, key=lambda j: (-won[j], -game[j]))[:4]
        res[cn] = dict(m=[s.names[a], s.names[b]], mp=round(cnt / NSIM, 3), win=win, wp=round(wp, 3), neutral=x['neutral'],
                       real=x['real'] is not None, done=x['played'],
                       odds=[[s.names[j], round(game[j] / NSIM, 3), round(won[j] / NSIM, 3)] for j in top if won[j] or game[j]])
    return res, odds

RANKS = {}
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
            isconf = o in conf and conf[o] == conf[t] and conf[t] != 'Independent' and g['id'] not in CCG_IDS
            r['allos'].append(strength[o])
            loc = 0 if g['n'] else (1 if side == 'h' else -1)
            if played:
                pf, pa = (g['hp'], g['ap']) if side == 'h' else (g['ap'], g['hp'])
                raw = pf - pa; win = raw > 0
                r['w' if win else 'l'] += 1
                if isconf: r['cw' if win else 'cl'] += 1
                rm = float(s.mixed(np.array([i]), P)[0]) * (1 if side == 'h' else -1)   # = raw when eff_w is 0
                mc = float(soft(np.array(rm), P['soft_k']))
                sa = float(soft(np.array(rm - hfa * loc), P['soft_k'])) - mc
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
    titles, podds = simulate(w, strength, hfa, T)
    champs = {cn: titles[cn]['win'] for cn in ['ACC', 'Big Ten', 'Big 12', 'SEC']}
    g6 = min((titles[cn]['win'] for cn in G6), key=lambda n: T[n]['ar'])
    auto = set(champs.values()) | {g6}
    if T['Notre Dame']['ar'] <= 12: auto.add('Notre Dame')
    order = sorted(out, key=lambda o: (0 if o['team'] in auto else 1, o['ar']))
    field = [o['team'] for o in order[:12]]
    seeds = sorted(field, key=lambda n: (1000 if (n in auto and T[n]['ar'] > 12) else 0) + T[n]['ar'])
    R = lambda x, d=2: None if x is None else round(float(x), d)
    RANKS[w] = {o['team']: o['ar'] for o in out}
    weeks[w] = dict(hfa=round(hfa, 2),
                    teams=[[o['team'], R(o['str']), o['w'], o['l'], o['cw'], o['cl'], R(o['sos']), R(o['tsos']), R(o['rsos']),
                            o['ar'], o['sr'], o['tr'], R(o['pw']), R(o['pl']), R(o['pcw']), R(o['pcl']),
                            R(o['c']['opp']), R(o['c']['margin']), R(o['c']['site']), R(o['c']['win']), R(o['c']['pre']), R(o['share'], 3),
                            o['t25'][0], o['t25'][1], o['best'], o['worst']] for o in out],
                    power={n: round(v, 2) for n, v in strength.items()},
                    det=det, titles=titles, odds=podds, cfp=dict(champs=champs, g6=g6, auto=sorted(auto), seeds=seeds,
                                      out=[o['team'] for o in order[12:16]], nd=T['Notre Dame']['ar']))

# key games: ranked matchups, ranked teams in close games, and toss-ups between good teams (ranks as of kickoff)
keyg = {}
for wk in sorted({g['wk'] for g in gl}):
    rk = RANKS.get(min(wk - 1, LAST))
    if rk is None or wk > LAST + 1: continue
    c1, c2, c3 = [], [], []
    for g in gl:
        if g['wk'] != wk or g['h'] not in conf or g['a'] not in conf: continue
        rh, ra = rk[g['h']], rk[g['a']]; ln = abs(g['line'])
        if rh <= 25 and ra <= 25: c1.append((rh + ra, g['id'], 'Top 25 clash'))
        elif min(rh, ra) <= 25 and ln <= 10: c2.append((ln, g['id'], 'Upset watch'))
        elif ln <= 3.5 and max(rh, ra) <= 60: c3.append((ln + (rh + ra) / 100, g['id'], 'Toss-up'))
    pick = sorted(c1)[:8] + sorted(c2)[:6] + sorted(c3)[:3]
    pick = pick[:12]
    if pick: keyg[wk] = [[gid, rk[GL[gid]['h']], rk[GL[gid]['a']], tag] for _, gid, tag in pick]

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

# ---------- payload for the in-browser scenario builder (latest week) ----------
_S, _h = rate(LAST)
sim = dict(names=s.names, pr=[round(float(x), 3) for x in PRI], hfa=round(float(_h), 4),
           st=[round(float(_S[i, min(LAST + 1, NW - 1)]), 3) for i in range(s.T)],
           g=[[int(s.h[i]), int(s.a[i]), int(s.wk[i]), int(s.home[i]),
               None if not (s.played[i] and s.wk[i] <= LAST) else float(RAW[i]), 1 if i in CCG_I else 0, games[i]['Id'],
               None if not (s.played[i] and s.wk[i] <= LAST) else round(float(s.mixed(np.array([i]), P)[0]), 3)] for i in range(len(s.h))],
           ccw=CCW, fcol=FINAL_COL, div={k: [sorted(d) for d in v] for k, v in DIVISIONS.items()}, neutral=sorted(NEUTRAL_TITLE),
           tconfs=TITLE_CONFS, g6=sorted(G6), nw=NW, ccg={cn: games[i]['Id'] for cn, i in CCG.items()},
           P=dict(k=P['soft_k'], wb=P['win_bonus'], pw=P['prior_weight'], hl=P['half_life'], passes=P['passes'], ls=LS, sig=SIG))

# ---------- past seasons: final regular-season AR polls (title games included, bowls and playoff not) ----------
archive = {}; hist = {}
for y in sorted(B.SEAS):
    if y >= 2026: continue
    ss = B.SEAS[y]; pri = _prior(y, P) if y in _W else None
    Sy, hy = ss.rate(99, pri, P); col = min(int(ss.wk.max()) + 1, NW - 1)
    sty = {n: float(Sy[ss.idx[n], col]) for n in ss.names}
    rec_ = {n: [0, 0] for n in ss.fbs}; opp = {n: [] for n in ss.fbs}
    for i in np.where(ss.played)[0]:
        hn, an = ss.names[ss.h[i]], ss.names[ss.a[i]]; hw = ss.hp[i] > ss.ap[i]
        for tm, o, wn in ((hn, an, hw), (an, hn, not hw)):
            if tm in rec_: rec_[tm][0 if wn else 1] += 1; opp[tm].append(sty[o])
    order = sorted(ss.fbs, key=lambda n: -sty[n]); sosr = {n: k + 1 for k, n in enumerate(sorted(ss.fbs, key=lambda n: -np.mean(opp[n])))}
    yr = [r for r in bt['rows'] if r[0] == y]
    v = np.array([(r[2], r[3]) for r in yr]) if yr else None
    fb = sorted(ss.fbs); others = [n for n in ss.names if n not in ss.fbs]; nm = fb + others; ix = {n: k for k, n in enumerate(nm)}
    hist[y] = dict(names=nm, nf=len(fb), hfa=round(float(hy), 2), r=[round(sty[n], 2) for n in nm],
                   g=[[ix[ss.names[ss.h[i]]], ix[ss.names[ss.a[i]]], 0 if ss.home[i] else 1, int(ss.hp[i]), int(ss.ap[i]), int(ss.wk[i])] for i in np.where(ss.played)[0]])
    archive[y] = dict(n=len(ss.fbs), top=[[n, ss.conf.get(n, ''), rec_[n][0], rec_[n][1], round(sty[n], 2), sosr[n]] for n in order[:25]],
                      su=None if v is None else round(float(np.mean((v[:, 0] > 0) == (v[:, 1] > 0))), 3),
                      mae=None if v is None else round(float(np.mean(abs(v[:, 0] - v[:, 1]))), 2), games=len(yr))

def local_logo(url, kind):
    """Use the copy saved in the site's logos folder when it exists (same-origin: graphics can be downloaded)."""
    if not url: return url
    f = f'logos/{kind}/{url.rsplit("/", 1)[-1]}'
    return f if os.path.exists('../' + f) else url
for _m in meta['teams'].values(): _m['logo'] = local_logo(_m.get('logo'), 'teams')
for _m in meta['conferences'].values(): _m['logo'] = local_logo(_m.get('logo'), 'conf')
teams_meta = {n: dict(ab=m['abbr'], c=m['color'], c2=m['alt_color'], ink=m['ink'], logo=m['logo'], m=m['mascot'])
              for n, m in meta['teams'].items()}
data = dict(season=2026, last=LAST, asof=ASOF, publish=4, sigma=SIG, games=gl, conf=conf, confs=CONF_ORDER,
            weeks=weeks, picks=byweek, keyg=keyg, sim=sim, archive=archive, hist=hist, meta=teams_meta, cmeta=meta['conferences'], backtest=backtest,
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
