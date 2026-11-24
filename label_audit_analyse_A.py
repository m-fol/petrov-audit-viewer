"""Label audit (Stage A only): agreement and label precision. See PREREGISTRATION_label_audit.md. Run once.

    python scripts/label_audit_analyse_A.py --dir label_audit --out runs/label_audit
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("--dir", default="label_audit")
ap.add_argument("--out", default="runs/label_audit")
ap.add_argument("--boot", type=int, default=2000)
a = ap.parse_args()
d, out = Path(a.dir), Path(a.out)
out.mkdir(parents=True, exist_ok=True)


def wilson(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (c - h, c + h)


def kappa(x, y):
    cats = sorted(set(x) | set(y))
    po = (x == y).mean()
    pe = sum((x == c).mean() * (y == c).mean() for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else np.nan


def norm(s):
    return s.astype(str).str.strip().str.lower().replace({"nan": np.nan, "": np.nan})


key = pd.read_csv(d / "key.csv").set_index("alert_id")
A = [pd.read_csv(d / "answers" / f"sheet_A_annotator{i}.csv").set_index("alert_id").sort_index() for i in (1, 2)]
for df in A:
    for c in ("fire_or_burn_visible", "likely_cause", "confidence", "land_context"):
        df[c] = norm(df[c])
    df["cause3"] = df["likely_cause"].map(lambda v: "military" if v == "military" else ("unclear" if v == "unclear" else "other"))
assert (A[0].index == A[1].index).all() and len(A[0]) == 80
D = pd.DataFrame({"f1": A[0].fire_or_burn_visible, "f2": A[1].fire_or_burn_visible, "c1": A[0].likely_cause, "c2": A[1].likely_cause, "k1": A[0].cause3, "k2": A[1].cause3,
                  "q1": A[0].confidence, "q2": A[1].confidence}).join(key["label"])
n = len(D)
rng = np.random.default_rng(0)
draws = [rng.integers(0, n, n) for _ in range(a.boot)]
print("== A1 agreement between the annotators (n=%d)" % n)
rows = []
for name, x, y in (("fire_or_burn_visible", D.f1, D.f2), ("likely_cause (5 categories)", D.c1, D.c2), ("cause collapsed {military, other, unclear}", D.k1, D.k2)):
    k = kappa(x, y)
    kb = np.array([kappa(x.iloc[i].reset_index(drop=True), y.iloc[i].reset_index(drop=True)) for i in draws])
    kb = kb[~np.isnan(kb)]
    raw = (x == y).mean()
    print(f"  {name}: raw agreement {raw:.2f}, kappa {k:.2f} ({np.percentile(kb, 2.5):.2f} to {np.percentile(kb, 97.5):.2f})")
    rows.append(dict(item=name, raw=raw, kappa=k, lo=np.percentile(kb, 2.5), hi=np.percentile(kb, 97.5)))
pd.DataFrame(rows).to_csv(out / "agreement.csv", index=False)
print("  share of 'unclear': annotator 1 %.2f, annotator 2 %.2f; 'cannot_tell' on fire: %.2f, %.2f" % ((D.c1 == "unclear").mean(), (D.c2 == "unclear").mean(), (D.f1 == "cannot_tell").mean(), (D.f2 == "cannot_tell").mean()))
print("  fire visible 'yes': annotator 1 %.2f, annotator 2 %.2f" % ((D.f1 == "yes").mean(), (D.f2 == "yes").mean()))
print("  cause counts, annotator 1:", D.c1.value_counts().to_dict())
print("  cause counts, annotator 2:", D.c2.value_counts().to_dict())
print("  both decided (neither unclear): %d alerts; agreement among them on the 5 categories: %.2f" % (((D.c1 != "unclear") & (D.c2 != "unclear")).sum(),
      (D.c1 == D.c2)[(D.c1 != "unclear") & (D.c2 != "unclear")].mean()))

print("== A2 label precision as a range, within each class")
res = []
for lab, g in D.groupby("label"):
    m = len(g)
    mil1, mil2 = (g.c1 == "military"), (g.c2 == "military")
    both, either = (mil1 & mil2).sum(), (mil1 | mil2).sum()
    lo, hi = wilson(both, m)
    env = lambda s: s.isin(["agricultural", "wildfire"])  # noqa: E731
    e_both, e_either = (env(g.c1) & env(g.c2)).sum(), (env(g.c1) | env(g.c2)).sum()
    ind_both, ind_either = ((g.c1 == "industrial_static") & (g.c2 == "industrial_static")).sum(), ((g.c1 == "industrial_static") | (g.c2 == "industrial_static")).sum()
    un_both = ((g.c1 == "unclear") & (g.c2 == "unclear")).sum()
    print(f"  {lab} (n={m}): military by both {both} ({both / m:.2f}; Wilson {lo:.2f}-{hi:.2f}), by at least one {either} ({either / m:.2f}); agricultural/wildfire by both {e_both} ({e_both / m:.2f}), "
          f"by at least one {e_either} ({e_either / m:.2f}); industrial_static by both {ind_both}, by at least one {ind_either}; unclear by both {un_both} ({un_both / m:.2f}); fire visible 'yes' by both {((g.f1 == 'yes') & (g.f2 == 'yes')).sum()}")
    res.append(dict(label=lab, n=m, mil_both=both, mil_either=either, env_both=e_both, env_either=e_either, ind_both=ind_both, ind_either=ind_either, unclear_both=un_both,
                    mil_both_lo=lo, mil_both_hi=hi))
pd.DataFrame(res).to_csv(out / "label_precision.csv", index=False)

print("== A3 confidence")
ok = D.q1.isin(["medium", "high"]) & D.q2.isin(["medium", "high"])
print(f"  both at least medium: n={ok.sum()}, agreement on collapsed cause {(D.k1 == D.k2)[ok].mean():.2f}; otherwise n={(~ok).sum()}, agreement {(D.k1 == D.k2)[~ok].mean():.2f}")
print("  confidence counts: annotator 1", D.q1.value_counts().to_dict(), "; annotator 2", D.q2.value_counts().to_dict())

k3 = [r for r in rows if r["item"].startswith("cause collapsed")][0]["kappa"]
c = [r for r in res if r["label"] == "conflict_related"][0]
e = [r for r in res if r["label"] == "environmental_fire"][0]
print("P1 (kappa collapsed cause >= 0.40):", bool(k3 >= 0.40), round(float(k3), 3))
print("P2 (<= 20% of conflict-labelled rated military by both):", bool(c["mil_both"] / c["n"] <= 0.20), round(c["mil_both"] / c["n"], 3))
print("P3 (<= 10% of environmental-labelled rated military by at least one):", bool(e["mil_either"] / e["n"] <= 0.10), round(e["mil_either"] / e["n"], 3))
