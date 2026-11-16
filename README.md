# Heat-pain rating generator (`SfN_2026_heat_pain_gui.py`)

Generator version 2.8; GUI tool version 1.0.

`SfN_2026_heat_pain_gui.py` produces seeded, reproducible simulated pain ratings on the 0 to 10 scale for a batch of simulated people. You supply an event list (onset time, body region, spot, target temperature); the tool returns, for every person and event, a noise-free `latent` rating and a noisy `observed` rating. Its purpose is to let calibration procedures be run against simulated people and scored against a known ground truth: a procedure sees only `observed`, and is scored against `latent`.

The numbered sections of this README use the same numbers as the section references in the GUI (for example the "Parameters (section 5)" tab, the "Scenario (section 12)" panel, the "0 to 100 (x10, section 2)" option and the "Run self-tests (checks 8 to 10)" button, where checks are numbered in section 16).

---

## Contents

- [Getting started](#getting-started)
- [1. Scope](#1-scope)
- [2. The rating scale](#2-the-rating-scale)
- [3. Interface: inputs, outputs and guarantees](#3-interface-inputs-outputs-and-guarantees)
- [4. The generator, step by step](#4-the-generator-step-by-step)
- [5. Parameters](#5-parameters)
- [6. Layer 1: the forearm person](#6-layer-1-the-forearm-person)
- [7. Layer 1b: how the population was fitted](#7-layer-1b-how-the-population-was-fitted)
- [8. Layer 2: the static response curve](#8-layer-2-the-static-response-curve)
- [9. Layer 3: reachability](#9-layer-3-reachability)
- [10. Layer 4: forearm to thenar](#10-layer-4-forearm-to-thenar)
- [11. Layer 5: within-session dynamics](#11-layer-5-within-session-dynamics)
- [12. Scenario presets and the 15-cell reporting grid](#12-scenario-presets-and-the-15-cell-reporting-grid)
- [13. Layer 6: observation noise](#13-layer-6-observation-noise)
- [14. Open questions and how they are handled](#14-open-questions-and-how-they-are-handled)
- [15. Assumptions and known limits](#15-assumptions-and-known-limits)
- [16. Validation checks](#16-validation-checks)
- [17. References](#17-references)
- [Appendix A. Output files](#appendix-a-output-files)
- [Appendix B. Seeding and reproducibility](#appendix-b-seeding-and-reproducibility)
- [Appendix C. Using the module from Python](#appendix-c-using-the-module-from-python)

---

## Getting started

### Requirements

| Package | Needed for | Notes |
| --- | --- | --- |
| Python 3.9 or later | everything | |
| numpy, scipy | everything | |
| tkinter | the GUI only | Standard library, but packaged separately on some Linux and conda Pythons (`sudo apt install python3-tk`, `brew install python-tk`, or the python.org installer) |
| matplotlib | the rating-vs-temperature plot only | Optional; without it the plot option is disabled and everything else works |

```bash
pip install numpy scipy matplotlib
python heat_pain_gui.py
```

If tkinter is missing the script exits with installation instructions. The module can also be imported without tkinter (Appendix C).

### The window

| Tab or menu | What it does | Section |
| --- | --- | --- |
| **File** menu | Load a saved configuration or a run manifest; save the configuration (JSON); reset everything to defaults | Appendix B |
| **Run and output** | Base seed and number of subjects; scenario preset or the 15-cell grid; output folder, file prefix, rating scale, tables and plot; Generate, Cancel, self-tests, golden-vector replay; the log | 2, 12, 16, Appendix A |
| **Parameters** | Every parameter, with default, meaning, sweep and source; changed values shown in red | 5 |
| **Stimulus events** | The event list applied to every subject: edit, build from a template, load the test sequence, import or export CSV, preview of the flags each event will carry | 3 |
| **Reference** | Read-only summary of the presets, the grid, the fixed constants, the output fields, the rules, the known limits and the sources | 12, 15, 17 |

**Typical run.** Set the base seed and number of subjects, choose a preset (or tick the 15-cell grid), set up the event list, choose the output folder, then press **Generate**. The run happens in the background with a progress bar; **Cancel** stops it and writes nothing. If any output file already exists you are asked before it is overwritten.

### Rules for using the output

- `latent` is the scoring target; `observed` is what a procedure may see.
- Report results on the 15-cell grid (section 12). A conclusion that changes across cells is reported as unresolved by the available evidence, not averaged.
- For sweeps, keep the seeds and change parameters only; every subject then differs between runs only through the parameter change (Appendix B).
- Inputs are evaluated and flagged, never clamped. Treat `extrapolated` and `beyond_measured_visits` outputs as outside the evidence.
- One person, one session. Replaying a person (`reset()`) is a counterfactual replay of the same session, not a second visit.

### Code layout

| Part | Contents |
| --- | --- |
| PART 1 | The generator: sources, fixed constants, full-precision defaults, scenario presets, the skew-normal threshold shape, the `Generator` class, and the 49 unit tests of checks 8 to 10. This part is an unedited copy of the reference implementation and reproduces its 75 reference cases (`golden_vectors.json`) exactly. |
| PART 2 | Interface metadata: parameter meanings, sweeps and sources, scenario descriptions, the 15-cell grid, fixed constants, the default test event sequence. |
| PART 3 | Batch runner and exporters (no GUI): subject seeds, validation, runs, tables, plots, manifest, configuration files, golden-vector replay. |
| PART 4 | The tkinter GUI. |

---

## 1. Scope

The generator answers one question: given a simulated person, a spot, a target temperature and the session history, what rating would be recorded?

**In scope.**
- Six spots per simulated session: three on the left volar forearm and three on the left thenar eminence.
- Between-person variation in heat-pain sensitivity and in habituation.
- A latent (expected) rating and a noisy observed rating for every event.
- Within-session change driven by the history at the same spot, the immediately preceding stimulus, and position in the session.

**Out of scope.** Calibration procedures, stopping rules, target definitions and scoring; the choice of temperatures, spot order and timing (these are your inputs); hardware and data collection; any second session. The tool applies one fixed event list to every subject.

**The simulated person is one person in one session.** A later real session is not a replay of the first: Evans et al. (2026) found session-2 thresholds 3.16 C higher than session 1, at intervals of about two days.

**Population.** Healthy, first-session, test-naive adults aged 18 to 50, under the medical inclusion criteria of Amir et al. (2022): no history of psychiatric or neurological disorder, chronic pain, substance abuse, or a major medical condition affecting somatosensation; not pregnant; no pain relievers within 5 half-lives.

**Why the left side.** The person layer, the dynamics and the noise all come from left volar forearm data. Laterality does not matter for thresholds (Schaffner et al., 2008; Taylor et al., 1993), but Evans et al. (2026) found side-dependent habituation, and every dynamics source is left-sided.

**Validity envelope.** Any event list is accepted. The parameters were estimated under the conditions below; events outside them are evaluated and flagged (section 3), never refused.

| Property | Value the parameters assume |
| --- | --- |
| Stimulus | 8 s: 1.5 s rise from 32 C, 5 s at target, 1.5 s fall (Amir et al., 2022) |
| Onset to onset | 28 s (tolerance 26 to 30 s), a 20 s gap from stimulus offset to the next onset |
| Same-spot revisit | 168 s (tolerance 156 to 180 s) |
| Visits per spot | at most 3, the most measured in the dynamics data |
| Temperature | 34 to 50 C, the span of the dynamics data; reporting window 40 to 49 C |

**The intended spot order** is forearm 1, thenar 1, forearm 2, thenar 2, forearm 3, thenar 3, repeating, with onsets every 28 s. Every revisit then falls at 168 s, and the event before every event is in the other region. This order is a choice, not a requirement; the template builder (section 3) uses it as its default. A 21 s onset interval would give a 126 s revisit, shorter than the recovery time reported for same-site suppression (more than 3.75 min in LaMotte & Campbell, 1978; more than 4 min in Jepma et al., 2014).

**Evidence base.**
- Amir et al. (2022), 342 visit-1 threshold and tolerance anchors: the person population.
- The Dildine and Atlas dataset (n.d.), 46 people and 1,104 trials, from the study of Dildine et al. (2020): curve shape, dynamics, between-person variation in habituation, noise.
- Jepma et al. (2014), 100 people: the independent replication of the dynamics.
- Lotsch et al. (2026), 125 forearm thresholds: the shape of the threshold distribution.
- Forearm to thenar: Hagander et al. (2000), Taylor et al. (1993), Eckert et al. (2017), Lautenbacher and Rollman (1993), Schaffner et al. (2008), LaMotte and Campbell (1978).

The Dildine, Mischkowski and Amir samples come from the same screening pipeline, so the Dildine fits are not an independent check on the Amir anchors; Jepma et al. (2014) is the only independent replication of the dynamics.

**What it does not claim.** The generator does not reproduce any individual. Its target is a population whose marginal distributions, curve shape, within-session dynamics and residual distribution match published estimates, with the shortfalls stated (section 15).

## 2. The rating scale

Every value lives on the 0 to 10 scale used by all the sources: 0 no sensation, 1 warmth but not pain, 2 pain threshold, 5 moderate pain, 8 pain tolerance (the most pain the person is willing to tolerate), 10 most pain imaginable (Amir et al., 2022; Mischkowski et al., 2021).

- Moderate pain is a rating of 5. No tolerance band around it is defined here.
- The scale is treated as an interval scale, as every source does.
- **0 to 100 output.** The **Rating scale** option on the Run and output tab multiplies `latent`, `observed` and the diagnostic `raw` by 10. No parameter changes; `z` and all temperatures are unchanged; plot anchors and axes are scaled to match.

## 3. Interface: inputs, outputs and guarantees

`Generator(seed, params=None, scenario="P1")` draws one simulated person when it is created, and exposes `simulate(events, duration_s=8.0)`, `reset()` and `person()`.

### Inputs: the event list

| Field | Type | Meaning |
| --- | --- | --- |
| `t_s` | number | onset time in seconds from session start; must be non-decreasing |
| `region` | `forearm` or `thenar` | body region |
| `spot` | 1, 2 or 3 | spot within the region |
| `temp_c` | number | target temperature (C) |

### Outputs: one record per event, in order

| Field | Meaning |
| --- | --- |
| `latent` | expected rating with no noise, `clip(R_raw, 0, 10)`. **The scoring target.** |
| `observed` | `clip(R_raw + sigma(R_raw) z, 0, 10)`, the rating a procedure may see |
| `raw` | diagnostic: the unclipped rating `R_raw` |
| `z` | diagnostic: the standardised noise value |
| `in_window` | true when 40 <= `temp_c` <= 49 |
| `extrapolated` | true when `temp_c` < 34 or `temp_c` > 50 |
| `beyond_measured_visits` | true on the fourth or later visit to a spot |
| `off_protocol_timing` | true when the onset interval from the previous event lies outside 26 to 30 s, or the interval since the previous visit to the same spot lies outside 156 to 180 s; never set on the first event, and the revisit condition never set on a first visit |

`person()` returns, for each region, the fresh-skin threshold and tolerance (C), the width, the exponent `b`, the zero point (32 C), the mean step and step SD that apply in that region under the scenario, the person's own step, and the fresh-skin temperature for any rating, `T(R) = 32 + (T_thr - 32) (R / 2)^(1/b)`.

### Guarantees

- **Determinism.** The same seed, parameters, scenario and event list give identical output. Two independent random streams come from each seed: a person stream of exactly six uniforms, used at creation, and a noise stream of one uniform per event.
- **The person never changes.** `reset()` clears all session history (all six spot histories, the previous event, the event counter, the noise autocorrelation) and rewinds the noise stream only.
- **Common random numbers.** Every random quantity is an inverse CDF applied to one uniform; there are no redraws. The same seed under different parameter values gives the same person and the same noise ranks, moved only by the parameter change. Sweeps rely on this.
- **Inputs are never clamped or modified.** Out-of-window and out-of-range events are evaluated and flagged.
- **`latent` is the scoring target; `observed` is what a procedure may see.**
- **Stimulus duration is fixed at 8 s.** Any other `duration_s` raises.
- **Overrides.** `params` overrides any single key of section 5; an unrecognised key or scenario raises.

### The Stimulus events tab

- **Edit.** Add event (continues the intended spot order at +28 s and the previous temperature), Delete selected, Move up, Move down, Clear. Double-click a cell to edit `t_s`, `region`, `spot` or `temp_c`.
- **Build from template.** Number of events, first onset, onset interval, a cycled spot order, and either one temperature for all events or exactly one per event. Spot order accepts `F1, T1, F2`, `forearm 1`, `thenar-2` and similar. The defaults (18 events every 28 s in the intended order) give 3 visits per spot with every revisit at 168 s. Temperatures are your protocol's choice.
- **Load test sequence.** The 18-event sequence used to build the reference cases (intended order, 28 s onsets, mixed temperatures from 40 to 49 C). It is a test sequence, not a recommended protocol.
- **Import CSV / Export CSV.** Columns `t_s, region, spot, temp_c` with a header row; other columns are ignored.
- **Flag preview.** The "will be flagged" column shows, before you run, which events will fall outside 40 to 49 C, be extrapolated, be a fourth or later visit, or be off the 26 to 30 s or 156 to 180 s timing. An onset earlier than the previous one is marked as an error and refused at Generate.

## 4. The generator, step by step

Constants: zero point 32 C; carry-over reference 44.84 C; drift and previous-stimulus reference 45 C; onset window the first 3 events; visit-3 step multiplier `m_step` = 1.43.

**Step A. Draw the person (once).**
1. Draw `U1` to `U6` from the person stream.
2. Let `g(z)` be the standardised skew-normal quantile function with shape `alpha_pop` (mean 0, SD 1; `g(z) = z` when `alpha_pop` = 0). The forearm median log threshold is `med1 = m1 + s1 g(0)`; the thenar location and scale apply the offset and the spread ratio at the median: `s3 = kappa s1 exp(med1) / (exp(med1) + Delta)`, `m3 = ln(exp(med1) + Delta) - s3 g(0)`.
3. Form the covariance of (forearm log threshold, forearm log width, thenar log threshold):

   ```
   | s1^2        r s1 s2       rho s1 s3   |
   | r s1 s2     s2^2          rho r s2 s3 |
   | rho s1 s3   rho r s2 s3   s3^2        |
   ```
4. Take its Cholesky factor (forearm first), apply it to the normal scores of `U1` to `U3`, then apply the skew shape to the two log thresholds through their normal scores. The width is not transformed.
5. `z = Phi^-1(U4)` is the step variate, shared by both regions; `xi = Phi^-1(U5)` is the thenar log-width deviate; `U6` is reserved.
6. Forearm: `T_thr = 32 + exp(x1)`, `W = exp(x2)`. Thenar: `T_thr = 32 + exp(x3)` and `ln W_th = ln(exp(m2) / k_slope) + rho_W (x2 - m2) + s2 sqrt(1 - rho_W^2) xi`.
7. In each region `T_tol = T_thr + W` and `b = ln 4 / ln((T_tol - 32) / (T_thr - 32))`.
8. Step parameters by region and scenario (section 12): the mean step is `S` on the forearm, and on the thenar `S` under P1, P2, S1, S3 and `S_th` under P3, P4, S2. The step SD is `sigma_S` everywhere unless `sigma_S_th` is set, which then applies on the thenar under P3, P4 and S2 only.

Because the factor is ordered forearm first, changing `Delta`, `kappa`, `rho` or `rho_W` never changes the forearm person, and changing `alpha_pop` never changes either width.

**Step B. Evaluate each event.** For event `i` (counted from 1), at region `g`, spot `j`, temperature `T`: `v` is the visit number at that spot; `T_1`, `T_2` are the temperatures of the last and second-last visits to the spot; `T_prev` is the temperature of event `i - 1`.

```
R_g(T) = 2 ((T - 32) / (T_thr,g - 32))^b_g      for T > 32;  0 otherwise

R_raw = R_g(T) (1 + a_g [i <= 3])
      + [v > 1] ( min(0, m_v S_g + beta_1 (T_1 - 44.84) + beta_2 (T_2 - 44.84) [v > 2]) + m_v sigma_S,g z )
      + gamma (min(v, 3) - 1) (T - 45)
      + c tau (T_prev - 45) [i > 1] [event i-1 is not at this spot]
```

- `m_v` is 1 at visit 2 and `m_step` at visit 3 and later; it multiplies the mean step inside the cap and the person's step deviation outside it, not `beta_1` or `beta_2`.
- The drift multiplier `min(v, 3) - 1` is 0, 1, 2 at visits 1, 2, 3+.
- `tau` is 1 when the previous event is in the same region, otherwise the scenario's cross-region value for that direction (section 12).
- `a_g` is `a` on the forearm; on the thenar it is `a_th` if set, otherwise `a`, and 0 under S3.
- `latent = clip(R_raw, 0, 10)`.

**Step C. Add noise.** Draw one uniform from the noise stream; `u_i` is the standard Student `t` quantile with `nu` degrees of freedom (not rescaled). Then `z_1 = u_1`, `z_i = phi z_(i-1) + sqrt(1 - phi^2) u_i`, `sigma(R) = s0 + s1n exp(-(R - peak)^2 / (2 w^2))`, and `observed = clip(R_raw + sigma(R_raw) z_i, 0, 10)`. The autocorrelation runs in event order across both regions; `sigma` is evaluated at the unclipped `R_raw` and is positive everywhere.

**Step D. Set the flags** (section 3), then record the event in the spot's history and as the previous event.

## 5. Parameters

Every parameter can be changed on the **Parameters** tab, which shows its key, editable full-precision value, a **Default** button, the printed default, meaning, sweep and source. Changed keys are shown in red and counted at the top; **Reset all parameters to defaults** restores them.

- **Sweep** is the range over which a parameter should be varied in a sensitivity analysis, usually its 95 percent interval. A value outside it is allowed and noted in the log as a labelled sensitivity outside the evidence.
- **Refused values.** Generate refuses values the equations cannot evaluate: non-finite values; `s1`, `s2`, `kappa`, `k_slope` or `nu` <= 0; `w` = 0; a correlation (`r`, `rho`, `rho_W`, `phi`) outside [-1, 1]; |`r`| = 1 or |`rho`| = 1 (the covariance is then singular); a person draw that is not finite.
- **`a_th` and `sigma_S_th`** have an **unset** box, ticked by default (unset means equal to `a` and `sigma_S`). Unticking fills a starting value of 0 or 4.5969.
- **`m_step`** is not swept (section 11.2).

**Source tags.** [read]: taken from the text, a table or a figure of a cited source. [refit]: estimated by refitting one of the three source datasets (Amir et al., 2022; Dildine & Atlas, n.d.; Lotsch et al., 2026). [model]: follows by construction or arithmetic on stated quantities. [design]: a protocol choice.

**Person population (Layer 1, section 6).**

| Key | Meaning | Default | Sweep | Source |
| --- | --- | --- | --- | --- |
| `m1` | mean of ln(T_thr - 32), forearm fresh skin | 2.33030 | 2.2731 to 2.3875 (approximate conditional interval) | Layer 1b (section 7) [refit] |
| `s1` | SD of ln(T_thr - 32) | 0.35514 | 0.3037 to 0.4066 | Layer 1b [refit] |
| `m2` | location of ln W (W = tolerance - threshold) | 1.62249 | 1.5290 to 1.7160 | Layer 1b [refit] |
| `s2` | scale of ln W | 0.50008 | 0.4129 to 0.5873 | Layer 1b [refit] |
| `r` | correlation of the normal scores of ln(T_thr - 32) and ln W (Gaussian copula) | -0.81198 | -0.8849 to -0.7390 | Layer 1b [refit] |
| `alpha_pop` | skew-normal shape of ln(T_thr - 32), both regions (0 is the log-normal) | -3.5272 | -6.17 to -1.98; log-normal (0) as a reference | Lotsch et al. (2026) [refit] |

Implied fresh-skin medians: threshold 42.83 C, width 5.07 C, tolerance 47.90 C.

**Forearm to thenar (Layer 4, section 10).**

| Key | Meaning | Default | Sweep | Source |
| --- | --- | --- | --- | --- |
| `Delta` | thenar threshold offset at the median (C) | +0.5 | co-primary +0.5 and +0.9; stress +1.6; 0 under P3 and P4 (grid cells) | Hagander et al. (2000); Taylor et al. (1993); Eckert et al. (2017) [read] |
| `kappa` | thenar-to-forearm threshold spread ratio, in degrees at the median | 1.2 | 1.04 to 1.37; stress 1.50 | Eckert et al. (2017); Taylor et al. (1993); Hagander et al. (2000) [read]; pooled 1.203 [model] |
| `k_slope` | slope ratio; thenar width is forearm width divided by `k_slope` at the median | 0.92 | 0.56 to 1.27 | Taylor et al. (1993), Table 3 [read]; sampling interval [model] |
| `rho` | forearm-thenar log-threshold correlation (latent Pearson) | 0.75 | 0.3 to 0.9 | Lautenbacher and Rollman (1993), proxy [read] |
| `rho_W` | forearm-thenar log-width correlation | 0.63 | 0.3 to 1.0; reference points 0.75 and 1.0 | Schaffner et al. (2008) with the reliabilities of Amir et al. (2022) [read], [model] |

**Within-session dynamics (Layer 5, section 11).**

| Key | Meaning | Default | Sweep | Source |
| --- | --- | --- | --- | --- |
| `S` | mean revisit step, forearm (rating units) | -0.2134 | -0.4283 to +0.0259 | Dildine matched set [refit] |
| `sigma_S` | between-person step SD, absolute, both regions | 0.6705 | 0.4095 to 0.8660 | [refit] |
| `m_step` | multiplier on the step at visit 3 and later | 1.43 | not swept (section 11.2) | Dildine profile [refit]; inside the bound from Jepma et al. (2014) [read], [model] |
| `gamma` | drift per C of (T - 45), per drift unit (0, 1, 2) | +0.0404 | -0.0188 to +0.1015; stress +0.0772 | [refit]; stress from Jepma et al. (2014) [read] |
| `beta_1` | lag-1 same-spot carry-over, per C of (T_1 - 44.84) | -0.0426 | -0.0967 to +0.0205 | [refit]; Jepma et al. (2014) value -0.0679 lies inside |
| `beta_2` | lag-2 same-spot carry-over, per C of (T_2 - 44.84) | 0 | -0.0595 to +0.0920 (fitted +0.0134) | [refit] |
| `c` | previous stimulus, per C of (T_prev - 45) | +0.0880 | +0.0571 to +0.1284; co-primary +0.035 outside the sweep | [refit]; co-primary from Jepma et al. (2014) [read] |
| `a` | proportional onset term, events 1 to 3 (factor 1 + a = 0.7626) | -0.2374 | -0.2923 to -0.1810 | [refit] |
| `a_th` | thenar onset term; unset means equal to `a` | unset | 0 under S3 | LaMotte and Campbell (1978) [read] |
| `S_th` | thenar mean step under P3, P4, S2 | -1.4628 | -1.909 to -1.142 | LaMotte and Campbell (1978), converted [read], [model] |
| `sigma_S_th` | thenar step SD under P3, P4, S2; unset means equal to `sigma_S` | unset | proportional sensitivity 4.5969 | assumption item 43 (section 15) [model] |

**Observation noise (Layer 6, section 13).** All six calibrated jointly [refit].

| Key | Meaning | Default | Sweep |
| --- | --- | --- | --- |
| `nu` | Student `t` innovation degrees of freedom (not rescaled) | 5.8603 | 2.673 to 9.047 |
| `s0` | asymptotic spread away from the peak | 0.3031 | 0.112 to 0.494 |
| `s1n` | peak spread increment (distinct from the population's `s1`) | 1.3927 | 0.997 to 1.788 |
| `w` | width of the spread bump (rating units) | 1.6975 | 1.390 to 2.005 |
| `peak` | rating at which the spread peaks | 4.4402 | 4.192 to 4.688 |
| `phi` | lag-1 autocorrelation of `z` | 0.1926 | 0.092 to 0.293 |

**Fixed constants (not configurable).**

| Quantity | Value | Source |
| --- | --- | --- |
| Curve zero point | 32 C | [refit]: a free zero point is not identified |
| Carry-over reference | 44.84 C | mean previous same-spot temperature in the Dildine data [refit] |
| Drift and previous-stimulus reference | 45 C | [design] |
| Onset window | events 1 to 3 | the window `a` was fitted at [refit] |
| Visit cap on step and drift codings | visit 3 | the Dildine data and Jepma et al. (2014) measured 3 visits [read] |
| Stimulus | 8 s: 1.5 s rise from 32 C, 5 s at target, 1.5 s fall; enforced | Amir et al. (2022), Supplementary Materials [read] |
| Timing flag | onsets 26 to 30 s; revisits 156 to 180 s | [design] |
| Reporting window (`in_window`) | 40 to 49 C | [design] |
| Extrapolation flag | below 34 C or above 50 C | span of the Dildine data [refit] |
| Person-stream uniforms | 6 | determinism (section 3) |

## 6. Layer 1: the forearm person

A simulated person is a forearm fresh-skin pain threshold (the temperature at which their fresh-skin rating is 2) and a width (tolerance minus threshold, where tolerance is the temperature at which the fresh-skin rating is 8). The thenar person (section 10) and the curve shape (section 8) follow from these.

```
ln(T_thr - 32) = m1 + s1 g_alpha(z1)
ln W           = m2 + s2 (r z1 + sqrt(1 - r^2) z2)
T_tol          = T_thr + W
```

`z1`, `z2` are independent standard normal scores and `g_alpha` the standardised skew-normal quantile function. At `alpha` = 0 the model is a bivariate log-normal.

- **Why the log scale.** Every moment of threshold, width and exponent stays finite, and thresholds are bounded below by 32 C, the resting skin temperature and the curve's zero point.
- **Why the threshold is skewed.** The 125 forearm thresholds of Lotsch et al. (2026) are left-skewed (skewness -0.99 on ln(T - 32)) and reject the log-normal (Shapiro-Wilk p = 0.0001; AIC 17.0 worse than every alternative). The skew-normal on ln(T - 32) is within 1.3 AIC of the best family and keeps the lower bound at 32 C. Only the shape is taken from this source (`alpha` = -3.527, profile 95 percent interval -6.17 to -1.98); location and scale come from Layer 1b (section 7). The log-normal and the interval ends are carried as sensitivities.
- **Observed anchors.** Amir et al.'s (2022) anchors include 4 thresholds below 32 C and a maximum tolerance of 76.88 C; these are artefacts of a 24-trial regression, which the population cannot and should not produce.

## 7. Layer 1b: how the population was fitted

Amir et al.'s (2022) anchors are the output of a procedure: a staircase on 8 rotating forearm sites, a linear regression, and the participant's own session dynamics over 24 trials. Layer 1b separates the person's fresh-skin curve from the regression error and session dynamics by forward simulation. It is how `m1, s1, m2, s2, r` were estimated; it plays no part when the generator runs your protocol.

- **The emulator** reproduces Amir et al.'s calibration session: fixed opening temperatures (41, 44, 47 C), the documented regression rule rounded to 0.5 C and clipped to 36 to 50 C, a fixed target order recovered from the Dildine data, manual lowering, deviations resampled from the Dildine data, and ratings from the dynamics and noise of sections 11 and 13. It passes an in-sample adequacy test against the Dildine data (Mahalanobis distance 2.05 against a 95th percentile of 3.64).
- **The fit** matches eight statistics of the emulated anchors (a censored bivariate `t` description of the anchors, and the mean and SD of r-squared) to Amir et al.'s values, by indirect inference on samples of 342 people with a usable anchor. It was run 6 times on independent seeds and the mean adopted. 1.2 percent of the simulated population cannot produce a usable anchor.
- **Intervals** combine the data uncertainty with the spread between runs. They are approximate and conditional on the dynamics and noise estimates.
- **The tails do not match** (section 15, item 30): emulated anchors give 3.50 thresholds below 36 C per 342 people (Amir: 17) and 124.7 tolerances above 50 C (Amir: 71). These are reported, not tuned away.
- **Shape decision.** Through the emulator, Amir et al.'s anchors prefer a milder skew than the Lotsch et al. (2026) thresholds. A profile over `alpha` with rules fixed in advance puts the log-normal last under both weightings used, and adopts the external shape `alpha` = -3.527.

## 8. Layer 2: the static response curve

```
R(T) = 2 ((T - 32) / (T_thr - 32))^b,    b = ln 4 / ln((T_tol - 32) / (T_thr - 32))
```

`R(T_thr) = 2` and `R(T_tol) = 8` exactly. This is the expected rating on a spot's first visit, after the session's opening events, with the preceding stimulus at 45 C; every dynamic term in section 11 is a deviation from it.

- **Power law rather than linear.** By leave-one-trial-out cross-validation the power law predicts better than a straight line for 34 of 46 Dildine participants (p = 0.0016).
- **Zero point fixed at 32 C**; a free zero point is not identified. At and below 32 C, `R` = 0. Above tolerance the curve is uncapped; only `latent` and `observed` are clipped at 10.
- **One curve per region, shared by all three spots** (section 15, item 39).

## 9. Layer 3: reachability

Reachability is the share of simulated people whose temperature for a latent rating of 5 falls inside 40 to 49 C. It is a property of the population and the window, reported so results can be read in context; it is not a target. At the defaults, forearm reachability is 0.830 to 0.850 in every grid cell and thenar reachability 0.491 to 0.678 (it falls with the offset and under the LaMotte-scaled presets at visits 2 and 3). It depends only on the latent rating, so no noise parameter changes it. The tool does not compute it; it is reported here for context.

## 10. Layer 4: forearm to thenar

The thenar person is derived from the forearm person with three sourced quantities (`Delta`, `kappa`, `k_slope`) and two proxy correlations (`rho`, `rho_W`); see section 4, steps A2 to A6.

- **Offset `Delta`, default +0.5 C** (Hagander et al., 2000), the only source with both sites approximately matched (thenar against volar wrist). Taylor et al. (1993) and Eckert et al. (2017) give about +0.9 C with less well-matched sites, so +0.9 is co-primary. Hagander's ramp method and same-site repetition both bias the offset upward, so 0 is carried as a stress point under P3 and P4. No source measures the thenar against the mid-volar forearm in the same people with a contact thermode.
- **Spread ratio `kappa`, default 1.2**, the sample-size-weighted pool (1.203) of the ratios in Eckert et al. (2017), Taylor et al. (1993) and Hagander et al. (2000).
- **Slope ratio `k_slope`, default 0.92**, the ratio of forearm to hand gaps between slight and moderate pain thresholds in Taylor et al. (1993, Table 3); the sweep is its sampling interval.
- **Threshold correlation `rho`, default 0.75** (latent Pearson; Spearman 0.734). A labelled proxy from Lautenbacher and Rollman (1993); no direct estimate exists.
- **Width correlation `rho_W`, default 0.63.** Derived from the cross-side correlations of Schaffner et al. (2008), calibrated against the reliabilities in Amir et al. (2022) (threshold .66, tolerance .67, temperature-pain slope .23), which put the width correlation below the threshold correlation. The derived range is 0.543 to 0.724; `rho_W` = 1 reproduces the rule "thenar width = forearm width / k" exactly.
- **Thenar step `S_th` = -1.4628** (used by P3, P4, S2): the 2.3 C fresh-to-revisit threshold shift in LaMotte and Campbell (1978) converted to rating units at the median slope of the thenar curve at a rating of 2.

**Results at the defaults.** Thenar median threshold 43.34 C (43.72 C at `Delta` = +0.9); thenar tolerance above 49 C for 55.0 percent of people and above 52 C for 29.0 percent; forearm-thenar threshold Spearman 0.733.

## 11. Layer 5: within-session dynamics

All terms are on the 0 to 10 scale and are deviations from the fresh-skin curve (section 4, step B).

### 11.1 The matched coefficient set

One model fitted by least squares to all 1,104 Dildine trials on unclipped ratings, with a power-law curve and a revisit step for each person, and shared drift, carry-over, previous-stimulus and onset terms. Intervals are from a 300-replicate bootstrap over people.

| Term | Estimate | 95% interval |
| --- | --- | --- |
| Mean revisit step `S` | -0.2134 | -0.4283 to +0.0259 |
| Between-person step SD `sigma_S` | 0.6705 | 0.4095 to 0.8660 |
| Drift `gamma` | +0.0404 | -0.0188 to +0.1015 |
| Lag-1 carry-over `beta_1` | -0.0426 | -0.0967 to +0.0205 |
| Lag-2 carry-over `beta_2` | +0.0134 (default 0) | -0.0595 to +0.0920 |
| Previous stimulus `c` | +0.0880 | +0.0571 to +0.1284 |
| Onset `a` | -0.2374 | -0.2923 to -0.1810 |

Per-person steps differ more than estimation error allows (p = 3.3e-08), are consistent with a normal distribution, and are uncorrelated with the person's threshold. The lag-1 carry-over agrees with Jepma et al. (2014).

### 11.2 The visit-3 multiplier `m_step`

Visit 2 adds the person's step; visit 3 adds `m_step` times it. `m_step` = 1 would be a plateau, 2 linear in visit.

- The Dildine profile gives 1.431 (95 percent interval 1.075 to 2.062): it rejects the plateau (p = 0.013) and contains 2. The model-selection step in Jepma et al. (2014) also rejects the plateau and bounds `m_step` to about 1.41 to 3.44.
- **`m_step` is not swept.** Every other coefficient is estimated conditional on 1.43; at `m_step` = 2 the fitted `S` is -0.1503 and `sigma_S` 0.4755. Changing `m_step` alone runs a parameter vector no data support.
- In Jepma et al. (2014) the visit-3 shape depends on temperature; here it does not, because a temperature-dependent form did not predict held-out Dildine participants better (section 15, item 16).

### 11.4 The same-spot cap

The mean same-spot effect (step plus carry-over) is capped at 0: a cool previous stimulus can cancel habituation but not create sensitisation. The person's own deviation is added outside the cap, so individual sensitisers are kept. At the defaults the cap binds at visit 2 only for a previous same-spot visit below 39.83 C, so inside 40 to 49 C it does not bind; at the edges of the `S` and `beta_1` sweeps it can bind over much of the window.

### 11.5 Drift

The drift is `gamma (min(v, 3) - 1)(T - 45)`: zero at visit 1, then growing with visit. Jepma et al. (2014) found habituation at 41 to 47 C and sensitisation at 49 C; their stronger value, +0.0772, is the stress point.

### 11.6 Session onset

Ratings on the first three events are multiplied by `1 + a` = 0.7626. The effect is large at moderate and high ratings, the opposite of a clipping artefact. Limits: in the Dildine data the first three events were always a rising 41, 44, 47 C sequence, so the term cannot be separated from that order, and it may overstate the effect under a randomised opening (Jepma et al., 2014). LaMotte and Campbell (1978) found no early decrease on the thenar, which preset S3 represents.

### 11.7 The previous stimulus `c` and carry-over between regions

- `c` applies to every event after the first, per C of the previous event's temperature relative to 45 C, unless the previous event was at the same spot (then `beta_1` carries it). Within a region `tau` = 1: Jepma et al. (2014) found no effect of distance between successive sites.
- **Default +0.0880** (Dildine). Jepma et al.'s (2014) +0.035 lies outside the Dildine interval and is carried as a **co-primary** value: the two laboratories disagree. The Dildine gap between stimuli was about 13 s against 20 s in Jepma and in this protocol, and the Dildine data support (but cannot size) a decline of `c` with the gap.
- **Between regions there is no measurement**, so cross-region transfer `tau` is carried at 1 and 0 (presets P1 to P4) with one-direction stress presets (S1, S2).

### 11.8 Thenar same-spot dynamics

Two co-primary scenarios: the thenar uses the forearm step (P1, P2), or a LaMotte-scaled step `S_th` (P3, P4). The step SD stays at the absolute `sigma_S` by default; a proportional SD (4.5969) is the sensitivity. Under the absolute default, 1.5 percent of people have a positive thenar step under P3 and P4, against 37.5 percent on the forearm.

## 12. Scenario presets and the 15-cell reporting grid

| Preset | Thenar same-spot dynamics | `tau`, thenar to forearm | `tau`, forearm to thenar | Thenar onset |
| --- | --- | --- | --- | --- |
| P1 | equal to forearm | 1 | 1 | `a` |
| P2 | equal to forearm | 0 | 0 | `a` |
| P3 | LaMotte-scaled (`S_th`) | 1 | 1 | `a` |
| P4 | LaMotte-scaled (`S_th`) | 0 | 0 | `a` |
| S1 (stress) | equal to forearm | 1 | 0 | `a` |
| S2 (stress) | LaMotte-scaled (`S_th`) | 1 | 0 | `a` |
| S3 (stress) | equal to forearm | 1 | 1 | 0 |

Choose a preset in the **Scenario** panel of the Run and output tab; its description appears below the selector.

**The 15-cell primary grid.** Every result produced with this generator should be reported on these 15 cells. **A conclusion that changes across cells is reported as unresolved by the available evidence, not averaged.**

| Cell | Preset | `Delta` (C) | `c` |
| --- | --- | --- | --- |
| 1 | P1 | +0.5 | +0.0880 |
| 2 | P1 | +0.9 | +0.0880 |
| 3 | P2 | +0.5 | +0.0880 |
| 4 | P2 | +0.9 | +0.0880 |
| 5 | P3 | +0.5 | +0.0880 |
| 6 | P3 | +0.9 | +0.0880 |
| 7 | P4 | +0.5 | +0.0880 |
| 8 | P4 | +0.9 | +0.0880 |
| 9 | P1 | +0.5 | +0.0350 |
| 10 | P1 | +0.9 | +0.0350 |
| 11 | P3 | +0.5 | +0.0350 |
| 12 | P3 | +0.9 | +0.0350 |
| 13 | P3 | 0.0 | +0.0880 |
| 14 | P4 | 0.0 | +0.0880 |
| 15 | P3 | 0.0 | +0.0350 |

- P2 and P4 are not repeated over `c` because they set `tau` = 0 and, under the intended spot order, the previous event is always in the other region, so `c` never applies.
- `Delta` = 0 under P3 and P4 guards against counting thenar suppression twice (section 15, item 28).
- **Grid mode in the GUI.** Tick **Run the 15-cell reporting grid instead**. Every subject runs, with the same seed, in all 15 cells (runs `cell01` to `cell15`), so differences between cells come from the cell settings alone. Each cell sets the scenario, `Delta` and `c`; your own `Delta` or `c` overrides are replaced (a note is logged), and all other overrides apply to every cell. The preset selector is disabled while grid mode is on.

## 13. Layer 6: observation noise

The equations are in section 4, step C: a standard Student `t` innovation, a Gaussian-bump spread with a free peak, and AR(1) autocorrelation in event order across both regions.

- **Why the spread depends on the rating.** Ratings near the scale ends vary less than mid-scale ratings. The free-peak Gaussian was selected among seven shapes by leave-one-person-out predictive likelihood on the Dildine residuals.
- **Calibration.** Fitting a curve and step to each person distorts the residuals, so all six noise parameters were calibrated jointly by indirect inference, with 95 percent intervals from a 400-replicate bootstrap over people.
- **Derived values at the defaults.** `sigma` peaks at 1.6958 (rating 4.44); `sigma(0)` 0.3486, `sigma(2)` 0.7987, `sigma(5)` 1.6221, `sigma(8)` 0.4576, `sigma(10)` 0.3096. The marginal SD of the noise is `sigma(R) x 1.2321`: 1.9986 at a rating of 5.
- **Scale ends.** At 40 to 49 C many people exceed 10 on fresh forearm skin (1.5 percent at 45 C, 11.3 percent at 47 C, 37.5 percent at 49 C); their observed ratings sit at 10 with a small spread. A procedure keying on values at the scale ends will see this.
- The same noise process applies to both regions (section 15, item 21).

## 14. Open questions and how they are handled

Criteria were fixed before results were seen. **A conclusion that changes across the co-primary values of any open item is reported as unresolved by the available evidence, not averaged.**

**Tested and settled.**

| Item | Question | Outcome |
| --- | --- | --- |
| D1 | Visit-3 form | `m_step` = 1.43 (section 11.2) |
| D2 | Default `c` | +0.0880, with +0.035 co-primary (section 11.7) |
| D3 | Does constraining `c` to +0.035 move the other coefficients? | No (max shift 0.80 bootstrap SE) |
| D4 | Noise family | scaled `t` kept; a calibrated normal mixture fails the same tail check further out (section 15, item 29) |
| D5 | Population tails | do not match; registered (section 15, item 30) |
| D6 | Emulator adequacy | pass, in-sample (section 7) |
| D7 | Same-spot cap | binds on 2.85 percent of Dildine revisit trials; a refit with the cap was run and rejected, so the cap is applied at generation only |
| D8 | Curve form | power law (section 8) |
| D17 | Noise spread shape | free-peak Gaussian (section 13) |
| D18 | Threshold shape | skew-normal, `alpha_pop` = -3.527 (sections 6 and 7) |

**Open, carried as co-primary values or presets.**

| Item | Question | Values carried | Default | What would settle it |
| --- | --- | --- | --- | --- |
| D9 | Thenar offset `Delta` | +0.5 and +0.9 C (0 under P3, P4) | +0.5 | thenar and mid-volar forearm thresholds in the same people, first stimulus at fresh spots, 8 s contact waveform |
| D10 | Cross-region transfer `tau` | 1 and 0 | P1/P3: 1; P2/P4: 0 | a forearm-to-thenar previous-stimulus measurement in one session |
| D11 | Thenar same-spot dynamics | equal to forearm (P1/P2); LaMotte-scaled (P3/P4) | all four reported | per-person thenar revisit steps with a contact thermode |
| D12 | `rho_W` | 0.63; 0.75 and 1.0 as reference points | 0.63 | the threshold-tolerance correlation at two sites in the same people |
| D13 | Thenar step SD | absolute 0.6705 or proportional 4.5969 | absolute | per-person thenar revisit steps |
| D14 | Cross-region step correlation | fixed at 1 | 1 (not a parameter) | as D13 |
| D15 | `k_slope` sweep width | 0.56 to 1.27 or 0.67 to 1.17 | 0.56 to 1.27 | the hand-arm gap correlation in Taylor et al.'s per-person data |
| D16 | Threshold shape | skew-normal (adopted); log-normal and `alpha` interval ends as sensitivities | skew-normal | a fresh-skin threshold distribution measured with this protocol's first-stimulus design |

## 15. Assumptions and known limits

Items are numbered for stable reference; only items that bear on using the generator are listed.

**Known limits (also on the Reference tab).**
- **The thenar layer rests on proxies and scenarios** (D9 to D14; items 16, 28, 43): `Delta`, `tau` and the thenar dynamics are carried as co-primary values or presets.
- **The threshold shape** is set from independent data (Lotsch et al., 2026) that the anchors of Amir et al. (2022) only partly support (item 30, D18). `alpha_pop` = 0 and the interval ends -6.17 and -1.98 are the sensitivities.
- **The fresh-skin upper tails are heavy** (item 48): the threshold 99th percentile (51.14 C) is above any deliverable stimulus, and 1.2 percent of people could not produce a usable anchor.
- **The noise far tail is lighter in the data than in the `t`** (item 29); the spread has unmodelled structure near the middle of the scale (item 47).
- **`c` is applied at a longer gap than it was fitted at** (item 38); +0.035 is co-primary.
- **The visit-3 multiplier does not depend on temperature here**, though the data of Jepma et al. (2014) say it does (item 16); visits beyond the third are flagged.

**Selected assumption items.**

| # | Assumption | Status |
| --- | --- | --- |
| 3 | The 0 to 10 scale is an interval scale | convention |
| 8 | Thenar offset, spread and slope ratio transfer from studies with different sites and methods | open gap |
| 9 | The forearm-thenar threshold correlation is a proxy | open gap |
| 13 | The forearm-thenar width correlation is derived, not measured | open gap, swept 0.3 to 1.0 |
| 15 | Same-spot coefficients apply at a 168 s revisit | bounded: the Dildine revisit was about 165 to 180 s |
| 16 | Thenar same-spot dynamics, and the visit-3 form | open gap, handled by presets; Jepma et al. (2014) and the Dildine data disagree on how `m_step` varies with temperature |
| 17 | Carry-over between forearm and thenar | open gap, handled by presets |
| 18 | Session onset applies to both regions | open gap; S3 removes it on the thenar |
| 19 | Visits beyond three | outside the measured range, flagged |
| 21 | One noise process for both regions, correlated across them | open gap |
| 24 | One person, one session | scope |
| 28 | The thenar offset may already contain revisit suppression, so P3 and P4 may count it twice | open gap; `Delta` = 0 cells in the grid |
| 29 | The residuals' far tail is lighter, relative to their shoulder, than the `t` (and than a normal mixture) | open, registered |
| 30 | The emulated anchor tails miss Amir et al.'s (2022): too few low thresholds, too many tolerances above 50 C | open, registered |
| 32 | The onset term was fitted on a fixed rising opening | open gap; may overstate under a randomised opening |
| 33 | The same-spot cap is imposed on a model fitted without it | convention, checked (D7) |
| 35 | The previous-stimulus term is constant across the session | open gap |
| 37 | The drift is linear in temperature | bounded; Jepma et al.'s (2014) quadratic term is not implemented |
| 38 | `c` is applied at a longer gap than it was fitted at | bounded, direction known: the default may overstate `c` |
| 39 | All three spots in a region share one curve | convention, supported by Schaffner et al. (2008) |
| 43 | The thenar between-person step SD is unsourced | open gap, both candidates reported |
| 47 | A single-peak spread leaves a residual misfit near ratings 4 to 6 | open gap |
| 48 | The fresh-skin upper tails are heavy | open gap |

## 16. Validation checks

Checks 8 to 10 test the generator itself and run in the tool; the others concern the population and the fitted parameters and were computed when the parameters were derived.

| # | Check | Where | Result |
| --- | --- | --- | --- |
| 1 | Person marginals against the observed anchors | derivation | reported |
| 2 | Anchor recovery: `R(T_thr) = 2`, `R(T_tol) = 8` | derivation | pass |
| 3 | Exponent distribution | derivation | reported; upper tail heavy (item 48) |
| 4 | Reachability on the 15-cell grid | derivation | section 9 |
| 5 | Boundary diagnostic | derivation | pass |
| 6 | Thenar layer | derivation | section 10 |
| 7 | Noise marginal SD and autocorrelation | derivation | pass |
| **8** | **Dynamics unit tests (28 tests)** | **this tool** | **pass** |
| **9** | **Determinism and common random numbers (9 tests)** | **this tool** | **pass** |
| **10** | **Flags and input handling (12 tests)** | **this tool** | **pass** |
| 11 | Every derived number reproduces | derivation | pass |
| 12 | Cap binding in the source data | derivation | 2.85 percent (D7) |
| 13 | Emulator adequacy | derivation | pass, in-sample |
| 14 | Thenar curve shape near threshold | derivation | reported |
| 15 | Projection diagnostics | derivation | reported |
| 16 | Visit-3 multiplier | derivation | section 11.2 |
| 17 | The spread function needs no clamp | derivation | pass |
| 18 | Noise family tail statistics | derivation | **fails** on the 99th/90th percentile ratio (item 29) |
| 19 | `c` constrained to +0.035 | derivation | max shift 0.80 SE (D3) |
| 20 | `c` against the gap between stimuli | derivation | section 11.7 |

**In the GUI.**
- **Run self-tests (checks 8 to 10)** runs all 49 tests on the embedded generator and logs "49 of 49 pass" or each failure. Examples: a first visit carries no step, drift or history; a second visit at 45 C after 44.84 C carries exactly `S`; the cap binds for a prior visit at 35 C; under P2 and P4 a previous thenar stimulus adds nothing to a forearm event; the same seed gives identical output; changing thenar parameters leaves forearm ratings identical; a fourth visit sets `beyond_measured_visits`; onsets 31 s apart set `off_protocol_timing` and 29 s apart do not; a duration other than 8 s raises.
- **Replay golden vectors...** replays `golden_vectors.json`, the 75 reference cases produced by the reference implementation, and logs the number of cases, the maximum numeric difference and whether every flag matches. PASS requires a difference of exactly 0. Different numpy or scipy versions can give tiny differences; up to 1e-6 is acceptable.

## 17. References

Amir, C., Rose-McCandlish, M., Weger, R., Dildine, T. C., Mischkowski, D., Necka, E. A., Lee, I.-S., Wager, T. D., Pine, D. S., & Atlas, L. Y. (2022). Test-retest reliability of an adaptive thermal pain calibration procedure in healthy volunteers. *The Journal of Pain, 23*(9), 1543-1555. https://doi.org/10.1016/j.jpain.2022.01.011

Dildine, T. C., & Atlas, L. Y. (n.d.). *[Unpublished heat pain rating dataset, with readme]* [Data set]. Confidence Database. https://osf.io/s46pr

Dildine, T. C., Necka, E. A., & Atlas, L. Y. (2020). Confidence in subjective pain is predicted by reaction time during decision making. *Scientific Reports, 10*(1), Article 21373. https://doi.org/10.1038/s41598-020-77864-8

Eckert, N. R., Vierck, C. J., Simon, C. B., Cruz-Almeida, Y., Fillingim, R. B., & Riley, J. L. (2017). Testing assumptions in human pain models: Psychophysical differences between first and second pain. *The Journal of Pain, 18*(3), 266-273. https://doi.org/10.1016/j.jpain.2016.10.019

Evans, D. W., Frowen, V., & Mansfield, M. (2026). Repeated heat pain threshold testing in pain-free individuals induces habituation and yields false-positive pre-post comparisons. *Scientific Reports, 16*(1), Article 26806. https://doi.org/10.1038/s41598-026-61723-z

Hagander, L. G., Midani, H. A., Kuskowski, M. A., & Parry, G. J. (2000). Quantitative sensory testing: Effect of site and skin temperature on thermal thresholds. *Clinical Neurophysiology, 111*(1), 17-22. https://doi.org/10.1016/s1388-2457(99)00192-3

Jepma, M., Jones, M., & Wager, T. D. (2014). The dynamics of pain: Evidence for simultaneous site-specific habituation and site-nonspecific sensitization in thermal pain. *The Journal of Pain, 15*(7), 734-746. https://doi.org/10.1016/j.jpain.2014.02.010

LaMotte, R. H., & Campbell, J. N. (1978). Comparison of responses of warm and nociceptive C-fiber afferents in monkey with human judgments of thermal pain. *Journal of Neurophysiology, 41*(2), 509-528. https://doi.org/10.1152/jn.1978.41.2.509

Lautenbacher, S., & Rollman, G. B. (1993). Sex differences in responsiveness to painful and non-painful stimuli are dependent upon the stimulation method. *Pain, 53*(3), 255-264. https://doi.org/10.1016/0304-3959(93)90221-A

Lotsch, J., Fluhr, K., & Neddermeyer, T. J. (2026). *Quantitative sensory testing dataset with capsaicin and menthol sensitization assessing modality-specific sex differences and sensitization effect sizes in 125 healthy volunteers* (Version 2) [Data set]. Mendeley Data. https://doi.org/10.17632/y6v3rtpgps.2

Mischkowski, D., Stavish, C. M., Palacios-Barrios, E. E., Banker, L. A., Dildine, T. C., & Atlas, L. Y. (2021). Dispositional mindfulness and acute heat pain: Comparing stimulus-evoked pain with summary pain assessment. *Psychosomatic Medicine, 83*(6), 539-548. https://doi.org/10.1097/PSY.0000000000000911

Schaffner, N., Wittwer, A., Kut, E., Folkers, G., Benninger, D. H., & Candia, V. (2008). Heat pain threshold and tolerance show no left-right perceptual differences at complementary sites of the human forearm. *Neuroscience Letters, 440*(3), 309-313. https://doi.org/10.1016/j.neulet.2008.05.084

Taylor, D. J., McGillis, S. L. B., & Greenspan, J. D. (1993). Body site variation of heat pain sensitivity. *Somatosensory & Motor Research, 10*(4), 455-465. https://doi.org/10.3109/08990229309028850

---

## Appendix A. Output files

Set the folder, file prefix (default `heat_pain`) and options in the **Output** panel of the Run and output tab. Files are named `<prefix>_<name>`.

| File | Written | Contents |
| --- | --- | --- |
| `<prefix>_manifest.json` | always | tool and generator versions; UTC time; Python, numpy, scipy and matplotlib versions; the full configuration; effective parameters per run; the run list; the seed derivation; every subject seed; notes; files written; the usage rules |
| `<prefix>_events.csv` | if ticked | one row per subject, run and event: `subject, subject_seed, run, cell, scenario, Delta, c, event, t_s, region, spot, temp_c, visit, latent, observed`, optionally `raw, z`, then the four flags |
| `<prefix>_persons.csv` | if ticked | one row per subject, run and region, fresh-skin values: `threshold_c, tolerance_c, width_c, exponent, zero_point_c, T_at_rating_5_c, step_mean, step_sd, step_person, step_variate` |
| `<prefix>_summary.csv` | if ticked | by run, region and visit (4 and later pooled as `4+`): counts; mean, SD, median, 5th and 95th percentile of `latent` and `observed`; share of each flag |
| `<prefix>_rating_vs_temperature.csv` | if ticked | by run, region and delivered temperature: counts, visits present, and the same statistics |
| `<prefix>_rating_vs_temperature_<run>.<png, pdf or svg>` | if the plot is ticked and matplotlib is installed | one figure per run (`single`, or `cell01` to `cell15`): forearm and thenar panels with each event's rating against delivered temperature, the median at each temperature, optional fresh-skin curves for the first K subjects, the 40 to 49 C window and the 2 / 5 / 8 anchors |

Plot options: ratings shown (both, observed or latent), format, DPI (20 to 1200), and the number of fresh-skin curves. Floats are written in shortest round-trip form and booleans as `true` / `false`. Summary tables pool subjects within a run; for grid runs, compare cells rather than pooling across them.

After each run the log lists the files written, the count of each flag, and per region the latent median and the share of latent ratings at 0 and at the top of the scale.

## Appendix B. Seeding and reproducibility

- **One person per seed.** For N subjects, subject *i* (counted from 0) receives
  `int(numpy.random.SeedSequence(entropy=base_seed, spawn_key=(i,)).generate_state(1, numpy.uint64)[0]) >> 15`,
  the top 49 bits of the first 64-bit word, so every seed has at most 15 digits and survives spreadsheets that keep 15 significant digits.
- A subject's seed depends only on the base seed and *i*, not on N: running 10 or 1,000 subjects from the same base seed gives the same first 10 people, and different base seeds do not share subjects.
- Each person then uses two streams: person `numpy.random.default_rng([seed, 0]).random(6)`; noise `numpy.random.default_rng([seed, 1])`, one uniform per event. Every uniform is clipped to [1e-12, 1 - 1e-12] before an inverse CDF.
- In grid mode every subject keeps the same seed in every cell.
- Every subject seed is written to the outputs, so any single person can be regenerated with `Generator(seed)`.
- **Saving and reloading.** File > Save configuration writes the seed, subjects, scenario, grid mode, parameter overrides, events and output options as JSON. File > Load configuration or manifest accepts either a saved configuration or a run manifest, and reproduces the run exactly on the same numpy and scipy versions. Unknown parameter keys or scenarios in a loaded file are refused.

## Appendix C. Using the module from Python

The module imports without tkinter; no window opens.

```python
import heat_pain_gui as H

# One person, one session
g = H.Generator(seed=12345, params={"c": 0.035}, scenario="P3")
events = [H.ev(28.0 * i, *H.INTENDED_ORDER[i % 6], 45.0) for i in range(18)]
out = g.simulate(events)      # list of dicts: latent, observed, raw, z and the four flags
anchors = g.person()          # fresh-skin threshold, tolerance, exponent and steps per region

# A batch run, as the GUI does it
cfg = H.default_config()
cfg.update(seed=1, n_subjects=200, grid_mode=True, events=events)
cfg["output"].update(directory="out", prefix="study1")
errors, notes = H.validate_config(cfg)
res = H.run_batch(cfg)
files, rows = H.write_outputs(res)

# Checks 8 to 10 and the reference cases
results = H.run_unit_tests()
n_cases, max_diff, flags_ok = H.replay_golden("golden_vectors.json")

# Reproduce a run from its manifest
cfg2 = H.load_config("out/study1_manifest.json")
```

Other helpers: `H.subject_seeds(base_seed, n)`, `H.build_template(n, start_s, interval_s, order_text, temps_text)`, `H.read_events_csv(path)`, `H.write_events_csv(path, events)`, `H.check_params(overrides, scenario)`, `H.check_events(events)`.
