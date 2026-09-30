"""AR Poll engine v9 (season-generic, numpy).

Rating = opponent-adjusted, time-weighted, softened scoring margin (points vs an average FBS team).
Same math as v8, generalized so any season can be run and backtested.
"""
import csv, math, datetime as dt
import numpy as np

NW = 18  # CFBD weeks 0..17 (regular season)

DEFAULTS = dict(half_life=3.0, prior_weight=1.5, lower_div=-25.0, soft_k=21.0, win_bonus=0.0,
                hfa_default=2.5, hfa_shrink=40, passes=15, sigma=15.0)


def soft(m, k):
    return np.sign(m) * k * np.log1p(np.abs(m) / k)


def load_games(paths, season=None, fbs_only_home=False):
    seen, out = set(), []
    for p in paths:
        with open(p, encoding='utf-8-sig', newline='') as fh:
            for r in csv.DictReader(fh):
                if r['Id'] in seen: continue
                if season and str(r['Season']) != str(season): continue
                seen.add(r['Id']); out.append(r)
    return out


class Season:
    """Pre-processed game table for one season."""
    def __init__(self, games, fbs_teams=None, conf=None):
        self.games = games
        teams = set()
        conf = dict(conf or {})
        cls = {}
        for g in games:
            for s in ('Home', 'Away'):
                t = g[s + 'Team']; teams.add(t)
                c = g.get(s + 'Classification', '')
                if c: cls[t] = c
                if t not in conf and g.get(s + 'Conference') and c == 'fbs':
                    conf[t] = g[s + 'Conference']
        self.fbs = set(fbs_teams) if fbs_teams else {t for t in teams if cls.get(t) == 'fbs'}
        self.conf = conf
        self.names = sorted(self.fbs) + sorted(teams - self.fbs)
        self.idx = {n: i for i, n in enumerate(self.names)}
        T = len(self.names)
        rows = []
        for g in games:
            wk = int(g['Week'])
            played = g['HomePoints'] not in ('', None) and g['AwayPoints'] not in ('', None)
            neutral = str(g['NeutralSite']).lower() == 'true'
            h, a = self.idx[g['HomeTeam']], self.idx[g['AwayTeam']]
            hp = float(g['HomePoints']) if played else np.nan
            ap = float(g['AwayPoints']) if played else np.nan
            ch, ca = conf.get(g['HomeTeam']), conf.get(g['AwayTeam'])
            confgame = bool(ch and ch == ca and 'Indep' not in ch)
            rows.append((h, a, wk, 0 if neutral else 1, hp, ap, confgame, g['Id']))
        self.h = np.array([r[0] for r in rows]); self.a = np.array([r[1] for r in rows])
        self.wk = np.array([r[2] for r in rows]); self.home = np.array([r[3] for r in rows])
        self.hp = np.array([r[4] for r in rows]); self.ap = np.array([r[5] for r in rows])
        self.confgame = np.array([r[6] for r in rows]); self.ids = [r[7] for r in rows]
        self.played = ~np.isnan(self.hp)
        self.T = T

    def rate(self, through_week, prior=None, P=None):
        """Ratings using games in weeks <= through_week. Returns (S[T,NW], hfa)."""
        P = dict(DEFAULTS, **(P or {}))
        self._nf = P.get('neutral_frac', 0.0); self._ls = P.get('line_scale', 1.0)
        T = self.T
        pr = np.full(T, P['lower_div'], float)
        for n in self.fbs: pr[self.idx[n]] = 0.0
        if prior:
            for n, v in prior.items():
                if n in self.idx: pr[self.idx[n]] = v
        use = self.played & (self.wk <= through_week)
        # home field from conference games (home/road balanced within conference)
        cg = use & self.confgame & (self.home == 1)
        n = int(cg.sum()); est = float((self.hp[cg] - self.ap[cg]).mean()) if n else 0.0
        hfa = P.get('hfa_fixed') if P.get('hfa_fixed') is not None else (n * est + P['hfa_shrink'] * P['hfa_default']) / (n + P['hfa_shrink'])
        h, a, wk = self.h[use], self.a[use], self.wk[use]
        raw = self.hp[use] - self.ap[use]
        loc = np.where(self.home[use] == 1, 1.0, P.get('neutral_frac', 0.0))
        m = raw - hfa * loc
        wb = P.get('win_bonus', 0.0); lp = P.get('loss_penalty', wb)   # loss penalty defaults to the win bonus (symmetric)
        base = soft(m, P['soft_k'])
        if P.get('margin_cap'): base = np.clip(base, -P['margin_cap'], P['margin_cap'])
        sh = base + np.where(raw > 0, wb, -lp); sa = -base + np.where(raw < 0, wb, -lp)
        # both sides: team, opp, week, performance from team's view
        team = np.concatenate([h, a]); opp = np.concatenate([a, h]); w2 = np.concatenate([wk, wk]); s2 = np.concatenate([sh, sa])
        W = np.arange(NW)
        D = 0.5 ** (np.abs(W[:, None] - W[None, :]) / P['half_life'])  # D[w,k]
        N = np.zeros((T, NW)); np.add.at(N, (team, w2), 1)
        DN = N @ D.T
        pw = P['prior_weight']
        if P.get('prior_off_week'):   # preseason share fades linearly to zero at this week
            pw = pw * max(0.0, 1 - through_week / P['prior_off_week'])
        pw = max(pw, 1e-6)
        S = np.repeat(pr[:, None], NW, 1)
        for _ in range(P['passes']):
            perf = s2 + S[opp, w2]
            PS = np.zeros((T, NW)); np.add.at(PS, (team, w2), perf)
            S = (pw * pr[:, None] + PS @ D.T) / (pw + DN)
        return S, hfa

    def line(self, S, hfa, gi, wk):
        """Predicted home margin for game index gi, using strengths at week wk."""
        loc = 1.0 if self.home[gi] == 1 else self._nf
        return self._ls * (S[self.h[gi], wk] - S[self.a[gi], wk]) + hfa * loc
