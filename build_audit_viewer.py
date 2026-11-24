"""Pre-load imagery for the label audit and build a local labelling page.

usage: python build_audit_viewer.py <sheet.csv> <out_dir> [--limit N] [--exclude-unusable] [--no-basemap]

For every alert in the sheet it fetches (no account needed):
  - up to 3 clear Sentinel-2 L2A true-colour crops BEFORE the alert date and up to 3 ON/AFTER it
    (Microsoft Planetary Computer: public STAC + data API),
  - a close-up and a wider view of the Esri World Imagery basemap.
It writes images/, data.js and index.html into out_dir. Nothing from the answer key is used.
"""
import csv, io, json, math, os, sys, time, datetime as dt
from concurrent.futures import ThreadPoolExecutor
import requests
import numpy as np
from PIL import Image

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
DATA = "https://planetarycomputer.microsoft.com/api/data/v1/item/bbox/%f,%f,%f,%f/%dx%d.png"
ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export"
HALF_KM = 1.2      # half-width of close crop
WIDE_KM = 4.0
PX = 700
WINDOW_D = 45
GOOD_BRIGHT = 0.25   # local cloud/snow-like fraction
SES = requests.Session()


def box(lat, lon, km):
    dlat = km / 111.0
    dlon = km / (111.0 * math.cos(math.radians(lat)))
    return lon - dlon, lat - dlat, lon + dlon, lat + dlat


def get(url, **kw):
    for k in range(4):
        try:
            r = SES.get(url, timeout=120, **kw)
            if r.status_code == 200:
                return r
            if r.status_code in (429, 503, 502, 504):
                time.sleep(3 * (k + 1))
                continue
            return r
        except requests.RequestException:
            time.sleep(3 * (k + 1))
    return None


def search(lat, lon, d0, d1):
    body = {"collections": ["sentinel-2-l2a"], "bbox": [lon - 0.0005, lat - 0.0005, lon + 0.0005, lat + 0.0005],
            "datetime": "%sT00:00:00Z/%sT23:59:59Z" % (d0, d1), "limit": 200,
            "query": {"eo:cloud_cover": {"lt": 85}}}
    for k in range(4):
        try:
            r = SES.post(STAC, json=body, timeout=90)
            if r.status_code == 200:
                return r.json().get("features", [])
            time.sleep(3 * (k + 1))
        except requests.RequestException:
            time.sleep(3 * (k + 1))
    return []


def render_s2(item_id, lat, lon):
    bb = box(lat, lon, HALF_KM)
    r = get(DATA % (bb + (PX, PX)), params={"collection": "sentinel-2-l2a", "item": item_id, "assets": "visual",
                                             "asset_bidx": "visual|1,2,3", "nodata": 0})
    if r is None or r.status_code != 200:
        return None
    im = Image.open(io.BytesIO(r.content)).convert("RGBA")
    a = np.asarray(im)
    valid = a[..., 3] > 0
    if valid.mean() < 0.9:
        return None
    rgb = a[..., :3].astype(int)
    mn, mx = rgb.min(-1), rgb.max(-1)
    bright = float(((mn > 165) & (mx - mn < 40)).mean())
    return im.convert("RGB"), bright


def basemap(lat, lon, km, path):
    bb = box(lat, lon, km)
    r = get(ESRI, params={"bbox": "%f,%f,%f,%f" % bb, "bboxSR": 4326, "imageSR": 4326, "size": "%d,%d" % (PX, PX),
                          "format": "jpg", "f": "image"})
    if r is None or r.status_code != 200 or "image" not in r.headers.get("content-type", ""):
        return False
    open(path, "wb").write(r.content)
    return True


def pick(cands, lat, lon, out, tag, imgdir):
    """cands: list of (datestr, [items]) already ordered by closeness. Returns list of dicts."""
    res, tried, fallback = [], 0, None
    for ds, items in cands:
        if len(res) >= 3 or tried >= 7:
            break
        items = sorted(items, key=lambda f: f["properties"]["eo:cloud_cover"])
        for f in items:
            tried += 1
            out_r = render_s2(f["id"], lat, lon)
            if out_r is None:
                continue
            im, bright = out_r
            rec = {"date": ds, "scene_cloud": round(f["properties"]["eo:cloud_cover"]), "local_bright": round(100 * bright)}
            if bright <= GOOD_BRIGHT:
                fn = "%s_%d.jpg" % (tag, len(res) + 1)
                im.save(os.path.join(imgdir, fn), quality=88)
                rec["file"] = fn
                res.append(rec)
            elif fallback is None or bright < fallback[0]:
                fallback = (bright, im, rec)
            break
    if not res and fallback is not None:
        bright, im, rec = fallback
        fn = "%s_1.jpg" % tag
        im.save(os.path.join(imgdir, fn), quality=88)
        rec["file"] = fn
        rec["note"] = "all passes cloudy near the point"
        res.append(rec)
    return res


def process(row, outdir):
    aid = row["alert_id"]
    lat, lon = float(row["lat"]), float(row["lon"])
    day = dt.date.fromisoformat(row["date"])
    imgdir = os.path.join(outdir, "images", aid)
    os.makedirs(imgdir, exist_ok=True)
    meta_p = os.path.join(imgdir, "meta.json")
    if os.path.exists(meta_p):
        return aid, json.load(open(meta_p))
    feats = search(lat, lon, (day - dt.timedelta(WINDOW_D)).isoformat(), (day + dt.timedelta(WINDOW_D)).isoformat())
    bydate = {}
    for f in feats:
        bydate.setdefault(f["properties"]["datetime"][:10], []).append(f)
    before = sorted([(k, v) for k, v in bydate.items() if k < day.isoformat()], key=lambda x: x[0], reverse=True)
    after = sorted([(k, v) for k, v in bydate.items() if k >= day.isoformat()], key=lambda x: x[0])
    meta = {"before": pick(before, lat, lon, None, "before", imgdir), "after": pick(after, lat, lon, None, "after", imgdir)}
    if "--no-basemap" in sys.argv:   # skip the Esri World Imagery views (check Esri's terms before using them)
        meta["ground"] = meta["wide"] = False
    else:
        meta["ground"] = basemap(lat, lon, HALF_KM, os.path.join(imgdir, "ground.jpg"))
        meta["wide"] = basemap(lat, lon, WIDE_KM, os.path.join(imgdir, "wide.jpg"))
    json.dump(meta, open(meta_p, "w"))
    return aid, meta


def main():
    sheet, outdir = sys.argv[1], sys.argv[2]
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    rows = list(csv.DictReader(open(sheet, encoding="utf-8-sig", newline="")))
    if limit:
        rows = rows[:limit]
    os.makedirs(outdir, exist_ok=True)
    metas = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        for i, (aid, meta) in enumerate(ex.map(lambda r: process(r, outdir), rows), 1):
            metas[aid] = meta
            print(i, len(rows), aid, len(meta["before"]), len(meta["after"]), flush=True)
    fields = list(rows[0].keys())
    if "--exclude-unusable" in sys.argv:
        # rule fixed before looking at any answer: an alert needs at least one clear (local cloud/snow-like <=25%)
        # Sentinel-2 image before AND one on/after the alert date within 45 days. Imagery only; labels are not used.
        keep, drop = [], []
        for r in rows:
            m = metas[r["alert_id"]]
            okb = any("note" not in x for x in m["before"])
            oka = any("note" not in x for x in m["after"])
            (keep if okb and oka else drop).append((r, okb, oka))
        with open(os.path.join(outdir, "excluded_no_usable_imagery.csv"), "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["alert_id", "date", "clear_before", "clear_after"])
            for r, okb, oka in drop:
                w.writerow([r["alert_id"], r["date"], int(okb), int(oka)])
        print("excluded", len(drop), "kept", len(keep))
        rows = [r for r, _, _ in keep]
    data = {"sheet": os.path.basename(sheet), "fields": fields, "rows": rows, "meta": metas,
            "half_km": HALF_KM, "wide_km": WIDE_KM}
    open(os.path.join(outdir, "data.js"), "w", encoding="utf-8").write("window.AUDIT = " + json.dumps(data) + ";")
    tpl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_viewer_template.html")
    open(os.path.join(outdir, "index.html"), "w", encoding="utf-8").write(open(tpl, encoding="utf-8").read())
    print("done", outdir)


if __name__ == "__main__":
    main()
