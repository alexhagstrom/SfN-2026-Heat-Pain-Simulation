#!/usr/bin/env python3
"""heat_pain_gui.py: heat-pain rating generator (build specification v2.8) with a configuration GUI. See README.md."""

# #####################################################################################################
# PART 1. THE GENERATOR: verbatim copy of heat_pain_generator.py v2.8 (lines 41 to 429 of the reference)
# #####################################################################################################
import numpy as np
from scipy import stats

__version__ = "2.8"

# =====================================================================================
# SOURCES (spec section 17)
# =====================================================================================
SOURCES = {
    "amir2022": "Amir C, Rose-McCandlish M, Weger R, Dildine TC, Mischkowski D, Necka EA, Lee I, Wager TD, Pine DS, "
                "Atlas LY. Test-retest reliability of an adaptive thermal pain calibration procedure in healthy "
                "volunteers. J Pain 2022;23(9):1543-1555, with Supplementary Materials.",
    "dildine_data": "Dildine TC, Atlas LY. Unpublished dataset, Confidence Database, osf.io/s46pr, with readme.",
    "dildine2020": "Dildine TC, Necka EA, Atlas LY. Confidence in subjective pain is predicted by reaction time during "
                   "decision making. Sci Rep 2020;10:21373.",
    "mischkowski2021": "Mischkowski D, et al. Psychosom Med 2021;83:539-548.",
    "jepma2014": "Jepma M, Jones M, Wager TD. The dynamics of pain: evidence for simultaneous site-specific habituation "
                 "and site-nonspecific sensitization in thermal pain. J Pain 2014;15(7):734-746.",
    "hagander2000": "Hagander LG, Midani HA, Kuskowski MA, Parry GJ. Quantitative sensory testing: effect of site and "
                    "skin temperature on thermal thresholds. Clin Neurophysiol 2000;111:17-22.",
    "taylor1993": "Taylor DJ, McGillis SLB, Greenspan JD. Body site variation of heat pain sensitivity. Somatosens Mot "
                  "Res 1993;10(4):455-465.",
    "eckert2017": "Eckert NR, Vierck CJ, Simon CB, Cruz-Almeida Y, Fillingim RB, Riley JL. Testing assumptions in human "
                  "pain models: psychophysical differences between first and second pain. J Pain 2017;18(3):266-273.",
    "lautenbacher1993": "Lautenbacher S, Rollman GB. Sex differences in responsiveness to painful and non-painful stimuli "
                        "are dependent upon the stimulation method. Pain 1993;53:255-264.",
    "lamotte1978": "LaMotte RH, Campbell JN. Comparison of responses of warm and nociceptive C-fiber afferents in monkey "
                   "with human judgments of thermal pain. J Neurophysiol 1978;41(2):509-528.",
    "schaffner2008": "Schaffner N, Wittwer A, Kut E, Folkers G, Benninger DH, Candia V. Heat pain threshold and tolerance "
                     "show no left-right perceptual differences at complementary sites of the human forearm. Neurosci "
                     "Lett 2008;440(3):309-313.",
    "lotsch2026": "Lotsch J, Fluhr K, Neddermeyer TJ. Quantitative sensory testing dataset with capsaicin and menthol "
                  "sensitization assessing modality-specific sex differences and sensitization effect sizes in 125 "
                  "healthy volunteers. Mendeley Data 2026, V2, doi:10.17632/y6v3rtpgps.2 (CC BY 4.0).",
}

# =====================================================================================
# FIXED CONSTANTS (spec section 4 and the constants table of section 5)
# =====================================================================================
ZERO_C = 32.0  # [refit] (spec 8)
REF = 44.84  # [refit] dildine_data (spec 11.1)
REF45 = 45.0  # [design]
ONSET_EVENTS = 3  # [refit] (spec 11.6)
DURATION_S = 8.0  # [read] amir2022 supplement
WINDOW = (40.0, 49.0)  # [design]
EXTRAP = (34.0, 50.0)  # [refit] dildine_data
GAP_OK = (26.0, 30.0)  # [design]
REVISIT_OK = (156.0, 180.0)  # [design]
UCLIP = 1e-12  # contract 1

# =====================================================================================
# DEFAULT PARAMETERS (spec section 5; refit_results.json `gen.defaults`)
# =====================================================================================
DEFAULT_PARAMS = dict(
    # --- Person population, forearm fresh skin (spec 6, 7) -----------------------------------------
    m1=2.330296123292602,  # [refit] Layer 1b, amir2022
    s1=0.3551431963909783,  # [refit] Layer 1b
    m2=1.6224878511569905,  # [refit] Layer 1b
    s2=0.5000802513346398,  # [refit] Layer 1b
    r=-0.8119759672175496,  # [refit] Layer 1b
    alpha_pop=-3.5271558588770993,  # [refit] lotsch2026 (spec 7.9)
    # --- Forearm to thenar (spec 10) -----------------------------------------------------------------
    Delta=0.5,  # [read] hagander2000
    kappa=1.2,  # [read] eckert2017, taylor1993, hagander2000
    k_slope=0.92,  # [read] taylor1993 Table 3
    rho=0.75,  # [read] lautenbacher1993
    rho_W=0.63,  # [read]/[model] schaffner2008, amir2022
    # --- Within-session dynamics (spec 11) -----------------------------------------------------------
    S=-0.21335495564428558,  # [refit] dildine_data
    sigma_S=0.670463453400068,  # [refit] dildine_data
    m_step=1.43,  # [refit] dildine_data; jepma2014 (spec 11.2)
    gamma=0.04041134212405255,  # [refit] dildine_data
    beta_1=-0.04258038641690283,  # [refit] dildine_data
    beta_2=0.0,  # [refit] (spec 11.1)
    c=0.08796278183812535,  # [refit] dildine_data; co-primary jepma2014
    a=-0.23740212989374126,  # [refit] dildine_data
    a_th=None,  # lamotte1978
    S_th=-1.4628396347267543,  # [read]/[model] lamotte1978 (spec 10)
    sigma_S_th=None,  # register item 43
    # --- Observation noise (spec 13) -----------------------------------------------------------------
    nu=5.860322714474537,  # [refit] dildine_data
    s0=0.3031155704778548,  # [refit]
    s1n=1.3926995502995485,  # [refit]
    w=1.6974674248734303,  # [refit]
    peak=4.44024076572635,  # [refit]
    phi=0.19264867084508813,  # [refit]
)

# spec section 12
SCEN = {'P1': ('forearm', 1.0, 1.0, False), 'P2': ('forearm', 0.0, 0.0, False),
        'P3': ('lamotte', 1.0, 1.0, False), 'P4': ('lamotte', 0.0, 0.0, False),
        'S1': ('forearm', 1.0, 0.0, False), 'S2': ('lamotte', 1.0, 0.0, False),
        'S3': ('forearm', 1.0, 1.0, True)}

# =====================================================================================
# THE THRESHOLD SHAPE (spec 4, step A2; spec 6)
# =====================================================================================
_GTAB = {}


def gq(z, alpha):
    """Standardised skew-normal quantile (spec 4, step A2; spec 6)."""
    if abs(alpha) < 1e-12: return np.asarray(z, float)
    if alpha not in _GTAB:
        zz = np.linspace(-9.0, 9.0, 36001)
        d = alpha / np.sqrt(1 + alpha * alpha); mu = d * np.sqrt(2 / np.pi); sd = np.sqrt(1 - 2 * d * d / np.pi)
        q = stats.skewnorm.ppf(stats.norm.cdf(zz), alpha)
        _GTAB[alpha] = (zz, (q - mu) / sd)
    zz, qq = _GTAB[alpha]
    return np.interp(np.clip(z, -9.0, 9.0), zz, qq)


def thenar_ms(m1, s1, Delta, kappa, alpha):
    """Thenar log-threshold location and scale (spec 4, step A2; spec 10)."""
    g0 = float(gq(0.0, alpha)); med1 = m1 + s1 * g0
    s3 = kappa * s1 * np.exp(med1) / (np.exp(med1) + Delta)
    m3 = np.log(np.exp(med1) + Delta) - s3 * g0
    return m3, s3, med1


def _u(x): return np.clip(x, UCLIP, 1 - UCLIP)


# =====================================================================================
# THE GENERATOR (spec sections 3 and 4)
# =====================================================================================
class Generator:

    def __init__(self, seed, params=None, scenario='P1'):
        if scenario not in SCEN: raise ValueError(f"unknown scenario {scenario}")
        p = dict(DEFAULT_PARAMS)
        for k_, v in (params or {}).items():
            if k_ not in p: raise KeyError(f"unrecognised parameter {k_}")
            p[k_] = v
        self.p = p; self.scenario = scenario
        self.thenar_mode, self.tau_tf, self.tau_ft, self.s3 = SCEN[scenario]
        self.seed = seed
        # Step A1 (contract 1)
        U = np.random.default_rng([seed, 0]).random(6); self._U = U
        m1, s1, m2, s2, r = p['m1'], p['s1'], p['m2'], p['s2'], p['r']
        D, kap, rho = p['Delta'], p['kappa'], p['rho']
        al = p['alpha_pop']
        # Step A2
        m3, s3, _ = thenar_ms(m1, s1, D, kap, al)
        # Steps A3 and A4
        C = np.array([[s1 * s1, r * s1 * s2, rho * s1 * s3], [r * s1 * s2, s2 * s2, rho * r * s2 * s3],
                      [rho * s1 * s3, rho * r * s2 * s3, s3 * s3]])
        zq = stats.norm.ppf(_u(U[:3]))
        x = np.array([m1, m2, m3]) + np.linalg.cholesky(C) @ zq
        x[0] = m1 + s1 * float(gq(zq[0], al)); x[2] = m3 + s3 * float(gq((x[2] - m3) / s3, al))
        # Step A5
        self.z_step = float(stats.norm.ppf(_u(U[3])))
        xi = float(stats.norm.ppf(_u(U[4]))); rw = p['rho_W']
        # Step A6
        lnWth = np.log(np.exp(m2) / p['k_slope']) + rw * (x[1] - m2) + s2 * np.sqrt(max(1 - rw * rw, 0.0)) * xi
        self.thr = {'forearm': ZERO_C + np.exp(x[0]), 'thenar': ZERO_C + np.exp(x[2])}
        self.W = {'forearm': np.exp(x[1]), 'thenar': np.exp(lnWth)}
        # Step A7
        self.b = {g: np.log(4) / np.log((self.thr[g] + self.W[g] - ZERO_C) / (self.thr[g] - ZERO_C)) for g in self.thr}
        self.reset()

    # Step A8
    def step_mean(self, g): return self.p['S'] if (g == 'forearm' or self.thenar_mode == 'forearm') else self.p['S_th']

    def step_sd(self, g):
        if g == 'forearm' or self.thenar_mode == 'forearm': return self.p['sigma_S']
        return self.p['sigma_S'] if self.p['sigma_S_th'] is None else self.p['sigma_S_th']

    def onset(self, g):
        if g == 'thenar' and self.s3: return 0.0
        if g == 'thenar' and self.p['a_th'] is not None: return self.p['a_th']
        return self.p['a']

    def person(self):
        """Spec section 3."""
        out = dict(scenario=self.scenario, step_variate=self.z_step)
        for g in ('forearm', 'thenar'):
            def T_for(R, g=g): return ZERO_C + (self.thr[g] - ZERO_C) * (R / 2.0) ** (1 / self.b[g])
            out[g] = dict(threshold_c=self.thr[g], tolerance_c=self.thr[g] + self.W[g], width_c=self.W[g],
                          exponent=self.b[g], zero_point_c=ZERO_C, step_mean=self.step_mean(g), step_sd=self.step_sd(g),
                          step_person=self.step_mean(g) + self.step_sd(g) * self.z_step, T_for_rating=T_for)
        return out

    def reset(self):
        """Contract 2."""
        self.hist = {(g, j): [] for g in ('forearm', 'thenar') for j in (1, 2, 3)}
        self.prev = None; self.i = 0; self.zprev = None
        self.noise_rng = np.random.default_rng([self.seed, 1])

    def sigma(self, R):
        """Spec 4, step C; spec 13."""
        p = self.p; return p['s0'] + p['s1n'] * np.exp(-(R - p['peak']) ** 2 / (2 * p['w'] ** 2))

    def simulate(self, events, duration_s=DURATION_S):
        """Spec 4, steps B to D; contract 4."""
        if abs(duration_s - DURATION_S) > 1e-12: raise ValueError("duration_s must equal 8.0")
        out = []
        for e in events:
            g = e['region']; j = int(e['spot']); T = float(e['temp_c']); t = float(e['t_s'])
            if g not in ('forearm', 'thenar'): raise ValueError("region must be 'forearm' or 'thenar'")
            if j not in (1, 2, 3): raise ValueError("spot must be 1, 2 or 3")
            self.i += 1; h = self.hist[(g, j)]; v = len(h) + 1
            # Step B
            X = max(T - ZERO_C, 0.0)
            Rg = 2.0 * (X / (self.thr[g] - ZERO_C)) ** self.b[g] if X > 0 else 0.0
            Rraw = Rg * (1.0 + (self.onset(g) if self.i <= ONSET_EVENTS else 0.0))
            if v > 1:
                mv = 1.0 if v == 2 else self.p['m_step']
                inner = mv * self.step_mean(g) + self.p['beta_1'] * (h[-1][0] - REF)
                if v > 2: inner += self.p['beta_2'] * (h[-2][0] - REF)
                Rraw += min(0.0, inner) + mv * self.step_sd(g) * self.z_step
            Rraw += self.p['gamma'] * (min(v, 3) - 1) * (T - REF45)
            if self.prev is not None:
                pg, pj, pT, _ = self.prev
                if not (pg == g and pj == j):
                    if pg == g: tau = 1.0
                    else: tau = self.tau_tf if (pg == 'thenar' and g == 'forearm') else self.tau_ft
                    Rraw += self.p['c'] * tau * (pT - REF45)
            latent = float(min(10.0, max(0.0, Rraw)))
            # Step C
            u = float(stats.t.ppf(_u(self.noise_rng.random()), self.p['nu']))
            zz = u if self.zprev is None else self.p['phi'] * self.zprev + np.sqrt(1 - self.p['phi'] ** 2) * u
            self.zprev = zz
            observed = float(min(10.0, max(0.0, Rraw + self.sigma(Rraw) * zz)))
            # Step D
            opt = False
            if self.prev is not None:
                gap = t - self.prev[3]
                if gap < GAP_OK[0] or gap > GAP_OK[1]: opt = True
            if v > 1:
                rg = t - h[-1][1]
                if rg < REVISIT_OK[0] or rg > REVISIT_OK[1]: opt = True
            out.append(dict(latent=latent, observed=observed, raw=Rraw, z=zz,
                            in_window=bool(WINDOW[0] <= T <= WINDOW[1]),
                            extrapolated=bool(T < EXTRAP[0] or T > EXTRAP[1]),
                            beyond_measured_visits=bool(v >= 4), off_protocol_timing=bool(opt)))
            h.append((T, t)); self.prev = (g, j, T, t)
        return out


def ev(t, region, spot, T):
    """One event record (spec 3)."""
    return dict(t_s=t, region=region, spot=spot, temp_c=T)


# =====================================================================================
# VALIDATION CHECKS 8, 9 AND 10 (spec section 16): identical to refit.py's run_unit_tests
# =====================================================================================
def run_unit_tests():
    R_ = []

    def chk(group, name, cond):
        R_.append(dict(check=group, name=name, passed=bool(cond)))
    mk = lambda **kw: {**dict(sigma_S=0.0), **kw}
    OTHER = lambda: ev(0, 'thenar', 1, 45.0)

    def seqp(*rest, region='thenar'):
        out = [ev(28 * i, region, (i % 3) + 1, 45.0) for i in range(3)]; t = 84.0
        for r in rest:
            r = dict(r); r['t_s'] = t; out.append(r); t += 28.0
        return out
    P = DEFAULT_PARAMS; S = P['S']; B1 = P['beta_1']; GAM = P['gamma']; MS = P['m_step']; C = P['c']
    g = Generator(3, params=mk(), scenario='P1'); pr = g.person()['forearm']
    Rg = lambda T, q=pr: 2.0 * ((T - 32.0) / (q['threshold_c'] - 32.0)) ** q['exponent']
    o = g.simulate(seqp(ev(0, 'forearm', 1, 45.0)))
    chk(8, "first visit carries no step, drift or same-spot history", abs(o[3]['latent'] - Rg(45.0)) < 1e-9)
    g.reset(); o = g.simulate(seqp(ev(0, 'forearm', 1, REF), OTHER(), ev(0, 'forearm', 1, 45.0)))
    chk(8, "second visit at 45 C after 44.84 C carries exactly S", abs(o[5]['latent'] - (Rg(45.0) + S)) < 1e-9)
    g.reset(); o = g.simulate(seqp(ev(0, 'forearm', 1, REF + 3), OTHER(), ev(0, 'forearm', 1, 45.0)))
    chk(8, "prior same-spot visit 3 C above the reference gives min(0, S + 3 beta_1)",
        abs(o[5]['latent'] - (Rg(45.0) + min(0.0, S + 3 * B1))) < 1e-9)
    g.reset(); o = g.simulate(seqp(ev(0, 'forearm', 1, 35.0), OTHER(), ev(0, 'forearm', 1, 45.0)))
    chk(8, "prior same-spot visit at 35 C: the cap binds and the same-spot term is 0", abs(o[5]['latent'] - Rg(45.0)) < 1e-9)
    g2 = Generator(3, params=mk(S=0.0)); q2 = g2.person()['forearm']
    o = g2.simulate(seqp(ev(0, 'forearm', 1, 43.0), OTHER(), ev(0, 'forearm', 1, 45.0)))
    chk(8, "S = 0, prior at 43 C: the cap binds inside the window", abs(o[5]['latent'] - Rg(45.0, q2)) < 1e-9)
    knife = S / (REF - 40.0)
    for b1v, should in [(knife - 0.0005, True), (B1, False)]:
        gk = Generator(3, params=mk(beta_1=b1v)); qk = gk.person()['forearm']
        o = gk.simulate(seqp(ev(0, 'forearm', 1, 40.0), OTHER(), ev(0, 'forearm', 1, 45.0)))
        binds = abs(o[5]['latent'] - Rg(45.0, qk)) < 1e-12
        chk(8, f"knife edge: beta_1 = {b1v:+.4f}, prior at 40 C: cap {'binds' if should else 'does not bind'}", binds == should)
    sz = None
    for sd in range(4000):
        if abs(Generator(sd, params=mk(sigma_S=0.83)).z_step - 1.0) < 0.02: sz = sd; break
    gz = Generator(sz, params=mk(sigma_S=0.83)); z = gz.z_step; qz = gz.person()['forearm']
    o = gz.simulate(seqp(ev(0, 'forearm', 1, REF), OTHER(), ev(0, 'forearm', 1, 45.0)))
    chk(8, "step SD 0.83, z near 1: visit-2 term is min(0, S) + 0.83 z", abs(o[5]['latent'] - Rg(45.0, qz) - (min(0, S) + 0.83 * z)) < 1e-9)
    gz.reset(); o = gz.simulate(seqp(ev(0, 'forearm', 1, REF), OTHER(), ev(0, 'forearm', 1, REF), OTHER(), ev(0, 'forearm', 1, 45.0)))
    chk(8, f"visit-3 term is min(0, {MS:g} S) + {MS:g} x 0.83 z", abs(o[7]['latent'] - Rg(45.0, qz) - (min(0, MS * S) + MS * 0.83 * z)) < 1e-9)
    sdr = None
    for sd in range(4000):
        q = Generator(sd, params=mk()).person()['forearm']
        if 6.0 < 2 * ((49 - 32) / (q['threshold_c'] - 32)) ** q['exponent'] < 9.0: sdr = sd; break
    gd = Generator(sdr, params=mk()); qd = gd.person()['forearm']
    o = gd.simulate(seqp(ev(0, 'forearm', 1, REF), OTHER(), ev(0, 'forearm', 1, 49.0)))
    chk(8, "the drift adds 4 gamma at 49 C on visit 2", abs(o[5]['latent'] - Rg(49.0, qd) - min(0, S) - 4 * GAM) < 1e-9)
    gd.reset(); o = gd.simulate(seqp(ev(0, 'forearm', 1, REF), OTHER(), ev(0, 'forearm', 1, REF), OTHER(), ev(0, 'forearm', 1, 49.0)))
    chk(8, "the drift adds 8 gamma at 49 C on visit 3", abs(o[7]['latent'] - Rg(49.0, qd) - min(0, MS * S) - 8 * GAM) < 1e-9)
    g.reset(); o = g.simulate(seqp(ev(0, 'forearm', 1, REF), OTHER(), ev(0, 'forearm', 1, REF), OTHER(), ev(0, 'forearm', 1, 45.0)))
    chk(8, f"third visit after two priors at 44.84 C, beta_2 = 0: same-spot term is {MS:g} S (a plateau would give S)",
        abs(o[7]['latent'] - Rg(45.0) - MS * S) < 1e-9)
    for sc, expv in [('P1', 4 * C), ('P3', 4 * C), ('S3', 4 * C), ('P2', 0.0), ('P4', 0.0), ('S1', 4 * C), ('S2', 4 * C)]:
        gs = Generator(3, params=mk(), scenario=sc); qs_ = gs.person()['forearm']
        o = gs.simulate(seqp(ev(0, 'thenar', 1, 49.0), ev(0, 'forearm', 1, 45.0)))
        chk(8, f"previous thenar stimulus at 49 C adds {expv:+.4f} to a forearm event under {sc}", abs(o[4]['latent'] - Rg(45.0, qs_) - expv) < 1e-9)
    for sc, expv in [('S1', 0.0), ('S2', 0.0), ('P1', 4 * C)]:
        gs = Generator(3, params=mk(), scenario=sc); qt = gs.person()['thenar']
        Rt = lambda T: 2.0 * ((T - 32.0) / (qt['threshold_c'] - 32.0)) ** qt['exponent']
        o = gs.simulate(seqp(ev(0, 'forearm', 1, 49.0), ev(0, 'thenar', 2, 45.0), region='forearm'))
        chk(8, f"previous forearm stimulus at 49 C adds {expv:+.4f} to a thenar event under {sc}", abs(o[4]['latent'] - Rt(45.0) - expv) < 1e-9)
    g.reset(); o = g.simulate(seqp(ev(0, 'forearm', 1, 49.0), ev(0, 'forearm', 1, 45.0)))
    chk(8, "an immediate same-spot revisit adds no c term", abs(o[4]['latent'] - Rg(45.0) - min(0.0, S + B1 * (49.0 - REF))) < 1e-9)
    g.reset(); o = g.simulate([OTHER(), ev(28, 'thenar', 2, 45.0), ev(56, 'thenar', 3, 45.0), ev(84, 'forearm', 1, 45.0)])
    chk(8, "events 1 to 3 carry the onset term, event 4 carries none", abs(o[3]['latent'] - Rg(45.0)) < 1e-9)
    g.reset(); o = g.simulate([ev(0, 'forearm', 1, 45.0)])
    chk(8, "event 1 carries the onset factor 1 + a", abs(o[0]['latent'] - Rg(45.0) * (1 + P['a'])) < 1e-9)
    gs = Generator(3, params=mk(), scenario='S3'); qt = gs.person()['thenar']
    Rt = lambda T: 2.0 * ((T - 32.0) / (qt['threshold_c'] - 32.0)) ** qt['exponent']
    o = gs.simulate([ev(0, 'thenar', 1, 45.0)])
    chk(8, "under S3, a thenar event 1 carries no onset term", abs(o[0]['latent'] - Rt(45.0)) < 1e-9)
    for sc in ('P3', 'P4'):
        gs = Generator(3, params=mk(), scenario=sc); qt = gs.person()['thenar']
        Rt = lambda T, qt=qt: 2.0 * ((T - 32.0) / (qt['threshold_c'] - 32.0)) ** qt['exponent']
        o = gs.simulate(seqp(ev(0, 'thenar', 1, REF), ev(0, 'forearm', 1, 45.0), ev(0, 'thenar', 1, 45.0), region='forearm'))
        chk(8, f"under {sc}, a thenar second visit carries S_th", abs(o[5]['latent'] - Rt(45.0) - min(0.0, P['S_th'])) < 1e-9)
    g.reset(); before = g.person()
    g.simulate([ev(28 * i, 'forearm' if i < 3 else 'thenar', (i % 3) + 1, 45.0) for i in range(6)])
    g.reset(); after = g.person()
    same = all(abs(before[r][k] - after[r][k]) < 1e-15 for r in ('forearm', 'thenar') for k in ('threshold_c', 'tolerance_c', 'exponent'))
    o1 = g.simulate(seqp(ev(0, 'forearm', 1, 45.0)))
    chk(8, "reset() clears all six histories and leaves person() unchanged", same and abs(o1[3]['latent'] - Rg(45.0)) < 1e-9)
    # ---- check 9: determinism and common random numbers
    E = [ev(28 * i, 'forearm' if i % 2 == 0 else 'thenar', (i // 2) % 3 + 1, 41.0 + i) for i in range(8)]
    a1 = Generator(11).simulate(E); a2 = Generator(11).simulate(E)
    chk(9, "same seed, parameters, scenario and events give identical output", all(x['observed'] == y['observed'] and x['latent'] == y['latent'] for x, y in zip(a1, a2)))
    gg = Generator(11); b1_ = gg.simulate(E); gg.reset(); b2_ = gg.simulate(E)
    chk(9, "after reset() the same events give the same output", all(x['observed'] == y['observed'] for x, y in zip(b1_, b2_)))
    f1 = Generator(11, params=dict(Delta=0.5)).simulate(E); f2 = Generator(11, params=dict(Delta=0.9, kappa=1.37, rho=0.3)).simulate(E)
    fa = [x for x, e in zip(f1, E) if e['region'] == 'forearm']; fb = [x for x, e in zip(f2, E) if e['region'] == 'forearm']
    chk(9, "different thenar offset, spread and correlation leave forearm latents identical to 1e-12", all(abs(x['latent'] - y['latent']) < 1e-12 for x, y in zip(fa, fb)))
    f3 = Generator(11, params=dict(rho_W=0.3)).simulate(E); fc = [x for x, e in zip(f3, E) if e['region'] == 'forearm']
    chk(9, "different rho_W leaves forearm latents identical to 1e-12", all(abs(x['latent'] - y['latent']) < 1e-12 for x, y in zip(fa, fc)))
    n1 = Generator(11, params=dict(nu=5.0)).simulate(E); n2 = Generator(11, params=dict(nu=15.0)).simulate(E)
    za = np.array([x['z'] for x in n1]); zb = np.array([x['z'] for x in n2])
    ua = (za[1:] - P['phi'] * za[:-1]); ub = (zb[1:] - P['phi'] * zb[:-1])
    chk(9, "different noise df give innovations with identical ranks", np.array_equal(stats.rankdata(ua), stats.rankdata(ub)))
    chk(9, "the person stream consumes exactly six uniforms", len(Generator(11)._U) == 6)
    r1 = Generator(11, params=dict(rho_W=1.0))
    chk(9, "at rho_W = 1 the thenar width is exactly W_fa / k", abs(r1.W['thenar'] - r1.W['forearm'] / P['k_slope']) < 1e-12)
    g0_ = Generator(11, params=dict(alpha_pop=0.0)); z1_ = stats.norm.ppf(g0_._U[0])
    chk(9, "alpha_pop = 0 gives the log-normal person: ln(T_thr - 32) = m1 + s1 z1", abs(np.log(g0_.thr['forearm'] - 32) - (P['m1'] + P['s1'] * z1_)) < 1e-12)
    ga_ = Generator(11); gb_ = Generator(11, params=dict(alpha_pop=0.0))
    chk(9, "the population skew leaves the forearm width unchanged", abs(ga_.W['forearm'] - gb_.W['forearm']) < 1e-12)
    # ---- check 10: flags and input handling
    o = Generator(5).simulate([ev(0, 'forearm', 1, 39.9)])
    chk(10, "39.9 C: in_window false, extrapolated false", (not o[0]['in_window']) and (not o[0]['extrapolated']))
    chk(10, "49.0 C: in_window true", Generator(5).simulate([ev(0, 'forearm', 1, 49.0)])[0]['in_window'])
    chk(10, "33.0 C: extrapolated true", Generator(5).simulate([ev(0, 'forearm', 1, 33.0)])[0]['extrapolated'])
    o = Generator(5).simulate([ev(168 * i, 'forearm', 1, 45.0) for i in range(4)])
    chk(10, "a fourth visit to a spot sets beyond_measured_visits", (not o[2]['beyond_measured_visits']) and o[3]['beyond_measured_visits'])
    chk(10, "onsets 31 s apart set off_protocol_timing", Generator(5).simulate([ev(0, 'forearm', 1, 45.0), ev(31, 'forearm', 2, 45.0)])[1]['off_protocol_timing'])
    chk(10, "onsets 29 s apart do not", not Generator(5).simulate([ev(0, 'forearm', 1, 45.0), ev(29, 'forearm', 2, 45.0)])[1]['off_protocol_timing'])
    seq = []; order5 = [('forearm', 1), ('forearm', 2), ('forearm', 3), ('thenar', 1), ('thenar', 2)]
    for i in range(11): seq.append(ev(28 * i, *order5[i % 5], 45.0))
    o = Generator(5).simulate(seq)
    chk(10, "a 5-event spot cycle (140 s revisit) sets off_protocol_timing through the revisit condition", o[5]['off_protocol_timing'])
    seq = []; order6 = [('forearm', 1), ('thenar', 1), ('forearm', 2), ('thenar', 2), ('forearm', 3), ('thenar', 3)]
    for i in range(18): seq.append(ev(28 * i, *order6[i % 6], 45.0))
    chk(10, "the intended 6-spot order (168 s revisit) never sets it", not any(x['off_protocol_timing'] for x in Generator(5).simulate(seq)))
    E0 = [ev(0, 'forearm', 1, 45.0)]; snap = [dict(x) for x in E0]; Generator(5).simulate(E0)
    chk(10, "no input is modified", E0 == snap)
    try: Generator(5).simulate(E0, duration_s=10.0); ok = False
    except ValueError: ok = True
    chk(10, "a duration other than 8 s raises", ok)
    try: Generator(5, params=dict(nonsense=1.0)); ok = False
    except KeyError: ok = True
    chk(10, "an unrecognised parameter key raises", ok)
    return R_


# #####################################################################################################
# PART 2. INTERFACE METADATA (spec sections 5 and 12; generator_parameters.json of the v2.8 package)
# #####################################################################################################
import csv
import json
import math
import os
import platform
import re
import sys
import time
import threading
from datetime import datetime, timezone

import scipy

TOOL_NAME = "heat_pain_gui.py"
TOOL_VERSION = "1.0"
SPEC_VERSION = "2.8"
CONFIG_SCHEMA = "heat_pain_gui.config/1"

# spec section 5
PARAM_GROUPS = [
    "Person population (Layer 1, spec section 6)",
    "Forearm to thenar (Layer 4, spec section 10)",
    "Within-session dynamics (Layer 5, spec section 11)",
    "Observation noise (Layer 6, spec section 13)",
]
_G1, _G2, _G3, _G4 = PARAM_GROUPS
PARAM_META = [
    ("m1", _G1, "mean of ln(T_thr - 32), forearm fresh skin", "2.33030",
     "2.2731 to 2.3875 (approximate conditional interval)", "Layer 1b [refit]", (2.2731, 2.3875), ()),
    ("s1", _G1, "SD of ln(T_thr - 32)", "0.35514", "0.3037 to 0.4066", "Layer 1b [refit]", (0.3037, 0.4066), ()),
    ("m2", _G1, "location of ln W (W = tolerance - threshold)", "1.62249", "1.5290 to 1.7160", "Layer 1b [refit]",
     (1.5290, 1.7160), ()),
    ("s2", _G1, "scale of ln W", "0.50008", "0.4129 to 0.5873", "Layer 1b [refit]", (0.4129, 0.5873), ()),
    ("r", _G1, "correlation of the normal scores of ln(T_thr - 32) and ln W (Gaussian copula)", "-0.81198",
     "-0.8849 to -0.7390", "Layer 1b [refit]", (-0.8849, -0.7390), ()),
    ("alpha_pop", _G1, "skew-normal shape of ln(T_thr - 32), both regions (0 is the log-normal)", "-3.5272",
     "-6.17 to -1.98; log-normal (0) as a reference", "Lotsch et al. thresholds [refit]", (-6.17, -1.98), (0.0,)),
    ("Delta", _G2, "thenar threshold offset at the median (C)", "+0.5",
     "co-primary +0.5 and +0.9; stress +1.6; 0 under P3 and P4 (grid cells)",
     "Hagander 2000 [read]; Taylor, Eckert [read]", None, (0.0, 0.5, 0.9, 1.6)),
    ("kappa", _G2, "thenar-to-forearm threshold spread ratio, in degrees at the median", "1.2",
     "1.04 to 1.37; stress 1.50", "Eckert, Taylor, Hagander [read]; pool 1.203 [model]", (1.04, 1.37), (1.50,)),
    ("k_slope", _G2, "slope ratio; thenar width is forearm width divided by k at the median", "0.92",
     "0.56 to 1.27", "Taylor Table 3 [read]; sampling interval [model]", (0.56, 1.27), ()),
    ("rho", _G2, "forearm-thenar log-threshold correlation (latent Pearson)", "0.75", "0.3 to 0.9",
     "Lautenbacher and Rollman 1993 proxy [read]", (0.3, 0.9), ()),
    ("rho_W", _G2, "forearm-thenar log-width correlation", "0.63",
     "0.3 to 1.0; reference points 0.75 and 1.0 reported on the grid",
     "Schaffner 2008 with Amir's ICCs [read], [model]", (0.3, 1.0), ()),
    ("S", _G3, "mean revisit step, forearm (rating units)", "-0.2134", "-0.4283 to +0.0259",
     "Dildine matched set [refit]", (-0.4283, 0.0259), ()),
    ("sigma_S", _G3, "between-person step SD, absolute, both regions", "0.6705", "0.4095 to 0.8660", "[refit]",
     (0.4095, 0.8660), ()),
    ("m_step", _G3, "multiplier on the step at visit 3 and later", "1.43", "not swept (section 11.2)",
     "Dildine profile [refit]; inside Jepma's bound and Figure 4 [read], [model]", None, ()),
    ("gamma", _G3, "drift, per C of T - 45, per drift unit (0, 1, 2)", "+0.0404",
     "-0.0188 to +0.1015; stress +0.0772 (Jepma)", "[refit], [read]", (-0.0188, 0.1015), (0.0772,)),
    ("beta_1", _G3, "lag-1 same-spot carry-over, per C of T_1 - 44.84", "-0.0426", "-0.0967 to +0.0205",
     "[refit]; Jepma -0.0679 inside", (-0.0967, 0.0205), ()),
    ("beta_2", _G3, "lag-2 same-spot carry-over, per C of T_2 - 44.84", "0", "-0.0595 to +0.0920 (fitted +0.0134)",
     "[refit]", (-0.0595, 0.0920), ()),
    ("c", _G3, "previous stimulus, per C of T_prev - 45", "+0.0880",
     "+0.0571 to +0.1284; co-primary +0.035 outside the sweep", "[refit]; Jepma [read]", (0.0571, 0.1284), (0.035,)),
    ("a", _G3, "proportional onset term, events 1 to 3 (factor 1 + a = 0.7626)", "-0.2374", "-0.2923 to -0.1810",
     "[refit]", (-0.2923, -0.1810), ()),
    ("a_th", _G3, "thenar onset term; when unset it equals a", "unset", "0 under S3",
     "LaMotte and Campbell [read]", None, (0.0,)),
    ("S_th", _G3, "thenar mean step under P3, P4, S2", "-1.4628", "-1.909 to -1.142",
     "LaMotte and Campbell, converted [read], [model]", (-1.909, -1.142), ()),
    ("sigma_S_th", _G3, "thenar step SD under P3, P4, S2; when unset it equals sigma_S", "unset",
     "proportional sensitivity 4.5969", "register item 43 [model]", None, (4.5969,)),
    ("nu", _G4, "Student t innovation degrees of freedom", "5.8603", "2.673 to 9.047", "calibrated [refit]",
     (2.673, 9.047), ()),
    ("s0", _G4, "asymptotic spread away from the peak", "0.3031", "0.112 to 0.494", "[refit]", (0.112, 0.494), ()),
    ("s1n", _G4, "peak spread increment (distinct from the population's s1)", "1.3927", "0.997 to 1.788", "[refit]",
     (0.997, 1.788), ()),
    ("w", _G4, "width of the spread bump (rating units)", "1.6975", "1.390 to 2.005", "[refit]", (1.390, 2.005), ()),
    ("peak", _G4, "rating at which the spread peaks", "4.4402", "4.192 to 4.688", "[refit]", (4.192, 4.688), ()),
    ("phi", _G4, "lag-1 autocorrelation of z", "0.1926", "0.092 to 0.293", "[refit]", (0.092, 0.293), ()),
]
OPTIONAL_KEYS = ("a_th", "sigma_S_th")  # spec section 5
M_STEP_NOTE = ("Not swept (spec 11.2): every other coefficient is estimated conditional on 1.43, so changing "
               "m_step alone runs a parameter vector no data support.")
assert [m[0] for m in PARAM_META] == list(DEFAULT_PARAMS), "PARAM_META must follow DEFAULT_PARAMS"

SCENARIO_DESC = {   # spec section 12
    "P1": "thenar same-spot dynamics equal to forearm; tau thenar->forearm 1, forearm->thenar 1; thenar onset a",
    "P2": "thenar same-spot dynamics equal to forearm; tau 0 both directions; thenar onset a",
    "P3": "thenar same-spot dynamics LaMotte-scaled (S_th); tau 1 both directions; thenar onset a",
    "P4": "thenar same-spot dynamics LaMotte-scaled (S_th); tau 0 both directions; thenar onset a",
    "S1": "stress: thenar dynamics equal to forearm; tau thenar->forearm 1, forearm->thenar 0; thenar onset a",
    "S2": "stress: thenar dynamics LaMotte-scaled (S_th); tau thenar->forearm 1, forearm->thenar 0; thenar onset a",
    "S3": "stress: thenar dynamics equal to forearm; tau 1 both directions; thenar onset 0",
}

# spec section 12; co-primary c from jepma2014
C_COPRIMARY = 0.035
REPORTING_GRID = (
    [(p, D, DEFAULT_PARAMS["c"]) for p in ("P1", "P2", "P3", "P4") for D in (0.5, 0.9)]
    + [(p, D, C_COPRIMARY) for p in ("P1", "P3") for D in (0.5, 0.9)]
    + [("P3", 0.0, DEFAULT_PARAMS["c"]), ("P4", 0.0, DEFAULT_PARAMS["c"]), ("P3", 0.0, C_COPRIMARY)]
)
assert len(REPORTING_GRID) == 15

FIXED_CONSTANTS = [  # spec section 5
    ("Curve zero point", "32 C", "[refit]: a free zero point is not identified"),
    ("Carry-over reference", "44.84 C", "Dildine mean previous same-spot temperature, 44.839 C [refit]"),
    ("Drift and previous-stimulus reference", "45 C", "[design]"),
    ("Onset window", "events 1 to 3", "the window a was fitted at [refit]"),
    ("Visit cap on step and drift codings", "visit 3", "Dildine and Jepma measured 3 visits [read]"),
    ("Stimulus", "8 s: 1.5 s rise from 32 C, 5 s at target, 1.5 s fall; enforced (contract 6)", "Amir supplement [read]"),
    ("Timing flag", "onsets 26 to 30 s; revisits 156 to 180 s", "[design]"),
    ("Reporting window (in_window flag)", "40 to 49 C", "[design]"),
    ("Extrapolation flag", "below 34 C or above 50 C", "Dildine span [refit]"),
    ("Person-stream uniforms", "6", "contract 1"),
]

# make_golden.py test sequence (spec section 1)
INTENDED_ORDER = [("forearm", 1), ("thenar", 1), ("forearm", 2), ("thenar", 2), ("forearm", 3), ("thenar", 3)]
_TEST_TEMPS = [41.0, 44.0, 47.0, 45.5, 43.0, 48.0, 46.0, 42.5, 49.0, 44.84, 45.0, 40.0, 47.5, 46.5, 43.5, 48.5,
               45.0, 44.0]
TEST_SEQUENCE = [ev(28.0 * i, *INTENDED_ORDER[i % 6], _TEST_TEMPS[i]) for i in range(18)]


# #####################################################################################################
# PART 3. BATCH RUNNER AND EXPORTERS (no GUI)
# #####################################################################################################
def default_output_options():
    return dict(directory="", prefix="heat_pain", scale="0-10", include_diagnostics=True,
                events_csv=True, persons_csv=True, summary_csv=True, rating_temperature_csv=True,
                plot=False, plot_format="png", plot_rating="both", plot_curves=True, plot_max_curves=20,
                plot_dpi=150)


def default_config():
    return dict(schema=CONFIG_SCHEMA, spec_version=SPEC_VERSION, seed=1, n_subjects=10, scenario="P1",
                grid_mode=False, params={}, events=[dict(e) for e in TEST_SEQUENCE],
                output=default_output_options())


def subject_seeds(base_seed, n):
    
    if isinstance(base_seed, bool) or int(base_seed) != base_seed or base_seed < 0:
        raise ValueError("the seed must be a non-negative integer")
    base_seed = int(base_seed)
    seeds = [int(np.random.SeedSequence(entropy=base_seed, spawn_key=(i,)).generate_state(1, np.uint64)[0]) >> 15
             for i in range(int(n))]
    if len(set(seeds)) != len(seeds):
        raise ValueError("two subjects received the same derived seed; choose another base seed")
    return seeds


def effective_params(overrides):
    """Contract 7."""
    p = dict(DEFAULT_PARAMS)
    for k, v in (overrides or {}).items():
        if k not in p: raise KeyError(f"unrecognised parameter {k}")
        p[k] = v
    return p


def _near(x, pts, tol=1e-9): return any(abs(x - q) <= tol for q in pts)


def check_params(overrides, scenario="P1"):
    errors, notes = [], []
    try:
        p = effective_params(overrides)
    except KeyError as e:
        return [str(e).strip("'\"")], notes
    for k, v in p.items():
        if v is None:
            if k not in OPTIONAL_KEYS: errors.append(f"{k}: a value is required")
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            errors.append(f"{k}: must be a finite number (got {v!r})")
    if errors: return errors, notes
    for k in ("s1", "s2", "kappa", "k_slope", "nu"):
        if p[k] <= 0: errors.append(f"{k}: must be greater than 0 (got {p[k]!r})")
    if p["w"] == 0: errors.append("w: must not be 0 (the spread divides by w squared)")
    for k in ("r", "rho", "rho_W", "phi"):
        if abs(p[k]) > 1: errors.append(f"{k}: a correlation must lie in [-1, 1] (got {p[k]!r})")
    if scenario not in SCEN: errors.append(f"unknown scenario {scenario}")
    if not errors:
        try:
            with np.errstate(all="ignore"):
                g = Generator(0, params={k: v for k, v in (overrides or {}).items()}, scenario=scenario)
            vals = [g.thr["forearm"], g.thr["thenar"], g.W["forearm"], g.W["thenar"], g.b["forearm"], g.b["thenar"]]
            if not all(np.isfinite(vals)):
                errors.append("the person draw is not finite: check Delta (exp(median) + Delta must be > 0), "
                              "kappa and k_slope")
        except np.linalg.LinAlgError:
            errors.append("the covariance of (forearm log threshold, log width, thenar log threshold) is not "
                          "positive definite: check r and rho (|r| = 1 or |rho| = 1 makes it singular)")
        except Exception as e:
            errors.append(f"the generator could not be built with these parameters: {e}")
    for key, _g, _m, _pd, sweep, _src, rng, pts in PARAM_META:
        v = p[key]; d = DEFAULT_PARAMS[key]
        if v == d or v is None: continue
        if key == "m_step":
            notes.append(f"m_step = {v!r}. {M_STEP_NOTE}"); continue
        inside = (rng is not None and rng[0] - 1e-12 <= v <= rng[1] + 1e-12) or _near(v, pts)
        if not inside:
            notes.append(f"{key} = {v!r} lies outside the spec's sweep ({sweep}); treat results as a labelled "
                         f"sensitivity outside the evidence")
    return errors, notes


_EVENT_KEYS = ("t_s", "region", "spot", "temp_c")


def check_events(events):
    """Spec section 3."""
    errs = []
    if not events: return ["the event list is empty"]
    prev_t = None
    for i, e in enumerate(events, 1):
        miss = [k for k in _EVENT_KEYS if k not in e]
        if miss: errs.append(f"event {i}: missing {', '.join(miss)}"); continue
        if e["region"] not in ("forearm", "thenar"): errs.append(f"event {i}: region must be forearm or thenar")
        sp = e["spot"]
        if isinstance(sp, bool) or not isinstance(sp, (int, float)) or sp not in (1, 2, 3):
            errs.append(f"event {i}: spot must be 1, 2 or 3")
        for k in ("t_s", "temp_c"):
            v = e[k]
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                errs.append(f"event {i}: {k} must be a finite number")
        if isinstance(e["t_s"], (int, float)) and math.isfinite(e["t_s"]):
            if prev_t is not None and e["t_s"] < prev_t:
                errs.append(f"event {i}: onset times must be non-decreasing (spec section 3)")
            prev_t = e["t_s"]
    return errs


def event_visits(events):
    n = {}; out = []
    for e in events:
        k = (e["region"], int(e["spot"])); n[k] = n.get(k, 0) + 1; out.append(n[k])
    return out


def build_runs(config):
    """Spec section 12."""
    ov = dict(config.get("params") or {})
    if not config.get("grid_mode"):
        p = effective_params(ov)
        return [dict(run="single", cell="", scenario=config["scenario"], params=ov, Delta=p["Delta"], c=p["c"])]
    runs = []
    for i, (pre, D, c) in enumerate(REPORTING_GRID, 1):
        runs.append(dict(run=f"cell{i:02d}", cell=i, scenario=pre, params={**ov, "Delta": D, "c": c}, Delta=D, c=c))
    return runs


class Cancelled(Exception):
    pass


def validate_config(config):
    errors, notes = [], []
    try:
        subject_seeds(config["seed"], 0)
    except (ValueError, TypeError):
        errors.append("seed: must be a non-negative integer")
    n = config.get("n_subjects")
    if isinstance(n, bool) or not isinstance(n, int) or n < 1: errors.append("number of subjects: must be an integer >= 1")
    if not config.get("grid_mode") and config.get("scenario") not in SCEN:
        errors.append(f"unknown scenario {config.get('scenario')}")
    for r in build_runs(config) if not errors else []:
        e, nt = check_params(r["params"], r["scenario"])
        errors += [f"{r['run']}: {x}" if config.get("grid_mode") else x for x in e]
        if not config.get("grid_mode") or r["cell"] == 1: notes += nt
    if config.get("grid_mode"):
        ov = config.get("params") or {}
        for k in ("Delta", "c"):
            if k in ov:
                notes.append(f"grid mode: your {k} = {ov[k]!r} is replaced in every cell by the cell's value "
                             f"(spec section 12); other parameter overrides apply to all cells")
        notes = [x for x in notes if not x.startswith(("Delta =", "c ="))]
    errors += check_events(config.get("events"))
    o = config.get("output") or {}
    if o.get("scale") not in ("0-10", "0-100"): errors.append("output scale must be 0-10 or 0-100")
    return errors, notes


def run_batch(config, progress=None, cancel=None):
    errors, notes = validate_config(config)
    if errors: raise ValueError("\n".join(errors))
    t0 = time.time()
    events = [dict(e) for e in config["events"]]
    seeds = subject_seeds(config["seed"], config["n_subjects"])
    runs = build_runs(config)
    visits = event_visits(events)
    total = len(seeds) * len(runs); done = 0
    data = []
    for r in runs:
        rec = dict(run=r, persons=[], outputs=[])
        for s in seeds:
            if cancel is not None and cancel.is_set(): raise Cancelled()
            g = Generator(s, params=r["params"], scenario=r["scenario"])
            out = g.simulate(events)
            pp = g.person()
            pers = dict(step_variate=pp["step_variate"])
            for reg in ("forearm", "thenar"):
                q = pp[reg]
                pers[reg] = {k: v for k, v in q.items() if k != "T_for_rating"}
                pers[reg]["T_at_rating_5_c"] = q["T_for_rating"](5.0)
            rec["persons"].append(pers); rec["outputs"].append(out)
            done += 1
            if progress is not None: progress(done, total)
        data.append(rec)
    return dict(config=config, notes=notes, seeds=seeds, runs=runs, events=events, visits=visits, data=data,
                elapsed_s=time.time() - t0)


# ---------------------------------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------------------------------
def _scale(config): return 10.0 if (config.get("output") or {}).get("scale") == "0-100" else 1.0


def events_table(res):
    cfg = res["config"]; f = _scale(cfg); diag = (cfg.get("output") or {}).get("include_diagnostics", True)
    rows = []
    for rec in res["data"]:
        r = rec["run"]
        for si, (seed, out) in enumerate(zip(res["seeds"], rec["outputs"]), 1):
            for ei, (e, v, o) in enumerate(zip(res["events"], res["visits"], out), 1):
                row = dict(subject=si, subject_seed=seed, run=r["run"], cell=r["cell"], scenario=r["scenario"],
                           Delta=r["Delta"], c=r["c"], event=ei, t_s=e["t_s"], region=e["region"],
                           spot=int(e["spot"]), temp_c=e["temp_c"], visit=v,
                           latent=o["latent"] * f, observed=o["observed"] * f)
                if diag: row.update(raw=o["raw"] * f, z=o["z"])
                row.update(in_window=o["in_window"], extrapolated=o["extrapolated"],
                           beyond_measured_visits=o["beyond_measured_visits"],
                           off_protocol_timing=o["off_protocol_timing"])
                rows.append(row)
    return rows


def persons_table(res):
    rows = []
    for rec in res["data"]:
        r = rec["run"]
        for si, (seed, pers) in enumerate(zip(res["seeds"], rec["persons"]), 1):
            for reg in ("forearm", "thenar"):
                q = pers[reg]
                rows.append(dict(subject=si, subject_seed=seed, run=r["run"], cell=r["cell"], scenario=r["scenario"],
                                 Delta=r["Delta"], c=r["c"], region=reg, threshold_c=q["threshold_c"],
                                 tolerance_c=q["tolerance_c"], width_c=q["width_c"], exponent=q["exponent"],
                                 zero_point_c=q["zero_point_c"], T_at_rating_5_c=q["T_at_rating_5_c"],
                                 step_mean=q["step_mean"], step_sd=q["step_sd"], step_person=q["step_person"],
                                 step_variate=pers["step_variate"]))
    return rows


def _stats(x):
    x = np.asarray(x, float); n = len(x)
    return dict(mean=float(x.mean()), sd=(float(x.std(ddof=1)) if n > 1 else None), median=float(np.median(x)),
                p05=float(np.percentile(x, 5)), p95=float(np.percentile(x, 95)))


_FLAGS = ("in_window", "extrapolated", "beyond_measured_visits", "off_protocol_timing")


def _grouped(rows, keyf):
    groups = {}
    for row in rows: groups.setdefault(keyf(row), []).append(row)
    return groups


def summary_table(ev_rows):
    out = []
    g = _grouped(ev_rows, lambda r: (r["run"], r["region"], min(r["visit"], 4)))
    for (run, reg, v), rr in g.items():
        a = rr[0]
        row = dict(run=run, cell=a["cell"], scenario=a["scenario"], Delta=a["Delta"], c=a["c"], region=reg,
                   visit=("4+" if v == 4 else v), n_events=len(rr), n_subjects=len({x["subject"] for x in rr}))
        for k in ("latent", "observed"):
            for s, val in _stats([x[k] for x in rr]).items(): row[f"{k}_{s}"] = val
        for fl in _FLAGS: row[f"share_{fl}"] = sum(bool(x[fl]) for x in rr) / len(rr)
        out.append(row)
    return out


def rating_temperature_table(ev_rows):
    out = []
    g = _grouped(ev_rows, lambda r: (r["run"], r["region"], r["temp_c"]))
    for (run, reg, T), rr in sorted(g.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
        a = rr[0]
        row = dict(run=run, cell=a["cell"], scenario=a["scenario"], Delta=a["Delta"], c=a["c"], region=reg,
                   temp_c=T, n_events=len(rr), visits=" ".join(str(v) for v in sorted({x["visit"] for x in rr})))
        for k in ("latent", "observed"):
            for s, val in _stats([x[k] for x in rr]).items(): row[f"{k}_{s}"] = val
        out.append(row)
    return out


def _fmt(v):
    if v is None: return ""
    if isinstance(v, (bool, np.bool_)): return "true" if v else "false"
    if isinstance(v, (float, np.floating)): return repr(float(v))
    return str(v)


def write_csv(path, rows):
    if not rows: return
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); keys = list(rows[0].keys()); w.writerow(keys)
        for r in rows: w.writerow([_fmt(r.get(k)) for k in keys])


# ---------------------------------------------------------------------------------------------------
# Plot (optional; matplotlib)
# ---------------------------------------------------------------------------------------------------
def have_matplotlib():
    try:
        import matplotlib  # noqa: F401
        return True
    except ImportError:
        return False


_COL = dict(observed="#2a78d6", latent="#eb6834", curve="#8a8985", text="#0b0b0b", text2="#52514e",
            grid="#e4e3df", window="#f3f2ee", anchor="#b5b4ad", surface="#fcfcfb")


def plot_rating_vs_temperature(res, rec, ev_rows, path, opts):
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    f = _scale(res["config"]); r = rec["run"]
    which = {"both": ("observed", "latent"), "observed": ("observed",), "latent": ("latent",)}[opts.get("plot_rating", "both")]
    rows = [x for x in ev_rows if x["run"] == r["run"]]
    temps = [x["temp_c"] for x in rows]
    xmin = min(min(temps) - 1.0, 38.0); xmax = max(max(temps) + 1.0, 50.0)
    fig = Figure(figsize=(11.0, 5.2), facecolor=_COL["surface"])
    FigureCanvasAgg(fig)
    axes = fig.subplots(1, 2, sharey=True)
    n_sub = len(res["seeds"]); ymax = 10.0 * f
    off = {"observed": -0.12, "latent": 0.12} if len(which) == 2 else {which[0]: 0.0}
    for ax, reg in zip(axes, ("forearm", "thenar")):
        ax.set_facecolor(_COL["surface"])
        ax.axvspan(WINDOW[0], WINDOW[1], color=_COL["window"], zorder=0, lw=0)
        for val, lab in ((2, "threshold"), (5, "moderate"), (8, "tolerance")):
            ax.axhline(val * f, color=_COL["anchor"], lw=0.8, ls=(0, (4, 3)), zorder=1)
            ax.text(xmin + 0.12, val * f + 0.12 * f, f"{lab} ({val * f:g})", ha="left", va="bottom", fontsize=8,
                    color=_COL["text2"], zorder=5, bbox=dict(boxstyle="square,pad=0.1", fc=_COL["surface"], ec="none", alpha=0.8))
        if opts.get("plot_curves", True):
            K = min(int(opts.get("plot_max_curves", 20)), n_sub)
            TT = np.linspace(ZERO_C, xmax, 300)
            for k in range(K):
                q = rec["persons"][k][reg]
                R = np.where(TT > ZERO_C, 2.0 * (np.clip(TT - ZERO_C, 0, None) / (q["threshold_c"] - ZERO_C)) ** q["exponent"], 0.0)
                ax.plot(TT, np.clip(R, 0, 10) * f, color=_COL["curve"], lw=0.8, alpha=0.35, zorder=2,
                        label=(f"fresh-skin curve R(T), first {K} subject{'s' if K != 1 else ''}" if k == 0 else None))
        rr = [x for x in rows if x["region"] == reg]
        npts = max(len(rr), 1); alpha = float(min(0.85, max(0.06, 25.0 / math.sqrt(npts))))
        for kind in which:
            xs = np.array([x["temp_c"] for x in rr]) + off[kind]; ys = np.array([x[kind] for x in rr])
            ax.scatter(xs, ys, s=14, color=_COL[kind], alpha=alpha, lw=0, zorder=3, label=f"{kind}, each event")
            byT = _grouped(rr, lambda x: x["temp_c"]); Ts = sorted(byT)
            med = [float(np.median([x[kind] for x in byT[T]])) for T in Ts]
            ax.plot(np.array(Ts) + off[kind], med, ls="none", color=_COL[kind], marker="D", ms=7,
                    mec=_COL["text"], mew=1.0, zorder=4, label=f"{kind}, median at each temperature")
        ax.set_xlim(xmin, xmax); ax.set_ylim(-0.3 * f, ymax + 0.3 * f)
        ax.set_title(reg.capitalize(), fontsize=11, color=_COL["text"], loc="left")
        ax.set_xlabel("Delivered temperature (C)", color=_COL["text2"])
        ax.grid(True, color=_COL["grid"], lw=0.6, zorder=0); ax.set_axisbelow(True)
        for s in ("top", "right"): ax.spines[s].set_visible(False)
        for s in ("left", "bottom"): ax.spines[s].set_color(_COL["anchor"])
        ax.tick_params(colors=_COL["text2"], labelsize=9)
    axes[0].set_ylabel(f"Rating (0 to {int(ymax)})", color=_COL["text2"])
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=min(len(l), 3), frameon=False, fontsize=9)
    sub = (f"{n_sub} subject{'s' if n_sub != 1 else ''}, scenario {r['scenario']}, Delta {r['Delta']:+g} C, "
           f"c {r['c']:+.4f}" + (f", grid cell {r['cell']}" if r["cell"] != "" else "") +
           f", base seed {res['config']['seed']}. Latent is the scoring target; observed is what a procedure sees.\n"
           f"Shaded: 40 to 49 C reporting window. Medians pool all visits at a temperature."
           + (" Observed and latent are drawn 0.12 C left and right of the delivered temperature."
              if len(which) == 2 else ""))
    fig.suptitle("Rating against delivered temperature", x=0.01, ha="left", fontsize=13, color=_COL["text"])
    fig.text(0.01, 0.935, sub, ha="left", va="top", fontsize=9, color=_COL["text2"], linespacing=1.4)
    fig.subplots_adjust(left=0.06, right=0.99, top=0.78, bottom=0.24, wspace=0.06)
    fig.savefig(path, dpi=int(opts.get("plot_dpi", 150)), facecolor=_COL["surface"])


# ---------------------------------------------------------------------------------------------------
# Writing a run
# ---------------------------------------------------------------------------------------------------
def planned_files(config):
    o = config["output"]; d = o.get("directory") or os.getcwd(); p = o.get("prefix") or "heat_pain"
    files = [os.path.join(d, f"{p}_manifest.json")]
    if o.get("events_csv"): files.append(os.path.join(d, f"{p}_events.csv"))
    if o.get("persons_csv"): files.append(os.path.join(d, f"{p}_persons.csv"))
    if o.get("summary_csv"): files.append(os.path.join(d, f"{p}_summary.csv"))
    if o.get("rating_temperature_csv"): files.append(os.path.join(d, f"{p}_rating_vs_temperature.csv"))
    if o.get("plot"):
        for r in build_runs(config):
            files.append(os.path.join(d, f"{p}_rating_vs_temperature_{r['run']}.{o.get('plot_format', 'png')}"))
    return files


def library_versions():
    v = dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
             platform=platform.platform())
    try:
        import matplotlib; v["matplotlib"] = matplotlib.__version__
    except ImportError:
        v["matplotlib"] = None
    return v


def manifest(res, files):
    cfg = res["config"]
    return dict(
        tool=TOOL_NAME, tool_version=TOOL_VERSION, spec_version=SPEC_VERSION, generator_version=__version__,
        created_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"), versions=library_versions(),
        config=cfg,
        effective_params={r["run"]: effective_params(r["params"]) for r in res["runs"]},
        runs=[dict(run=r["run"], cell=r["cell"], scenario=r["scenario"], Delta=r["Delta"], c=r["c"]) for r in res["runs"]],
        seed_derivation=("subject i (0-based): int(numpy.random.SeedSequence(entropy=base_seed, spawn_key=(i,))"
                         ".generate_state(1, numpy.uint64)[0]) >> 15; person stream default_rng([seed, 0]).random(6); "
                         "noise stream default_rng([seed, 1]), one uniform per event"),
        subject_seeds=res["seeds"], notes=res["notes"], files=[os.path.basename(f) for f in files],
        rules=["latent is the scoring target; observed is what a procedure may see (contract 5)",
               "report on the 15-cell grid; a conclusion that changes across cells is unresolved, not averaged",
               "inputs are evaluated and flagged, never clamped; extrapolated and beyond_measured_visits outputs "
               "are outside the evidence",
               "one person, one session; reset() is a counterfactual replay, not a second visit"])


def write_outputs(res, log=print):
    cfg = res["config"]; o = cfg["output"]
    d = o.get("directory") or os.getcwd(); os.makedirs(d, exist_ok=True)
    written = []
    ev_rows = events_table(res)
    p = o.get("prefix") or "heat_pain"; P = lambda name: os.path.join(d, f"{p}_{name}")
    if o.get("events_csv"): write_csv(P("events.csv"), ev_rows); written.append(P("events.csv"))
    if o.get("persons_csv"): write_csv(P("persons.csv"), persons_table(res)); written.append(P("persons.csv"))
    if o.get("summary_csv"): write_csv(P("summary.csv"), summary_table(ev_rows)); written.append(P("summary.csv"))
    if o.get("rating_temperature_csv"):
        write_csv(P("rating_vs_temperature.csv"), rating_temperature_table(ev_rows))
        written.append(P("rating_vs_temperature.csv"))
    if o.get("plot"):
        if not have_matplotlib():
            log("Plot skipped: matplotlib is not installed (pip install matplotlib).")
        else:
            for rec in res["data"]:
                fp = P(f"rating_vs_temperature_{rec['run']['run']}.{o.get('plot_format', 'png')}")
                plot_rating_vs_temperature(res, rec, ev_rows, fp, o); written.append(fp)
    mf = P("manifest.json")
    with open(mf, "w", encoding="utf-8") as fh: json.dump(manifest(res, [mf] + written), fh, indent=1)
    return [mf] + written, ev_rows


def run_summary_lines(res, ev_rows):
    n = len(res["seeds"]); L = []
    L.append(f"{n} subject{'s' if n != 1 else ''} x {len(res['runs'])} run{'s' if len(res['runs']) != 1 else ''} x "
             f"{len(res['events'])} events = {len(ev_rows)} rows in {res['elapsed_s']:.1f} s")
    for fl in _FLAGS:
        k = sum(bool(x[fl]) for x in ev_rows)
        L.append(f"  {fl}: {k} of {len(ev_rows)} events")
    f = _scale(res["config"])
    for reg in ("forearm", "thenar"):
        lat = [x["latent"] for x in ev_rows if x["region"] == reg]
        if lat:
            L.append(f"  {reg}: latent median {np.median(lat):.3f}, share at 0 {np.mean(np.array(lat) == 0):.3f}, "
                     f"share at {10 * f:g} {np.mean(np.array(lat) == 10 * f):.3f}")
    return L


# ---------------------------------------------------------------------------------------------------
# Configuration files
# ---------------------------------------------------------------------------------------------------
def save_config(config, path):
    with open(path, "w", encoding="utf-8") as fh: json.dump(config, fh, indent=1)


def load_config(path):
    """Contract 7."""
    with open(path, encoding="utf-8") as fh: d = json.load(fh)
    if "config" in d and "tool" in d: d = d["config"]
    cfg = default_config()
    for k in ("seed", "n_subjects", "scenario", "grid_mode", "params", "events"):
        if k in d: cfg[k] = d[k]
    cfg["output"].update(d.get("output") or {})
    unknown = [k for k in (cfg["params"] or {}) if k not in DEFAULT_PARAMS]
    if unknown: raise KeyError(f"unrecognised parameter key(s): {', '.join(unknown)}")
    if cfg["scenario"] not in SCEN: raise ValueError(f"unknown scenario {cfg['scenario']}")
    for e in cfg["events"]:
        if isinstance(e.get("spot"), float) and float(e["spot"]).is_integer(): e["spot"] = int(e["spot"])
    return cfg


def read_events_csv(path):
    out = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rd = csv.DictReader(fh)
        miss = [k for k in _EVENT_KEYS if k not in (rd.fieldnames or [])]
        if miss: raise ValueError(f"missing column(s): {', '.join(miss)}")
        for i, row in enumerate(rd, 2):
            try:
                sp = float(row["spot"])
                out.append(dict(t_s=float(row["t_s"]), region=row["region"].strip().lower(),
                                spot=int(sp) if sp.is_integer() else sp, temp_c=float(row["temp_c"])))
            except (TypeError, ValueError):
                raise ValueError(f"line {i}: could not read the row {row}")
    return out


def write_events_csv(path, events):
    write_csv(path, [{k: e[k] for k in _EVENT_KEYS} for e in events])


_SPOT_RE = re.compile(r"^\s*(f|fa|forearm|t|th|thenar)\s*[-_ ]?\s*([123])\s*$", re.I)


def parse_spot_order(text):
    out = []
    for tok in [t for t in re.split(r"[,;]", text) if t.strip()]:
        m = _SPOT_RE.match(tok)
        if not m: raise ValueError(f"could not read spot '{tok.strip()}' (use e.g. F1, T2, forearm 3)")
        out.append(("forearm" if m.group(1).lower().startswith("f") else "thenar", int(m.group(2))))
    if not out: raise ValueError("the spot order is empty")
    return out


def build_template(n_events, start_s, interval_s, order_text, temps_text):
    n = int(n_events)
    if n < 1: raise ValueError("number of events must be >= 1")
    order = parse_spot_order(order_text)
    temps = [float(t) for t in re.split(r"[,;\s]+", temps_text.strip()) if t]
    if len(temps) == 1: temps = temps * n
    if len(temps) != n: raise ValueError(f"give one temperature or exactly {n} temperatures (got {len(temps)})")
    return [ev(float(start_s) + i * float(interval_s), *order[i % len(order)], temps[i]) for i in range(n)]


def replay_golden(path):
    """Implementation guide rung 2."""
    with open(path, encoding="utf-8") as fh: G = json.load(fh)
    mx = 0.0; flags = True
    for c in G["cases"]:
        evs = G["protocol"] if c["events"] == "protocol" else G["edge"]
        out = Generator(c["seed"], params=c["params"], scenario=c["scenario"]).simulate(evs)
        for a, w in zip(out, c["outputs"]):
            for k, v in a.items():
                if isinstance(v, bool): flags &= (v == w[k])
                else: mx = max(mx, abs(v - w[k]))
    return len(G["cases"]), mx, flags


# ---------------------------------------------------------------------------------------------------
# Reference tab text
# ---------------------------------------------------------------------------------------------------
_REF_CONSTANTS = [
    ("Curve zero point", "32 C", None),
    ("Carry-over reference", "44.84 C (mean previous same-spot temperature)", "Dildine and Atlas, unpublished dataset"),
    ("Drift and previous-stimulus reference", "45 C", None),
    ("Onset window", "events 1 to 3", None),
    ("Visit cap on step and drift codings", "visit 3 (the most visits measured)",
     "Dildine and Atlas, unpublished dataset; Jepma et al. 2014"),
    ("Stimulus", "8 s: 1.5 s rise from 32 C, 5 s at target, 1.5 s fall", "Amir et al. 2022, Supplementary Materials"),
    ("Timing flag", "onsets 26 to 30 s; revisits 156 to 180 s", None),
    ("Reporting window (in_window flag)", "40 to 49 C", None),
    ("Extrapolation flag", "below 34 C or above 50 C (the delivered temperature span)",
     "Dildine and Atlas, unpublished dataset"),
    ("Person-stream uniforms", "6", None),
]

_REF_RULES = [
    "Rules",
    "* expected is the scoring target; observed is what a procedure may see.",
    "* Report on the 15-cell grid. A conclusion that changes across cells is reported as unresolved by the",
    "  available evidence, not averaged.",
    "* Use common random numbers for sweeps: same seeds, parameters changed through params.",
    "* Inputs are evaluated and flagged, never clamped. Treat extrapolated and beyond_measured_visits outputs",
    "  as outside the evidence.",
    "* One person, one session. reset() is a counterfactual replay, not a second visit.",
    "",
    "Known limits",
    "* The thenar layer rests on proxies and scenarios: Delta, tau and the thenar dynamics are carried as",
    "  co-primary values or presets.",
    "* The threshold shape is set from independent data (Lotsch et al. 2026) that the Amir et al. 2022 anchors",
    "  only partly support; alpha_pop = 0 (log-normal) and the interval ends -6.17 and -1.98 are the sensitivities.",
    "* The fresh-skin upper tails are heavy: the threshold 99th percentile is above any deliverable stimulus,",
    "  and 1.2 percent of people could not produce a usable anchor.",
    "* The noise far tail is lighter in the data than in the t; the spread has unmodelled structure near the",
    "  middle of the scale.",
    "* c is applied at a longer gap than it was fitted at; +0.035 (Jepma et al. 2014) is co-primary.",
    "* The visit-3 multiplier does not depend on temperature here, though the Jepma et al. 2014 data say it",
    "  does; visits beyond the third are flagged.",
]


def reference_text():
    L = ["SCENARIO PRESETS", ""]
    L += [f"  {k}  {v}" for k, v in SCENARIO_DESC.items()]
    L += ["", "THE 15-CELL REPORTING GRID", "",
          "  cell  preset  Delta (C)  c"]
    L += [f"  {i:>4}  {p:<6}  {D:+.1f}       {c:+.4f}" for i, (p, D, c) in enumerate(REPORTING_GRID, 1)]
    L += ["", "  Every result is reported on the 15 cells. A conclusion that changes across cells is reported as "
              "unresolved by the available evidence, not averaged.", "",
          "FIXED CONSTANTS (not configurable)", ""]
    L += [f"  {q}: {v}" + (f"   [{s}]" if s else "") for q, v, s in _REF_CONSTANTS]
    L += ["", "OUTPUT FIELDS", "",
          "  expected    rating with no noise, clip(R_raw, 0, 10). THE SCORING TARGET.",
          "  observed    clip(R_raw + sigma(R_raw) z, 0, 10), the rating a procedure is allowed to see",
          "  raw, z      diagnostics: unclipped R_raw and the standardised noise value",
          "  in_window   40 <= temp_c <= 49",
          "  extrapolated   temp_c < 34 or temp_c > 50",
          "  beyond_measured_visits   fourth or later visit to a spot",
          "  off_protocol_timing      onset gap outside 26-30 s, or revisit outside 156-180 s",
          "", "RULES AND KNOWN LIMITS", ""]
    L += ["  " + ln if ln else "" for ln in _REF_RULES]
    L += ["", "SOURCES", ""]
    L += [f"  {v}" for v in SOURCES.values()]
    return "\n".join(L)


# #####################################################################################################
# PART 4. THE GUI (tkinter)
# #####################################################################################################
def _fmt_param(v):
    return "" if v is None else repr(float(v))


def launch_gui(run=True):
    import queue
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    class Tooltip:
        def __init__(self, widget, text):
            self.w, self.text, self.tip = widget, text, None
            widget.bind("<Enter>", self.show); widget.bind("<Leave>", self.hide)

        def show(self, _e=None):
            if self.tip or not self.text: return
            x = self.w.winfo_rootx() + 12; y = self.w.winfo_rooty() + self.w.winfo_height() + 4
            self.tip = tk.Toplevel(self.w); self.tip.wm_overrideredirect(True); self.tip.wm_geometry(f"+{x}+{y}")
            tk.Label(self.tip, text=self.text, justify="left", background="#ffffe8", relief="solid", borderwidth=1,
                     wraplength=420, padx=6, pady=4).pack()

        def hide(self, _e=None):
            if self.tip: self.tip.destroy(); self.tip = None

    class App:
        def __init__(self, root):
            self.root = root
            root.title(f"Heat-pain rating generator v{SPEC_VERSION} ({TOOL_NAME} {TOOL_VERSION})")
            root.geometry("1180x800"); root.minsize(980, 640)
            self.q = queue.Queue(); self.worker = None; self.cancel = threading.Event()
            self.events = []
            st = ttk.Style()
            try: st.theme_use("clam")
            except tk.TclError: pass
            st.configure("Changed.TLabel", foreground="#b3261e", font=("TkDefaultFont", 9, "bold"))
            st.configure("Key.TLabel", font=("TkDefaultFont", 9, "bold"))
            st.configure("Head.TLabel", font=("TkDefaultFont", 10, "bold"))
            st.configure("Muted.TLabel", foreground="#52514e")
            self._menu()
            nb = ttk.Notebook(root); nb.pack(fill="both", expand=True, padx=6, pady=6); self.nb = nb
            self.tab_run = ttk.Frame(nb); self.tab_par = ttk.Frame(nb); self.tab_ev = ttk.Frame(nb); self.tab_ref = ttk.Frame(nb)
            nb.add(self.tab_run, text="Run and output"); nb.add(self.tab_par, text="Parameters (spec section 5)")
            nb.add(self.tab_ev, text="Stimulus events"); nb.add(self.tab_ref, text="Reference")
            self._build_run(); self._build_params(); self._build_events(); self._build_reference()
            self.set_config(default_config())
            self.root.after(100, self._poll)
            self.log(f"{TOOL_NAME} {TOOL_VERSION}, generator spec v{SPEC_VERSION}. "
                     f"Python {platform.python_version()}, numpy {np.__version__}, scipy {scipy.__version__}"
                     + ("" if have_matplotlib() else "; matplotlib not installed (plot export disabled)"))

        # ------------------------------------------------------------------ menu
        def _menu(self):
            m = tk.Menu(self.root); fm = tk.Menu(m, tearoff=0)
            fm.add_command(label="Load configuration or manifest...", command=self.on_load)
            fm.add_command(label="Save configuration...", command=self.on_save)
            fm.add_separator(); fm.add_command(label="Reset everything to defaults", command=self.on_reset_all)
            fm.add_separator(); fm.add_command(label="Quit", command=self.root.destroy)
            m.add_cascade(label="File", menu=fm); self.root.config(menu=m)

        # ------------------------------------------------------------------ run tab
        def _build_run(self):
            f = self.tab_run; f.columnconfigure(0, weight=1); f.columnconfigure(1, weight=1)
            # subjects and seed
            a = ttk.LabelFrame(f, text="Subjects and seed"); a.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
            self.v_seed = tk.StringVar(); self.v_n = tk.StringVar()
            ttk.Label(a, text="Base seed").grid(row=0, column=0, sticky="w", padx=6, pady=3)
            ttk.Entry(a, textvariable=self.v_seed, width=14).grid(row=0, column=1, sticky="w", padx=6)
            ttk.Label(a, text="Number of subjects").grid(row=1, column=0, sticky="w", padx=6, pady=3)
            ttk.Entry(a, textvariable=self.v_n, width=14).grid(row=1, column=1, sticky="w", padx=6)
            ttk.Label(a, style="Muted.TLabel", wraplength=470, justify="left",
                      text="Subject i gets its own Generator seed from SeedSequence(base seed, spawn_key=(i,)). "
                           "It depends on the base seed and i only, so the first k subjects are the same whatever "
                           "the number of subjects. Every subject seed is written to the outputs.").grid(
                row=2, column=0, columnspan=2, sticky="w", padx=6, pady=(2, 6))
            # scenario
            b = ttk.LabelFrame(f, text="Scenario (spec section 12)"); b.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)
            self.v_scen = tk.StringVar(); self.v_grid = tk.BooleanVar()
            ttk.Label(b, text="Preset").grid(row=0, column=0, sticky="w", padx=6, pady=3)
            self.cb_scen = ttk.Combobox(b, textvariable=self.v_scen, values=list(SCEN), state="readonly", width=6)
            self.cb_scen.grid(row=0, column=1, sticky="w", padx=6)
            self.l_scen = ttk.Label(b, style="Muted.TLabel", wraplength=470, justify="left")
            self.l_scen.grid(row=1, column=0, columnspan=2, sticky="w", padx=6)
            self.v_scen.trace_add("write", lambda *_: self.l_scen.config(text=SCENARIO_DESC.get(self.v_scen.get(), "")))
            ttk.Checkbutton(b, text="Run the 15-cell reporting grid instead", variable=self.v_grid,
                            command=self._grid_toggled).grid(row=2, column=0, columnspan=2, sticky="w", padx=6, pady=(8, 2))
            ttk.Label(b, style="Muted.TLabel", wraplength=470, justify="left",
                      text="Grid mode runs every subject, with the same seeds, in all 15 cells: {P1-P4} x Delta {+0.5, +0.9} "
                           "at the default c; {P1, P3} x Delta {+0.5, +0.9} at c = +0.035; P3 and P4 at Delta 0 (default c) "
                           "and P3 at Delta 0 (c = +0.035). Each cell sets the scenario, Delta and c; your other "
                           "parameter overrides apply to every cell.").grid(row=3, column=0, columnspan=2, sticky="w", padx=6, pady=(0, 6))
            # output
            c = ttk.LabelFrame(f, text="Output"); c.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=6, pady=6)
            c.columnconfigure(1, weight=1)
            self.v_dir = tk.StringVar(); self.v_prefix = tk.StringVar(); self.v_scale = tk.StringVar()
            self.v_diag = tk.BooleanVar(); self.v_evcsv = tk.BooleanVar(); self.v_pcsv = tk.BooleanVar()
            self.v_scsv = tk.BooleanVar(); self.v_rtcsv = tk.BooleanVar(); self.v_plot = tk.BooleanVar()
            self.v_pfmt = tk.StringVar(); self.v_prat = tk.StringVar(); self.v_pcur = tk.BooleanVar()
            self.v_pmax = tk.StringVar(); self.v_pdpi = tk.StringVar()
            ttk.Label(c, text="Folder").grid(row=0, column=0, sticky="w", padx=6, pady=3)
            ttk.Entry(c, textvariable=self.v_dir).grid(row=0, column=1, sticky="ew", padx=6)
            ttk.Button(c, text="Browse...", command=self.on_browse).grid(row=0, column=2, padx=6)
            ttk.Label(c, text="File prefix").grid(row=1, column=0, sticky="w", padx=6, pady=3)
            ttk.Entry(c, textvariable=self.v_prefix, width=24).grid(row=1, column=1, sticky="w", padx=6)
            ttk.Label(c, text="Rating scale").grid(row=2, column=0, sticky="w", padx=6, pady=3)
            sf = ttk.Frame(c); sf.grid(row=2, column=1, sticky="w")
            ttk.Radiobutton(sf, text="0 to 10", value="0-10", variable=self.v_scale).pack(side="left", padx=6)
            ttk.Radiobutton(sf, text="0 to 100 (x10, spec section 2)", value="0-100", variable=self.v_scale).pack(side="left", padx=6)
            ttk.Label(c, text="Tables (CSV)", style="Head.TLabel").grid(row=3, column=0, columnspan=3, sticky="w", padx=6, pady=(8, 2))
            for i, (var, txt, tip) in enumerate([
                    (self.v_evcsv, "Events: one row per subject, run and event (latent, observed, flags)", None),
                    (self.v_diag, "   include the diagnostic columns raw (unclipped R_raw) and z", None),
                    (self.v_pcsv, "Persons: thresholds, tolerances, widths, exponents, T at rating 5, steps", None),
                    (self.v_scsv, "Summary: by run, region and visit (mean, SD, median, 5th/95th, flag shares)", None),
                    (self.v_rtcsv, "Rating vs temperature: by run, region and temperature", None)]):
                ttk.Checkbutton(c, text=txt, variable=var).grid(row=4 + i, column=0, columnspan=3, sticky="w", padx=6)
            ttk.Label(c, text="A manifest (JSON) with the full configuration, every subject seed and the library "
                             "versions is always written.", style="Muted.TLabel", wraplength=520,
                      justify="left").grid(row=9, column=0, columnspan=3, sticky="w", padx=6)
            ttk.Label(c, text="Plot", style="Head.TLabel").grid(row=10, column=0, columnspan=3, sticky="w", padx=6, pady=(8, 2))
            self.cb_plot = ttk.Checkbutton(c, text="Rating vs temperature plot (one figure per run; needs matplotlib)",
                                           variable=self.v_plot)
            self.cb_plot.grid(row=11, column=0, columnspan=3, sticky="w", padx=6)
            pf = ttk.Frame(c); pf.grid(row=12, column=0, columnspan=3, sticky="w", padx=20)
            ttk.Label(pf, text="Ratings").grid(row=0, column=0, sticky="w")
            ttk.Combobox(pf, textvariable=self.v_prat, values=["both", "observed", "latent"], state="readonly",
                         width=9).grid(row=0, column=1, padx=4)
            ttk.Label(pf, text="Format").grid(row=0, column=2, sticky="w", padx=(10, 0))
            ttk.Combobox(pf, textvariable=self.v_pfmt, values=["png", "pdf", "svg"], state="readonly",
                         width=5).grid(row=0, column=3, padx=4)
            ttk.Label(pf, text="DPI").grid(row=0, column=4, sticky="w", padx=(10, 0))
            ttk.Entry(pf, textvariable=self.v_pdpi, width=5).grid(row=0, column=5, padx=4)
            ttk.Checkbutton(pf, text="Fresh-skin curves for the first", variable=self.v_pcur).grid(row=1, column=0, columnspan=3, sticky="w", pady=2)
            ttk.Entry(pf, textvariable=self.v_pmax, width=5).grid(row=1, column=3, sticky="w")
            ttk.Label(pf, text="subjects").grid(row=1, column=4, columnspan=2, sticky="w")
            if not have_matplotlib():
                self.cb_plot.state(["disabled"])
                ttk.Label(c, text="matplotlib is not installed: pip install matplotlib to enable the plot.",
                          style="Changed.TLabel").grid(row=13, column=0, columnspan=3, sticky="w", padx=6)
            # actions
            d = ttk.Frame(f); d.grid(row=2, column=0, columnspan=2, sticky="ew", padx=6, pady=(4, 2))
            self.b_go = ttk.Button(d, text="Generate", command=self.on_generate); self.b_go.pack(side="left")
            self.b_cancel = ttk.Button(d, text="Cancel", command=self.cancel.set, state="disabled"); self.b_cancel.pack(side="left", padx=6)
            ttk.Button(d, text="Run self-tests (checks 8 to 10)", command=self.on_selftest).pack(side="left", padx=(18, 6))
            ttk.Button(d, text="Replay golden vectors...", command=self.on_golden).pack(side="left")
            self.pb = ttk.Progressbar(d, mode="determinate", length=220); self.pb.pack(side="right")
            self.l_status = ttk.Label(d, text=""); self.l_status.pack(side="right", padx=8)
            # log
            lf = ttk.LabelFrame(f, text="Log"); lf.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=6, pady=6)
            f.rowconfigure(3, weight=1); lf.rowconfigure(0, weight=1); lf.columnconfigure(0, weight=1)
            self.t_log = tk.Text(lf, height=10, wrap="word", state="disabled", font=("TkFixedFont", 9))
            self.t_log.grid(row=0, column=0, sticky="nsew")
            sb = ttk.Scrollbar(lf, command=self.t_log.yview); sb.grid(row=0, column=1, sticky="ns")
            self.t_log.config(yscrollcommand=sb.set)

        def _grid_toggled(self):
            self.cb_scen.config(state="disabled" if self.v_grid.get() else "readonly")

        def log(self, text):
            self.t_log.config(state="normal"); self.t_log.insert("end", text + "\n"); self.t_log.see("end")
            self.t_log.config(state="disabled")

        # ------------------------------------------------------------------ parameters tab
        def _build_params(self):
            top = ttk.Frame(self.tab_par); top.pack(fill="x", padx=6, pady=4)
            ttk.Button(top, text="Reset all parameters to defaults", command=self.reset_params).pack(side="left")
            self.l_changed = ttk.Label(top, text=""); self.l_changed.pack(side="left", padx=12)
            ttk.Label(self.tab_par, style="Muted.TLabel", wraplength=1100, justify="left",
                      text="Values are full precision. Overrides apply through params (contract 7). A value outside the "
                           "spec's sweep is allowed and noted in the log; a value the equations cannot evaluate is "
                           "refused at Generate. Changed keys are shown in red.").pack(fill="x", padx=8)
            outer = ttk.Frame(self.tab_par); outer.pack(fill="both", expand=True)
            cv = tk.Canvas(outer, highlightthickness=0); sb = ttk.Scrollbar(outer, orient="vertical", command=cv.yview)
            sbx = ttk.Scrollbar(outer, orient="horizontal", command=cv.xview)
            inner = ttk.Frame(cv); inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
            cv.create_window((0, 0), window=inner, anchor="nw"); cv.configure(yscrollcommand=sb.set, xscrollcommand=sbx.set)
            sbx.pack(side="bottom", fill="x"); sb.pack(side="right", fill="y"); cv.pack(side="left", fill="both", expand=True)

            def _wheel(e):
                if e.num == 4: cv.yview_scroll(-3, "units")
                elif e.num == 5: cv.yview_scroll(3, "units")
                else: cv.yview_scroll(int(-e.delta / (120 if abs(e.delta) >= 120 else 1)), "units")
            cv.bind("<Enter>", lambda e: (cv.bind_all("<MouseWheel>", _wheel), cv.bind_all("<Button-4>", _wheel),
                                          cv.bind_all("<Button-5>", _wheel)))
            cv.bind("<Leave>", lambda e: (cv.unbind_all("<MouseWheel>"), cv.unbind_all("<Button-4>"), cv.unbind_all("<Button-5>")))
            self.pvars, self.punset, self.plabels, self.pentries = {}, {}, {}, {}
            heads = ["Key", "Value", "", "Default", "Meaning", "Sweep (spec section 5)", "Source"]
            r = 0
            for grp in PARAM_GROUPS:
                ttk.Label(inner, text=grp, style="Head.TLabel").grid(row=r, column=0, columnspan=7, sticky="w", padx=6, pady=(10, 2)); r += 1
                for j, h in enumerate(heads):
                    ttk.Label(inner, text=h, style="Muted.TLabel").grid(row=r, column=j, sticky="w", padx=4)
                r += 1
                for key, g, meaning, pdef, sweep, src, _rng, _pts in PARAM_META:
                    if g != grp: continue
                    lab = ttk.Label(inner, text=key, style="Key.TLabel"); lab.grid(row=r, column=0, sticky="w", padx=6, pady=1)
                    self.plabels[key] = lab
                    var = tk.StringVar(); self.pvars[key] = var
                    ent = ttk.Entry(inner, textvariable=var, width=20); ent.grid(row=r, column=1, sticky="w", padx=4)
                    self.pentries[key] = ent
                    cell = ttk.Frame(inner); cell.grid(row=r, column=2, sticky="w")
                    if key in OPTIONAL_KEYS:
                        uv = tk.BooleanVar(value=True); self.punset[key] = uv
                        ttk.Checkbutton(cell, text="unset", variable=uv,
                                        command=lambda k=key: self._unset_toggled(k)).pack(side="left")
                    ttk.Button(cell, text="Default", width=7, command=lambda k=key: self.reset_param(k)).pack(side="left", padx=2)
                    ttk.Label(inner, text=pdef).grid(row=r, column=3, sticky="w", padx=4)
                    ml = ttk.Label(inner, text=meaning, wraplength=250, justify="left"); ml.grid(row=r, column=4, sticky="w", padx=4)
                    ttk.Label(inner, text=sweep, wraplength=200, justify="left").grid(row=r, column=5, sticky="w", padx=4)
                    ttk.Label(inner, text=src, wraplength=170, justify="left", style="Muted.TLabel").grid(row=r, column=6, sticky="w", padx=4)
                    if key == "m_step":
                        Tooltip(ml, M_STEP_NOTE); Tooltip(ent, M_STEP_NOTE); ml.config(text=meaning + " (not swept; hover)")
                    var.trace_add("write", lambda *_a, k=key: self._param_changed(k))
                    r += 1

        def _unset_toggled(self, k):
            if self.punset[k].get():
                self.pvars[k].set(""); self.pentries[k].state(["disabled"])
            else:
                self.pentries[k].state(["!disabled"])
                if not self.pvars[k].get().strip():
                    self.pvars[k].set(_fmt_param(0.0 if k == "a_th" else 4.5969))
            self._param_changed(k)

        def _param_value(self, k):
            if k in OPTIONAL_KEYS and self.punset[k].get(): return None
            s = self.pvars[k].get().strip()
            if not s: raise ValueError(f"{k}: enter a number")
            v = float(s)
            if not math.isfinite(v): raise ValueError(f"{k}: must be finite")
            return v

        def _param_changed(self, k):
            try: changed = self._param_value(k) != DEFAULT_PARAMS[k]
            except ValueError: changed = True
            self.plabels[k].config(style="Changed.TLabel" if changed else "Key.TLabel")
            n = sum(1 for key in self.pvars if self.plabels[key].cget("style") == "Changed.TLabel")
            self.l_changed.config(text=f"{n} parameter{'s' if n != 1 else ''} changed from the defaults" if n else "all defaults")

        def reset_param(self, k):
            if k in OPTIONAL_KEYS:
                self.punset[k].set(DEFAULT_PARAMS[k] is None); self._unset_toggled(k)
                if DEFAULT_PARAMS[k] is not None: self.pvars[k].set(_fmt_param(DEFAULT_PARAMS[k]))
            else:
                self.pvars[k].set(_fmt_param(DEFAULT_PARAMS[k]))

        def reset_params(self):
            for k in DEFAULT_PARAMS: self.reset_param(k)

        def set_params(self, overrides):
            self.reset_params()
            for k, v in (overrides or {}).items():
                if k in OPTIONAL_KEYS:
                    self.punset[k].set(v is None); self._unset_toggled(k)
                if v is not None: self.pvars[k].set(_fmt_param(v))

        def get_overrides(self):
            ov, errs = {}, []
            for k in DEFAULT_PARAMS:
                try:
                    v = self._param_value(k)
                    if v != DEFAULT_PARAMS[k]: ov[k] = v
                except ValueError as e:
                    errs.append(str(e) if str(e).startswith(k) else f"{k}: not a number ({self.pvars[k].get()!r})")
            return ov, errs

        # ------------------------------------------------------------------ events tab
        def _build_events(self):
            f = self.tab_ev
            bar = ttk.Frame(f); bar.pack(fill="x", padx=6, pady=4)
            for txt, cmd in [("Add event", self.ev_add), ("Delete selected", self.ev_delete), ("Move up", lambda: self.ev_move(-1)),
                             ("Move down", lambda: self.ev_move(1)), ("Clear", self.ev_clear),
                             ("Build from template...", self.ev_template), ("Load test sequence", self.ev_test),
                             ("Import CSV...", self.ev_import), ("Export CSV...", self.ev_export)]:
                ttk.Button(bar, text=txt, command=cmd).pack(side="left", padx=2)
            ttk.Label(f, style="Muted.TLabel", wraplength=1100, justify="left",
                      text="The event list is the caller's protocol (spec section 3) and is applied to every subject. "
                           "Double-click a cell to edit it. Onset times must be non-decreasing. The stimulus is fixed at 8 s "
                           "(1.5 s rise from 32 C, 5 s at target, 1.5 s fall; contract 6). Temperatures are never clamped: "
                           "events outside 40 to 49 C, below 34 or above 50 C, at a fourth visit, or off the 28 s / 168 s "
                           "timing are evaluated and flagged in the output.").pack(fill="x", padx=8)
            tf = ttk.Frame(f); tf.pack(fill="both", expand=True, padx=6, pady=4)
            cols = ("n", "t_s", "region", "spot", "temp_c", "visit", "notes")
            self.tree = ttk.Treeview(tf, columns=cols, show="headings", selectmode="extended")
            for c_, w, t in zip(cols, (50, 90, 100, 60, 90, 60, 520),
                                ("#", "onset t_s (s)", "region", "spot", "temp_c (C)", "visit", "will be flagged")):
                self.tree.heading(c_, text=t); self.tree.column(c_, width=w, anchor="w", stretch=(c_ == "notes"))
            self.tree.pack(side="left", fill="both", expand=True)
            sb = ttk.Scrollbar(tf, command=self.tree.yview); sb.pack(side="right", fill="y"); self.tree.config(yscrollcommand=sb.set)
            self.tree.bind("<Double-1>", self._ev_edit)
            self.l_ev = ttk.Label(f, text=""); self.l_ev.pack(fill="x", padx=8, pady=(0, 6))
            self._editor = None

        def _ev_notes(self):
            """Spec section 3."""
            notes = []; prev = None; last = {}; vis = {}
            for e in self.events:
                n = []
                try:
                    T = float(e["temp_c"]); t = float(e["t_s"]); k = (e["region"], int(e["spot"]))
                except (TypeError, ValueError, KeyError):
                    notes.append(("", "invalid")); continue
                vis[k] = vis.get(k, 0) + 1
                if not (WINDOW[0] <= T <= WINDOW[1]): n.append("outside 40-49 C")
                if T < EXTRAP[0] or T > EXTRAP[1]: n.append("extrapolated (<34 or >50 C)")
                if vis[k] >= 4: n.append("beyond measured visits (4th+)")
                if prev is not None and not (GAP_OK[0] <= t - prev <= GAP_OK[1]): n.append(f"onset gap {t - prev:g} s (26-30)")
                if k in last and not (REVISIT_OK[0] <= t - last[k] <= REVISIT_OK[1]): n.append(f"revisit {t - last[k]:g} s (156-180)")
                if prev is not None and t < prev: n.append("ERROR: onset earlier than previous")
                prev = t; last[k] = t; notes.append((vis[k], "; ".join(n)))
            return notes

        def ev_refresh(self, select=None):
            self.tree.delete(*self.tree.get_children())
            for i, (e, (v, n)) in enumerate(zip(self.events, self._ev_notes())):
                self.tree.insert("", "end", iid=str(i), values=(i + 1, f"{e['t_s']:g}", e["region"], e["spot"],
                                                               f"{e['temp_c']:g}", v, n))
            if select is not None:
                sel = [str(i) for i in select if 0 <= i < len(self.events)]
                if sel: self.tree.selection_set(sel); self.tree.see(sel[0])
            nfl = sum(1 for _v, n in self._ev_notes() if n)
            span = (self.events[-1]["t_s"] - self.events[0]["t_s"]) if self.events else 0
            self.l_ev.config(text=f"{len(self.events)} events, onsets spanning {span:g} s; {nfl} event"
                                  f"{'s' if nfl != 1 else ''} will carry a flag")

        def _sel(self): return sorted(int(i) for i in self.tree.selection())

        def ev_add(self):
            s = self._sel(); pos = (s[-1] + 1) if s else len(self.events)
            prev = self.events[pos - 1] if pos > 0 else None
            if prev:
                try: k = INTENDED_ORDER.index((prev["region"], int(prev["spot"])))
                except ValueError: k = -1
                reg, sp = INTENDED_ORDER[(k + 1) % 6]; e = ev(float(prev["t_s"]) + 28.0, reg, sp, float(prev["temp_c"]))
            else:
                e = ev(0.0, "forearm", 1, 45.0)
            self.events.insert(pos, e); self.ev_refresh(select=[pos])

        def ev_delete(self):
            s = self._sel()
            for i in reversed(s): del self.events[i]
            self.ev_refresh()

        def ev_move(self, d):
            s = self._sel()
            if not s: return
            if (d < 0 and s[0] == 0) or (d > 0 and s[-1] == len(self.events) - 1): return
            order = s if d < 0 else list(reversed(s))
            for i in order: self.events[i], self.events[i + d] = self.events[i + d], self.events[i]
            self.ev_refresh(select=[i + d for i in s])

        def ev_clear(self):
            if self.events and messagebox.askyesno("Clear events", "Remove every event?"):
                self.events = []; self.ev_refresh()

        def ev_test(self):
            if not self.events or messagebox.askyesno("Load test sequence", "Replace the event list with the 18-event "
                                                      "test sequence (make_golden.py)? It is a test sequence, not a "
                                                      "recommended protocol."):
                self.events = [dict(e) for e in TEST_SEQUENCE]; self.ev_refresh()

        def ev_import(self):
            p = filedialog.askopenfilename(title="Import events CSV", filetypes=[("CSV", "*.csv"), ("All files", "*")])
            if not p: return
            try: evs = read_events_csv(p)
            except Exception as e: messagebox.showerror("Import events", str(e)); return
            errs = check_events(evs)
            if errs: messagebox.showerror("Import events", "\n".join(errs[:20])); return
            self.events = evs; self.ev_refresh(); self.log(f"Imported {len(evs)} events from {p}")

        def ev_export(self):
            p = filedialog.asksaveasfilename(title="Export events CSV", defaultextension=".csv", filetypes=[("CSV", "*.csv")])
            if p: write_events_csv(p, self.events); self.log(f"Exported {len(self.events)} events to {p}")

        def _ev_edit(self, e):
            if self.tree.identify("region", e.x, e.y) != "cell": return
            row = self.tree.identify_row(e.y); col = self.tree.identify_column(e.x)
            name = self.tree["columns"][int(col[1:]) - 1]
            if not row or name not in ("t_s", "region", "spot", "temp_c"): return
            i = int(row); x, y, w, h = self.tree.bbox(row, col)
            if self._editor: self._editor.destroy()
            var = tk.StringVar(value=str(self.events[i][name]))
            if name == "region": w_ = ttk.Combobox(self.tree, textvariable=var, values=["forearm", "thenar"], state="readonly")
            elif name == "spot": w_ = ttk.Combobox(self.tree, textvariable=var, values=["1", "2", "3"], state="readonly")
            else: w_ = ttk.Entry(self.tree, textvariable=var)
            w_.place(x=x, y=y, width=max(w, 90), height=h); w_.focus_set(); self._editor = w_
            if isinstance(w_, ttk.Entry) and not isinstance(w_, ttk.Combobox): w_.select_range(0, "end")

            def commit(_e=None):
                if self._editor is None: return
                s = var.get().strip()
                try:
                    if name in ("t_s", "temp_c"):
                        v = float(s)
                        if not math.isfinite(v): raise ValueError
                    elif name == "spot": v = int(s)
                    else: v = s
                    self.events[i][name] = v
                except ValueError:
                    messagebox.showerror("Edit event", f"{name}: '{s}' is not valid")
                self._editor.destroy(); self._editor = None; self.ev_refresh(select=[i])

            def cancel(_e=None):
                if self._editor: self._editor.destroy(); self._editor = None
            w_.bind("<Return>", commit); w_.bind("<Escape>", cancel); w_.bind("<FocusOut>", commit)
            if isinstance(w_, ttk.Combobox): w_.bind("<<ComboboxSelected>>", commit)

        def ev_template(self):
            d = tk.Toplevel(self.root); d.title("Build events from a template"); d.transient(self.root); d.grab_set()
            vs = dict(n=tk.StringVar(value="18"), start=tk.StringVar(value="0"), gap=tk.StringVar(value="28"),
                      order=tk.StringVar(value="F1, T1, F2, T2, F3, T3"), temps=tk.StringVar(value="45"))
            rows = [("Number of events", "n"), ("First onset (s)", "start"), ("Onset-to-onset interval (s)", "gap"),
                    ("Spot order, cycled (F = forearm, T = thenar)", "order"),
                    ("Temperatures (C): one value for all, or one per event", "temps")]
            for i, (t, k) in enumerate(rows):
                ttk.Label(d, text=t).grid(row=i, column=0, sticky="w", padx=8, pady=4)
                ttk.Entry(d, textvariable=vs[k], width=60 if k == "temps" else 30).grid(row=i, column=1, sticky="w", padx=8)
            ttk.Label(d, style="Muted.TLabel", wraplength=560, justify="left",
                      text="Defaults follow the spec's intended order and timing (section 1): onsets every 28 s, the six "
                           "spots alternating between regions, so every revisit falls at 168 s. 18 events give 3 visits "
                           "per spot, the most the parameters were measured at. Temperatures are your protocol's choice."
                      ).grid(row=len(rows), column=0, columnspan=2, sticky="w", padx=8, pady=6)

            def build():
                try:
                    evs = build_template(vs["n"].get(), vs["start"].get(), vs["gap"].get(), vs["order"].get(), vs["temps"].get())
                except ValueError as e:
                    messagebox.showerror("Template", str(e), parent=d); return
                if self.events and not messagebox.askyesno("Template", "Replace the current event list?", parent=d): return
                self.events = evs; self.ev_refresh(); d.destroy()
            bf = ttk.Frame(d); bf.grid(row=len(rows) + 1, column=0, columnspan=2, pady=8)
            ttk.Button(bf, text="Build", command=build).pack(side="left", padx=4)
            ttk.Button(bf, text="Cancel", command=d.destroy).pack(side="left", padx=4)

        # ------------------------------------------------------------------ reference tab
        def _build_reference(self):
            t = tk.Text(self.tab_ref, wrap="word", font=("TkFixedFont", 9)); sb = ttk.Scrollbar(self.tab_ref, command=t.yview)
            t.config(yscrollcommand=sb.set); sb.pack(side="right", fill="y"); t.pack(fill="both", expand=True, padx=6, pady=6)
            t.insert("1.0", reference_text()); t.config(state="disabled")

        # ------------------------------------------------------------------ config in and out
        def get_config(self):
            errs = []
            cfg = default_config()
            try: cfg["seed"] = int(self.v_seed.get().strip())
            except ValueError: errs.append("seed: must be a non-negative integer")
            try: cfg["n_subjects"] = int(self.v_n.get().strip())
            except ValueError: errs.append("number of subjects: must be a whole number")
            cfg["scenario"] = self.v_scen.get(); cfg["grid_mode"] = bool(self.v_grid.get())
            ov, perr = self.get_overrides(); cfg["params"] = ov; errs += perr
            cfg["events"] = [dict(e) for e in self.events]
            o = cfg["output"]
            o.update(directory=self.v_dir.get().strip(), prefix=self.v_prefix.get().strip() or "heat_pain",
                     scale=self.v_scale.get(), include_diagnostics=bool(self.v_diag.get()),
                     events_csv=bool(self.v_evcsv.get()), persons_csv=bool(self.v_pcsv.get()),
                     summary_csv=bool(self.v_scsv.get()), rating_temperature_csv=bool(self.v_rtcsv.get()),
                     plot=bool(self.v_plot.get()), plot_format=self.v_pfmt.get(), plot_rating=self.v_prat.get(),
                     plot_curves=bool(self.v_pcur.get()))
            try:
                o["plot_max_curves"] = int(self.v_pmax.get()); assert o["plot_max_curves"] >= 0
            except (ValueError, AssertionError): errs.append("plot: number of fresh-skin curves must be a whole number >= 0")
            try:
                o["plot_dpi"] = int(self.v_pdpi.get()); assert 20 <= o["plot_dpi"] <= 1200
            except (ValueError, AssertionError): errs.append("plot: DPI must be a whole number from 20 to 1200")
            return cfg, errs

        def set_config(self, cfg):
            self.v_seed.set(str(cfg["seed"])); self.v_n.set(str(cfg["n_subjects"])); self.v_scen.set(cfg["scenario"])
            self.v_grid.set(bool(cfg["grid_mode"])); self._grid_toggled(); self.set_params(cfg["params"])
            self.events = [dict(e) for e in cfg["events"]]; self.ev_refresh()
            o = {**default_output_options(), **cfg["output"]}
            self.v_dir.set(o["directory"] or os.getcwd()); self.v_prefix.set(o["prefix"]); self.v_scale.set(o["scale"])
            self.v_diag.set(o["include_diagnostics"]); self.v_evcsv.set(o["events_csv"]); self.v_pcsv.set(o["persons_csv"])
            self.v_scsv.set(o["summary_csv"]); self.v_rtcsv.set(o["rating_temperature_csv"])
            self.v_plot.set(bool(o["plot"]) and have_matplotlib()); self.v_pfmt.set(o["plot_format"])
            self.v_prat.set(o["plot_rating"]); self.v_pcur.set(o["plot_curves"]); self.v_pmax.set(str(o["plot_max_curves"]))
            self.v_pdpi.set(str(o["plot_dpi"]))

        def on_load(self):
            p = filedialog.askopenfilename(title="Load configuration or manifest", filetypes=[("JSON", "*.json"), ("All files", "*")])
            if not p: return
            try: cfg = load_config(p)
            except Exception as e: messagebox.showerror("Load configuration", str(e)); return
            self.set_config(cfg); self.log(f"Loaded configuration from {p}")

        def on_save(self):
            cfg, errs = self.get_config()
            if errs: messagebox.showerror("Save configuration", "\n".join(errs)); return
            p = filedialog.asksaveasfilename(title="Save configuration", defaultextension=".json", filetypes=[("JSON", "*.json")])
            if p: save_config(cfg, p); self.log(f"Saved configuration to {p}")

        def on_reset_all(self):
            if messagebox.askyesno("Reset", "Reset the seed, subjects, scenario, parameters, events and output options to defaults?"):
                self.set_config(default_config())

        def on_browse(self):
            d = filedialog.askdirectory(title="Output folder", initialdir=self.v_dir.get() or os.getcwd())
            if d: self.v_dir.set(d)

        # ------------------------------------------------------------------ running
        def _busy(self, busy):
            self.b_go.config(state="disabled" if busy else "normal")
            self.b_cancel.config(state="normal" if busy else "disabled")

        def on_generate(self):
            if self.worker and self.worker.is_alive(): return
            cfg, errs = self.get_config()
            if not errs:
                e2, notes = validate_config(cfg); errs += e2
            if errs:
                messagebox.showerror("Cannot generate", "\n".join(errs[:25])); return
            exist = [f for f in planned_files(cfg) if os.path.exists(f)]
            if exist and not messagebox.askyesno("Overwrite", f"{len(exist)} output file(s) already exist, e.g.\n"
                                                 f"{exist[0]}\n\nOverwrite them?"):
                return
            if cfg["output"]["plot"] and len(build_runs(cfg)) * len(cfg["events"]) * cfg["n_subjects"] > 2_000_000:
                self.log("Note: the plot draws every event; with this many points it will take a while.")
            self.log("-" * 100)
            mode = "15-cell grid" if cfg["grid_mode"] else f"scenario {cfg['scenario']}"
            self.log(f"Generate: base seed {cfg['seed']}, {cfg['n_subjects']} subjects, {mode}, {len(cfg['events'])} events, "
                     f"{len(cfg['params'])} parameter override(s){': ' + ', '.join(f'{k}={v!r}' for k, v in cfg['params'].items()) if cfg['params'] else ''}")
            for n in notes: self.log("Note: " + n)
            self.cancel.clear(); self._busy(True); self.pb.config(value=0, maximum=1)

            def work():
                try:
                    res = run_batch(cfg, progress=lambda d, t: self.q.put(("progress", d, t)), cancel=self.cancel)
                    self.q.put(("status", "writing files..."))
                    files, ev_rows = write_outputs(res, log=lambda s: self.q.put(("log", s)))
                    for ln in run_summary_lines(res, ev_rows): self.q.put(("log", ln))
                    self.q.put(("done", files))
                except Cancelled:
                    self.q.put(("cancelled",))
                except Exception as e:
                    import traceback
                    self.q.put(("error", f"{e}\n\n{traceback.format_exc(limit=3)}"))
            self.worker = threading.Thread(target=work, daemon=True); self.worker.start()

        def on_selftest(self):
            def work():
                res = run_unit_tests(); bad = [r for r in res if not r["passed"]]
                for r in bad: self.q.put(("log", f"FAIL check {r['check']}: {r['name']}"))
                self.q.put(("log", f"Self-tests: {len(res) - len(bad)} of {len(res)} pass (spec section 16, checks 8 to 10)"))
            self.log("Running the 49 unit tests..."); threading.Thread(target=work, daemon=True).start()

        def on_golden(self):
            here = os.path.dirname(os.path.abspath(__file__))
            init = os.path.join(here, "golden_vectors.json")
            p = filedialog.askopenfilename(title="golden_vectors.json from the v2.8 package",
                                           initialdir=here, initialfile="golden_vectors.json" if os.path.exists(init) else "",
                                           filetypes=[("JSON", "*.json")])
            if not p: return

            def work():
                try:
                    n, mx, fl = replay_golden(p)
                    ok = (mx == 0.0 and fl)
                    self.q.put(("log", f"Golden vectors: {n} cases, max numeric difference {mx:.3g}, flags "
                                       f"{'identical' if fl else 'DIFFER'}: {'PASS' if ok else 'FAIL (different numpy/scipy can give tiny differences; the guide allows 1e-6)'}"))
                except Exception as e:
                    self.q.put(("log", f"Golden vectors: could not replay ({e})"))
            self.log("Replaying golden vectors..."); threading.Thread(target=work, daemon=True).start()

        def _poll(self):
            try:
                while True:
                    m = self.q.get_nowait()
                    if m[0] == "progress":
                        self.pb.config(maximum=m[2], value=m[1]); self.l_status.config(text=f"{m[1]} of {m[2]} subject-runs")
                    elif m[0] == "status": self.l_status.config(text=m[1])
                    elif m[0] == "log": self.log(m[1])
                    elif m[0] == "done":
                        self._busy(False); self.l_status.config(text="done")
                        self.log("Wrote:"); [self.log("  " + f) for f in m[1]]
                    elif m[0] == "cancelled":
                        self._busy(False); self.l_status.config(text="cancelled"); self.log("Cancelled; no files written.")
                    elif m[0] == "error":
                        self._busy(False); self.l_status.config(text="error"); self.log("ERROR: " + m[1])
                        messagebox.showerror("Error", m[1].split("\n\n")[0])
            except queue.Empty:
                pass
            self.root.after(100, self._poll)

    root = tk.Tk()
    app = App(root)
    if run: root.mainloop()
    return root, app


if __name__ == "__main__":
    try:
        import tkinter  # noqa: F401
    except ImportError:
        sys.exit("tkinter is not available in this Python. Install it (e.g. `sudo apt install python3-tk`, "
                 "`brew install python-tk`, or use the python.org installer) and run again.")
    launch_gui()
