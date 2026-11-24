# Audit viewer for blind visual checks of satellite fire alerts

A small, local tool for annotators who judge satellite fire alerts by eye. For each alert it shows clear Sentinel-2 true-colour images from before and after the alert date, a blink view, 3x close-ups, and (optionally) two basemap views, and records four answers per alert
(fire or burn visible, land context, likely cause, confidence). It was used for the human label check in *"Not Observed Is Not Calm: Where Open Sensors Go Blind and How to Verify Alerts for C2"* (ICMCIS 2027 submission). In that check two annotators agreed little (Cohen's kappa 0.13 for the cause), so this tool is
released as an instrument and as a record of how the check was run, not as evidence that ten-metre images settle the cause of a fire.

## What is in this archive
| File | What it is |
|---|---|
| `build_audit_viewer.py` | Reads a sheet of alerts (CSV), fetches the images, writes a folder with `index.html`, `data.js` and `images/` |
| `audit_viewer_template.html` | The page (self-contained, no internet needed after the build) |
| `ANNOTATOR_GUIDE.md` | The instructions given to annotators |
| `docs/` | A static website for GitHub Pages: `index.html` is the page used in the study (80 alerts, answers removed), `about.html` describes the tool |
| `label_audit_analyse_A.py` | Agreement (Cohen's kappa) and label-precision summary from two exported answer sheets and a key file (optional) |
| `example/alerts_example.csv` | Three example alerts with empty answer columns, to show the expected format |

No answers or labels are included. The only imagery is the Sentinel-2 before/after crops for the 80 study alerts in `docs/images` (Sentinel data, free and open); the two context panels use open data (ESA WorldCover land cover and a wider Sentinel-2 view), not the Esri basemap. `python build_audit_viewer.py ... --open-context` builds these panels for your own alerts.

## Use
1. Install the requirements: `pip install -r requirements.txt`.
2. Make a CSV with the columns of `example/alerts_example.csv` (`alert_id, date, lat, lon`, plus `eo_browser`, `satellite_map` for links, and empty answer columns).
3. Build the page: `python build_audit_viewer.py my_alerts.csv my_viewer --exclude-unusable` (add `--open-context` for open-data context panels, or `--no-basemap` to skip them). Images are fetched from the Microsoft Planetary Computer's public STAC and data API; no account is needed.
   `--exclude-unusable` drops alerts that have no clear image before or after the alert date (within 45 days) and writes their identifiers to `excluded_no_usable_imagery.csv`; report this number if you use it.
4. Give the annotator the whole output folder. They open `index.html` in a browser, answer, and click "Export CSV" once at the end. Answers are saved in the browser's local storage while they work (use the same browser and do not clear its data).

## Notes on data and terms
- Sentinel-2 imagery: contains modified Copernicus Sentinel data, free and open under the Copernicus data policy.
- The optional basemap views come from the Esri World Imagery service. Check Esri's terms before using or redistributing them; do not publish them in a data archive. `--no-basemap` leaves them out.
- The tool sends no information about the annotators anywhere; answers stay in their browser and in the CSV they export.
- If you run a study with people, check whether your institution requires ethics approval or consent before you collect anything.

## Limits
- Sentinel-2 pixels are 10 m. Small burns, impact craters and vehicles are usually not visible, and many answers will legitimately be `unclear`. Cloud, season and the time gap between the images matter.
- A blind check needs independent annotators. In the study above the first annotator was also the author, which should be stated in any report.

## Citation
See `CITATION.cff`. Licence: MIT (code) for the files here; the annotator guide may be reused with attribution.

## Website (GitHub Pages)
The `docs/` folder is a ready-made static site: its main page is the viewer with the 80 study alerts (answers removed), and `about.html` describes the tool. To publish it, push the repository to GitHub, open Settings, then Pages, and choose "Deploy from a branch", branch `main`, folder `/docs`. The site will be at `https://YOUR-USERNAME.github.io/REPOSITORY/`.
The site has no server and collects nothing; answers stay in the visitor's browser.
