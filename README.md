# Heat-pain rating generator: configuration GUI (`heat_pain_gui.py`)

Tool version 1.0. Implements the heat-pain rating generator build specification v2.8 (generator `__version__` "2.8").

`heat_pain_gui.py` produces seeded, reproducible simulated pain ratings on the 0 to 10 scale for a batch of simulated people, from an event list that you supply (onset time, body region, spot, target temperature). It is meant for scoring calibration procedures against a known ground truth: every event returns a noise-free `latent` rating (the scoring target) and a noisy `observed` rating (what a procedure is allowed to see). The file contains the generator, a batch runner with exporters, and a tkinter GUI.

**Section numbering.** Throughout this README, "spec section N" refers to the numbered sections of *Heat-pain rating generator v2.8: build specification*, using the same numbers the GUI shows (for example the "Parameters (spec section 5)" tab and the "Scenario (spec section 12)" panel). "Contract N" refers to the seven contracts in spec section 3, "register item N" to the assumption register in spec section 15, "check N" to the validation checks in spec section 16, and "D-numbers" to the decision rules in spec section 14. "Implementation guide section N" refers to the separate implementation guide in the specification package.

---

## Contents

1. [Requirements](#requirements)
2. [Running the tool](#running-the-tool)
3. [Scope (spec section 1)](#scope-spec-section-1)
4. [The rating scale (spec section 2)](#the-rating-scale-spec-section-2)
5. [The generator (spec sections 3 and 4)](#the-generator-spec-sections-3-and-4)
6. [Seeding and reproducibility](#seeding-and-reproducibility)
7. [Using the GUI](#using-the-gui)
8. [Parameters (spec section 5)](#parameters-spec-section-5)
9. [Scenario presets and the 15-cell reporting grid (spec section 12)](#scenario-presets-and-the-15-cell-reporting-grid-spec-section-12)
10. [Output files](#output-files)
11. [Validation (spec section 16)](#validation-spec-section-16)
12. [Using the module without the GUI](#using-the-module-without-the-gui)
13. [Rules that come with the generator](#rules-that-come-with-the-generator)
14. [Known limits (spec sections 14 and 15)](#known-limits-spec-sections-14-and-15)
15. [References](#references)

---

## Requirements

| Package | Needed for | Notes |
| --- | --- | --- |
| Python 3.9 or later | everything | |
| numpy | everything | |
| scipy | everything | |
| tkinter | the GUI only | Standard library, but packaged separately on some Linux and conda Pythons (e.g. `sudo apt install python3-tk`, `brew install python-tk`, or the python.org installer) |
| matplotlib | the rating-vs-temperature plot only | Optional. Without it the plot checkbox is disabled and everything else works |

```bash
pip install numpy scipy matplotlib
```

Bit-identical output to the reference implementation (and to the golden vectors) is only guaranteed on the same numpy and scipy versions; the manifest of every run records them.

## Running the tool

```bash
python heat_pain_gui.py
```

If tkinter is missing, the script exits with installation instructions. The module can also be imported without tkinter (`import heat_pain_gui as H`); the generator, batch runner and exporters are then available and no window opens (see [Using the module without the GUI](#using-the-module-without-the-gui)).

### File layout

The single file is organised in four parts:

| Part | Contents |
| --- | --- |
| PART 1 | The generator, copied verbatim from the v2.8 reference implementation (`heat_pain_generator.py`): sources, fixed constants, full-precision defaults, scenario presets, the skew-normal threshold shape, the `Generator` class, and the 49 unit tests of checks 8 to 10. Nothing in PART 1 was edited; its output is bit-identical to the reference on all 75 golden vectors. |
| PART 2 | Interface metadata: parameter meanings, sweeps and sources (spec section 5), scenario descriptions and the 15-cell grid (spec section 12), fixed constants, the default test event sequence. |
| PART 3 | The batch runner and exporters (no GUI): subject seeds, validation, runs, tables, plots, manifest, configuration save and load, golden-vector replay. |
| PART 4 | The tkinter GUI. |

## Scope (spec section 1)

The generator answers one question: given a simulated person, a spot, a target temperature and the session history, what rating would be recorded?

**In scope.** Six spots per simulated session (three on the left volar forearm, three on the left thenar eminence); between-person variation in heat-pain sensitivity and habituation; a latent and an observed rating for every event; within-session change driven by same-spot history, the immediately preceding stimulus and position in the session.

**Out of scope.** Calibration procedures, stopping rules, target definitions and scoring; the choice of temperatures, spot order and timing (these are caller inputs); hardware; any second session. This tool applies one fixed, caller-supplied event list to every subject.

**Population.** Healthy, first-session, test-naive adults aged 18 to 50 under the inclusion criteria of Amir et al. (2022).

**Validity envelope.** Any event list is accepted. The parameters were estimated under the conditions below; events outside them are evaluated and flagged, never refused or clamped (contract 4).

| Property | Value the parameters assume |
| --- | --- |
| Stimulus | 8 s: 1.5 s rise from 32 C, 5 s at target, 1.5 s fall (enforced, contract 6) |
| Onset to onset | 28 s (tolerance 26 to 30 s) |
| Same-spot revisit | 168 s (tolerance 156 to 180 s) |
| Visits per spot | at most 3 |
| Temperature | 34 to 50 C (reporting window 40 to 49 C) |

The intended spot order (forearm 1, thenar 1, forearm 2, thenar 2, forearm 3, thenar 3, repeating) with onsets every 28 s puts every revisit at 168 s. It is a caller choice, not a requirement.

## The rating scale (spec section 2)

All values are on the 0 to 10 scale used by every source: 0 no sensation, 1 warmth but not pain, 2 pain threshold, 5 moderate pain, 8 pain tolerance, 10 most pain imaginable (Amir et al., 2022; Mischkowski et al., 2021).

The GUI offers a **0 to 100** output option. Per spec section 2, a caller working on 0 to 100 multiplies `latent` and `observed` by 10 and no parameter changes. The tool also multiplies the diagnostic `raw` by 10 for consistency. `z` and all temperatures are unchanged.

## The generator (spec sections 3 and 4)

`Generator(seed, params=None, scenario="P1")` draws one simulated person at construction and exposes `simulate(events, duration_s=8.0)`, `reset()` and `person()`.

**Input event fields** (spec section 3):

| Field | Type | Meaning |
| --- | --- | --- |
| `t_s` | float | onset time in seconds from session start, non-decreasing |
| `region` | `"forearm"` or `"thenar"` | any other value raises |
| `spot` | 1, 2 or 3 | any other value raises |
| `temp_c` | float | target temperature (C) |

**Output fields**, one record per event:

| Field | Meaning |
| --- | --- |
| `latent` | `clip(R_raw, 0, 10)`, the expected rating with no noise. **The scoring target.** |
| `observed` | `clip(R_raw + sigma(R_raw) z, 0, 10)`, the rating a procedure may see |
| `raw` | diagnostic: the unclipped `R_raw` |
| `z` | diagnostic: the standardised noise value |
| `in_window` | 40 <= `temp_c` <= 49 |
| `extrapolated` | `temp_c` < 34 or `temp_c` > 50 |
| `beyond_measured_visits` | fourth or later visit to a spot |
| `off_protocol_timing` | onset gap outside 26 to 30 s, or revisit interval outside 156 to 180 s |

**How a rating is built** (spec section 4, summarised; the specification is normative):

- **Step A, the person.** Six uniforms from the person stream give a forearm threshold and width (skew-normal log threshold, normal log width, Gaussian copula; spec section 6), a thenar threshold and width derived through `Delta`, `kappa`, `k_slope`, `rho` and `rho_W` (spec section 10), and one step variate shared by both regions. Each region's fresh-skin curve is a power law through rating 2 at threshold and rating 8 at tolerance, zero at 32 C (spec section 8).
- **Step B, the dynamics.** The fresh-skin rating is multiplied by the onset factor `1 + a` on events 1 to 3, then adjusted by the capped same-spot step and carry-over, the person's own step deviation, the drift, and the previous-stimulus term `c` scaled by the scenario's cross-region `tau` (spec section 11).
- **Step C, the noise.** One uniform per event gives a Student `t` innovation, made AR(1) across both regions with `phi`, and scaled by a Gaussian-bump spread `sigma(R)` evaluated at the unclipped `R_raw` (spec section 13).
- **Step D, the flags.**

**The seven contracts** (spec section 3): (1) determinism through two seeded streams; (2) the person never changes and `reset()` replays the same session counterfactually; (3) common random numbers, every random quantity an inverse CDF of one uniform; (4) inputs are never clamped; (5) `latent` is the scoring target and `observed` is what a procedure may see; (6) stimulus duration is fixed at 8 s; (7) `params` overrides any single key of the parameter table and an unrecognised key or scenario raises.

## Seeding and reproducibility

- **One person per seed** (contract 1). For N subjects, subject *i* (0-based) receives
  `int(numpy.random.SeedSequence(entropy=base_seed, spawn_key=(i,)).generate_state(1, numpy.uint64)[0]) >> 15`,
  the top 49 bits of the first 64-bit word, so every seed has at most 15 digits and survives spreadsheets that keep 15 significant digits.
- A subject's seed depends only on the base seed and *i*, not on N. Running 10 or 1,000 subjects from the same base seed gives the same first 10 people, and different base seeds do not share subjects.
- Each `Generator` then uses the reference's two streams: person `numpy.random.default_rng([seed, 0]).random(6)`; noise `numpy.random.default_rng([seed, 1])`, one uniform per event.
- In grid mode every subject keeps the same seed in every cell (common random numbers, contract 3), so differences between cells are caused by the cell's settings alone.
- Every subject seed is written to the outputs, so any single person can be regenerated with `Generator(seed)`.
- The manifest records the full configuration, every effective parameter, every subject seed and the Python, numpy, scipy and matplotlib versions. Loading a manifest (File > Load configuration or manifest) reproduces the run exactly on the same library versions.

## Using the GUI

The window has a File menu and four tabs.

**File menu.** Load configuration or manifest; Save configuration (JSON, schema `heat_pain_gui.config/1`); Reset everything to defaults; Quit.

### Tab 1: Run and output

- **Subjects and seed.** Base seed (non-negative integer) and number of subjects (integer >= 1).
- **Scenario (spec section 12).** Choose a preset (P1 to P4, S1 to S3); its description appears below. Tick **Run the 15-cell reporting grid instead** to run every subject, with the same seeds, in all 15 cells. In grid mode the preset selector is disabled, and each cell sets the scenario, `Delta` and `c`; any override you made to `Delta` or `c` is replaced in every cell (a note is logged), while your other parameter overrides apply to every cell.
- **Output.** Folder, file prefix (default `heat_pain`), rating scale (0 to 10, or 0 to 100), which CSV tables to write, whether to include the diagnostic columns `raw` and `z`, and the optional plot (ratings shown: both, observed or latent; format png, pdf or svg; DPI 20 to 1200; fresh-skin curves for the first K subjects). A manifest is always written.
- **Actions.** **Generate** runs in a background thread with a progress bar and a **Cancel** button (a cancelled run writes no files). If output files already exist you are asked before they are overwritten. **Run self-tests (checks 8 to 10)** and **Replay golden vectors...** are described under [Validation](#validation-spec-section-16).
- **Log.** Library versions on start-up; for each run, the configuration, notes on out-of-sweep values, the files written, flag counts and the latent median and share at the scale ends per region.

### Tab 2: Parameters (spec section 5)

Every parameter of spec section 5, grouped by layer, with its key, editable full-precision value, a **Default** button, the printed default, meaning, sweep and source. Changed keys are shown in red and counted at the top; **Reset all parameters to defaults** restores them.

- `a_th` and `sigma_S_th` have an **unset** checkbox. Unset (the default) means `a_th` equals `a` and `sigma_S_th` equals `sigma_S`. Unticking fills a starting value (0 for `a_th`, 4.5969 for `sigma_S_th`, the reference points in spec section 5).
- `m_step` carries a hover note: it is not swept (spec section 11.2), because every other coefficient is estimated conditional on 1.43, so changing it alone runs a parameter vector no data support.
- **Values outside the spec's sweep are allowed** and noted in the log as a labelled sensitivity outside the evidence. **Values the equations cannot evaluate are refused at Generate**: non-finite values; `s1`, `s2`, `kappa`, `k_slope` or `nu` <= 0; `w` = 0; a correlation (`r`, `rho`, `rho_W`, `phi`) outside [-1, 1]; a covariance that is not positive definite (|`r`| = 1 or |`rho`| = 1); or a person draw that is not finite.

### Tab 3: Stimulus events

The event list is your protocol (spec section 3) and is applied to every subject.

- **Edit.** Add event (continues the intended spot order at +28 s), Delete selected, Move up, Move down, Clear. Double-click a cell to edit `t_s`, `region`, `spot` or `temp_c`.
- **Build from template.** Number of events, first onset, onset-to-onset interval, a cycled spot order (e.g. `F1, T1, F2, T2, F3, T3`; also accepts `forearm 1`, `thenar-2`), and either one temperature for all events or exactly one per event. Defaults reproduce the intended order and timing: 18 events every 28 s, every revisit at 168 s, 3 visits per spot.
- **Load test sequence.** The 18-event sequence used to build the golden vectors (`make_golden.py`). It is a test sequence, not a recommended protocol.
- **Import CSV / Export CSV.** Columns `t_s, region, spot, temp_c` with a header row; other columns are ignored.
- **Flag preview.** The "will be flagged" column shows, before you run, which events will be outside 40 to 49 C, extrapolated, beyond the third visit, or off the 26 to 30 s / 156 to 180 s timing. Onset times must be non-decreasing; an event list that violates this is refused at Generate.

### Tab 4: Reference

Read-only text: the scenario presets, the 15-cell grid, the fixed constants, the output fields, the rules and known limits, and the sources.

## Parameters (spec section 5)

Defaults are printed to four or five decimals; the tool carries the full-precision values. Provenance tags (spec preamble): **[read]** taken from a cited source; **[refit]** computed by `refit.py` from the Amir, Dildine or Lotsch data; **[model]** follows by construction or arithmetic; **[design]** a protocol choice.

**Person population (Layer 1, spec section 6).** Fitted by the Layer 1b inference stage (spec section 7) on the visit-1 anchors of Amir et al. (2022); shape from Lotsch et al. (2026).

| Key | Meaning | Default | Sweep | Source |
| --- | --- | --- | --- | --- |
| `m1` | mean of ln(T_thr - 32), forearm fresh skin | 2.33030 | 2.2731 to 2.3875 (approximate conditional interval) | Layer 1b [refit] |
| `s1` | SD of ln(T_thr - 32) | 0.35514 | 0.3037 to 0.4066 | Layer 1b [refit] |
| `m2` | location of ln W (W = tolerance - threshold) | 1.62249 | 1.5290 to 1.7160 | Layer 1b [refit] |
| `s2` | scale of ln W | 0.50008 | 0.4129 to 0.5873 | Layer 1b [refit] |
| `r` | Gaussian-copula correlation of ln(T_thr - 32) and ln W | -0.81198 | -0.8849 to -0.7390 | Layer 1b [refit] |
| `alpha_pop` | skew-normal shape of ln(T_thr - 32), both regions (0 is log-normal) | -3.5272 | -6.17 to -1.98; 0 as a reference | Lotsch et al. (2026) [refit] |

**Forearm to thenar (Layer 4, spec section 10).**

| Key | Meaning | Default | Sweep | Source |
| --- | --- | --- | --- | --- |
| `Delta` | thenar threshold offset at the median (C) | +0.5 | co-primary +0.5 and +0.9; stress +1.6; 0 under P3 and P4 (grid cells) | Hagander et al. (2000); Taylor et al. (1993); Eckert et al. (2017) [read] |
| `kappa` | thenar-to-forearm threshold spread ratio at the median | 1.2 | 1.04 to 1.37; stress 1.50 | Eckert et al. (2017); Taylor et al. (1993); Hagander et al. (2000) [read]; pool [model] |
| `k_slope` | slope ratio; thenar width = forearm width / k at the median | 0.92 | 0.56 to 1.27 | Taylor et al. (1993), Table 3 [read]; interval [model] |
| `rho` | forearm-thenar log-threshold correlation (latent Pearson) | 0.75 | 0.3 to 0.9 | Lautenbacher & Rollman (1993), proxy [read] |
| `rho_W` | forearm-thenar log-width correlation | 0.63 | 0.3 to 1.0; reference points 0.75 and 1.0 | Schaffner et al. (2008) with the ICCs of Amir et al. (2022) [read], [model] |

**Within-session dynamics (Layer 5, spec section 11).** Fitted on the Dildine and Atlas dataset (n.d.; study described in Dildine et al., 2020), checked against Jepma et al. (2014).

| Key | Meaning | Default | Sweep | Source |
| --- | --- | --- | --- | --- |
| `S` | mean revisit step, forearm (rating units) | -0.2134 | -0.4283 to +0.0259 | Dildine matched set [refit] |
| `sigma_S` | between-person step SD, absolute, both regions | 0.6705 | 0.4095 to 0.8660 | [refit] |
| `m_step` | step multiplier at visit 3 and later | 1.43 | not swept (spec section 11.2) | Dildine profile [refit]; inside the bound from Jepma et al. (2014) [read], [model] |
| `gamma` | drift per C of (T - 45) per drift unit (0, 1, 2) | +0.0404 | -0.0188 to +0.1015; stress +0.0772 | [refit]; stress from Jepma et al. (2014) [read] |
| `beta_1` | lag-1 same-spot carry-over per C of (T_1 - 44.84) | -0.0426 | -0.0967 to +0.0205 | [refit]; Jepma et al. (2014) value -0.0679 lies inside |
| `beta_2` | lag-2 same-spot carry-over per C of (T_2 - 44.84) | 0 | -0.0595 to +0.0920 (fitted +0.0134) | [refit] |
| `c` | previous stimulus per C of (T_prev - 45) | +0.0880 | +0.0571 to +0.1284; co-primary +0.035 outside the sweep | [refit]; co-primary from Jepma et al. (2014) [read] |
| `a` | proportional onset term, events 1 to 3 (factor 0.7626) | -0.2374 | -0.2923 to -0.1810 | [refit] |
| `a_th` | thenar onset term; unset means equal to `a` | unset | 0 under S3 | LaMotte & Campbell (1978) [read] |
| `S_th` | thenar mean step under P3, P4, S2 | -1.4628 | -1.909 to -1.142 | LaMotte & Campbell (1978), converted [read], [model] |
| `sigma_S_th` | thenar step SD under P3, P4, S2; unset means equal to `sigma_S` | unset | proportional sensitivity 4.5969 | register item 43 [model] |

**Observation noise (Layer 6, spec section 13).** All six calibrated jointly by indirect inference on the Dildine and Atlas dataset.

| Key | Meaning | Default | Sweep |
| --- | --- | --- | --- |
| `nu` | Student `t` innovation degrees of freedom (not rescaled) | 5.8603 | 2.673 to 9.047 |
| `s0` | asymptotic spread away from the peak | 0.3031 | 0.112 to 0.494 |
| `s1n` | peak spread increment (distinct from the population's `s1`) | 1.3927 | 0.997 to 1.788 |
| `w` | width of the spread bump (rating units) | 1.6975 | 1.390 to 2.005 |
| `peak` | rating at which the spread peaks | 4.4402 | 4.192 to 4.688 |
| `phi` | lag-1 autocorrelation of `z`, in event order across regions | 0.1926 | 0.092 to 0.293 |

**Fixed constants (spec section 5; not configurable).**

| Quantity | Value | Source |
| --- | --- | --- |
| Curve zero point | 32 C | [refit]: a free zero point is not identified |
| Carry-over reference | 44.84 C | mean previous same-spot temperature in the Dildine and Atlas dataset [refit] |
| Drift and previous-stimulus reference | 45 C | [design] |
| Onset window | events 1 to 3 | the window `a` was fitted at [refit] |
| Visit cap on step and drift codings | visit 3 | Dildine and Jepma et al. (2014) each measured 3 visits [read] |
| Stimulus | 8 s: 1.5 s rise from 32 C, 5 s at target, 1.5 s fall; enforced (contract 6) | Amir et al. (2022), Supplementary Materials [read] |
| Timing flag | onsets 26 to 30 s; revisits 156 to 180 s | [design] |
| Reporting window (`in_window`) | 40 to 49 C | [design] |
| Extrapolation flag | below 34 C or above 50 C | span of the Dildine and Atlas dataset [refit] |
| Person-stream uniforms | 6 | contract 1 |

## Scenario presets and the 15-cell reporting grid (spec section 12)

| Preset | Thenar same-spot dynamics | `tau` thenar to forearm | `tau` forearm to thenar | Thenar onset |
| --- | --- | --- | --- | --- |
| P1 | equal to forearm | 1 | 1 | `a` |
| P2 | equal to forearm | 0 | 0 | `a` |
| P3 | LaMotte-scaled (`S_th`) | 1 | 1 | `a` |
| P4 | LaMotte-scaled (`S_th`) | 0 | 0 | `a` |
| S1 (stress) | equal to forearm | 1 | 0 | `a` |
| S2 (stress) | LaMotte-scaled (`S_th`) | 1 | 0 | `a` |
| S3 (stress) | equal to forearm | 1 | 1 | 0 |

"LaMotte-scaled" refers to the thenar step derived from LaMotte and Campbell (1978). The thenar layer rests on proxies, so the presets carry the open items D9 to D11 (spec section 14) as co-primary scenarios rather than single values.

**The 15-cell primary grid.** Every result produced with this generator is reported on these cells. **A conclusion that changes across cells is reported as unresolved by the available evidence, not averaged.**

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

The default `c` is the full-precision fitted value; +0.035 is the co-primary value from Jepma et al. (2014). P2 and P4 are not duplicated over `c` because they set `tau` = 0 and, under the intended spot order, the previous event is always in the other region. `Delta` = 0 under P3 and P4 is the double-count stress of register item 28. In the GUI, grid runs are labelled `cell01` to `cell15`.

## Output files

All files go to the chosen folder, named `<prefix>_<name>`.

| File | Written | Contents |
| --- | --- | --- |
| `<prefix>_manifest.json` | always | tool, spec and generator versions; UTC time; library versions; the full configuration; effective parameters per run; the run list; the seed derivation; every subject seed; notes; files written; the rules |
| `<prefix>_events.csv` | if ticked | one row per subject, run and event: `subject, subject_seed, run, cell, scenario, Delta, c, event, t_s, region, spot, temp_c, visit, latent, observed`, optionally `raw, z`, then the four flags |
| `<prefix>_persons.csv` | if ticked | one row per subject, run and region: `threshold_c, tolerance_c, width_c, exponent, zero_point_c, T_at_rating_5_c, step_mean, step_sd, step_person, step_variate` (fresh-skin values) |
| `<prefix>_summary.csv` | if ticked | by run, region and visit (visits 4 and later pooled as `4+`): counts; mean, SD, median, 5th and 95th percentile of `latent` and `observed`; share of each flag |
| `<prefix>_rating_vs_temperature.csv` | if ticked | by run, region and delivered temperature: counts, visits present, and the same statistics |
| `<prefix>_rating_vs_temperature_<run>.<fmt>` | if the plot is ticked and matplotlib is installed | one figure per run (`single` or `cell01` to `cell15`): forearm and thenar panels, each event's rating against delivered temperature, medians per temperature, optional fresh-skin curves, the 40 to 49 C window and the 2 / 5 / 8 anchors |

Floats are written in shortest round-trip form; booleans as `true` / `false`. Statistics in the summary tables pool all subjects within a run; for grid runs, compare cells rather than pooling across them.

## Validation (spec section 16)

- **Run self-tests (checks 8 to 10).** Runs the 49 unit tests of spec section 16 on the embedded generator: dynamics (check 8), determinism and common random numbers (check 9), flags and input handling (check 10). The log reports "49 of 49 pass" or lists each failure.
- **Replay golden vectors...** Select `golden_vectors.json` from the v2.8 specification package. Every case is replayed against PART 1 and the log reports the number of cases, the maximum numeric difference and whether every flag matches. PASS requires a difference of exactly 0 and identical flags; different numpy or scipy versions can give tiny differences, and the implementation guide allows 1e-6.

The remaining checks of spec section 16 (person marginals, reachability on the grid, noise calibration and so on) are computed by `refit.py` in the specification package, not by this tool.

## Using the module without the GUI

```python
import heat_pain_gui as H

# One person, one session
g = H.Generator(seed=12345, params={"c": 0.035}, scenario="P3")
events = [H.ev(28.0 * i, *H.INTENDED_ORDER[i % 6], 45.0) for i in range(18)]
out = g.simulate(events)          # list of dicts: latent, observed, raw, z, flags
anchors = g.person()              # fresh-skin threshold, tolerance, exponent, steps per region

# A batch run, exactly as the GUI does it
cfg = H.default_config()
cfg.update(seed=1, n_subjects=200, grid_mode=True, events=events)
cfg["output"].update(directory="out", prefix="study1")
errors, notes = H.validate_config(cfg)
res = H.run_batch(cfg)
files, rows = H.write_outputs(res)

# Validation
results = H.run_unit_tests()                       # checks 8 to 10
n_cases, max_diff, flags_ok = H.replay_golden("golden_vectors.json")

# Reproduce a run from its manifest
cfg2 = H.load_config("out/study1_manifest.json")
```

`H.subject_seeds(base_seed, n)` returns the per-subject seeds; `H.build_template(...)` and `H.read_events_csv(path)` build event lists as the GUI does.

## Rules that come with the generator

From implementation guide section 6, and repeated in every manifest:

- `latent` is the scoring target; `observed` is what a procedure may see (contract 5).
- Report on the 15-cell grid (spec section 12). A conclusion that changes across cells is reported as unresolved by the available evidence, not averaged.
- Use common random numbers for sweeps: same seeds, parameters changed through `params` (contract 3).
- Inputs are evaluated and flagged, never clamped (contract 4). Treat `extrapolated` and `beyond_measured_visits` outputs as outside the evidence.
- One person, one session (register item 24). `reset()` is a counterfactual replay, not a second visit; a later real session is not a replay of the first (Evans et al., 2026).

## Known limits (spec sections 14 and 15)

Also listed in implementation guide section 7.

- **The thenar layer rests on proxies and scenarios** (D9 to D14; register items 16, 28, 43). `Delta`, `tau` and the thenar dynamics are carried as co-primary values or presets.
- **The threshold shape** is set from independent data (Lotsch et al., 2026) that the anchors of Amir et al. (2022) only partly support (register item 30, D18). `alpha_pop` = 0 (log-normal) and the interval ends -6.17 and -1.98 are the sensitivities.
- **The fresh-skin upper tails are heavy** (register item 48): the threshold 99th percentile is above any deliverable stimulus, and 1.2 percent of people could not produce a usable anchor.
- **The noise far tail is lighter in the data than in the `t`** (register item 29; check 18 fails); the spread has unmodelled structure near the middle of the scale (register item 47).
- **`c` is applied at a longer gap than it was fitted at** (register item 38); +0.035 is co-primary.
- **The visit-3 multiplier does not depend on temperature here**, though the data of Jepma et al. (2014) say it does (register item 16); visits beyond the third are flagged.
- **Dependency between sources.** The Dildine, Mischkowski and Amir samples come from the same screening pipeline, so the Dildine refits are not an independent check on the Amir anchors; Jepma et al. (2014) is the only independent replication of the dynamics (spec section 1).

## References

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

The full source list, including sources used only for direction or stress bounds, is in spec section 17.
