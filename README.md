# Telangana TruDocs

Real-estate document search for Telangana. Python (FastAPI) backend, React+Vite frontend.

## Status (v0, first working slice)

Working end-to-end against the live government portals:
- **GHMC Mutation Status** — fully working; the record shows as our PDF.
- **GHMC Property Tax Search** — fully working (circle is a required field on the portal, not optional); the record shows as our PDF.
- **CDMA Property Tax Receipt** — fully working, no login, captcha or OTP (cdma.cgg.gov.in, every Telangana town outside GHMC). Enter a 10-digit PTIN, or pick the town and type a door number or owner name (3+ characters; up to 100 matches shown) to find it. Results show in a PDF preview with **Download PDF**, as in the Karnataka EC tool: first our own A4 PDF of the owner, door number, locality, usage, the tax due today (arrear and current, with interest) and every receipt on the portal, watermarked "Only For Information" (it reuses the look-up, so it costs the portal nothing extra); then any receipt's official PDF on request, the portal's own and untouched (seal watermark and QR code). The preview uses pdf.js (`pdfjs-dist`, as in trudocs-state's frontend shell), loaded only when a preview opens. The portal takes 14–50 s to make a receipt (over a minute when many are asked for at once), so PDFs are cached 6 hours (last 64 kept) and look-ups 5 minutes. The town list is `backend/data/cdma_towns.json`, rebuilt with `python -m backend.scripts.scrape_cdma_towns`.
- **TG-bPASS Building Permission** — fully working, no login, captcha or OTP. Enter a TG-bPASS file number to see the application's status, type, dates and place, with its official letters (the letter of approval for commencement of work, the building permit order, and any fee, revocation or show-cause letters) in the PDF preview, as on the CDMA tool. It uses the old TG-bPASS portal's public Citizen Search (backend.tsbpass.com), which still answers for the ~3.1 lakh applications filed before December 2025, when new applications moved to BuildNow (login only). The portal's own banner says it closed, so it may go away; the tool then shows a friendly message. Its application detail page is deliberately not used: it exposes applicants' Aadhaar, PAN and mobile numbers. The letters' links are signed for an hour, so they are fetched afresh; look-ups are cached 6 hours.
  - *Problems we hit while building it:*
    - **The new BuildNow portal can't be used.** TG-bPASS was replaced by BuildNow in December 2025, but BuildNow's search needs a logged-in account (mobile OTP) and Google reCAPTCHA. One shared account serving every user would get blocked and break the portal's terms (the same reason the EC tool was dropped), and reCAPTCHA is not something we automate.
    - **The old portal is officially closed.** Its own banner says it closed after 15 December 2025, yet its public search still answers, so the tool is built on it knowing it may stop.
    - **The old portal leaks personal data.** Its application detail page hands out applicants' Aadhaar, PAN, mobile, email and address to anyone, with no login. We never call it (worth reporting to the department). That page held the building facts (built-up area, floors, setbacks), so the tool shows those only inside the official letters.
    - **A search by area was dropped.** Searching a district + survey/plot/house number was planned, but the portal's town list is broken (it returns one town), its district names are stored in unusual spellings ("Hanamkonda", "Jagityal", "Medchal - Malkajgiri"…), every filter is an exact match, and the results list strangers' applications and names. For privacy and reliability the tool searches by file number only.
    - **Easy-to-miss portal traps:** an unknown search key silently means "no filter" (all 3 lakh applications, ~22 s), so only the portal's own keys are sent; the letters' links expire after an hour; a new connection is sometimes dropped and is retried once.
  - *Limitations:*
    - Only applications filed on TG-bPASS **before December 2025** (~3.1 lakh); anything newer is on BuildNow and isn't covered (the form says so up front).
    - Search by the **exact file number** only, as on the letters; no search by survey/plot number or owner name.
    - No separate built-up area / floors / setbacks block (read them in the letter), and no applicant name in the result (the letters carry it).
    - Only the letters the portal holds: some applications have none, and a rejected one shows a revocation instead of an approval.
    - If the government switches the old portal off, the tool can only say the portal isn't responding.
    - About 2 s per look-up and 3 s per letter; the portal is limited to 60 requests a minute, so 20 people searching at once wait up to ~20 s.
- **Adangal Extract (Pahani)** — **no records online (checked 22 Nov 2026).** The CCLA portal lists no survey or khata numbers for any village (8 districts tried, and on its own page in a browser too) and answers "No RoR-1B Details Found" to every search, so the page says so above the form and points to Land Details. Our search is built end to end, including the final search submit. A Pahani shows as our PDF (landscape A4, the portal's tables as drawn). (Note: the portal's survey/khata number lists come back empty for every village tried, so the number is typed in. Bhu Bharati's survey lists were tried as the dropdown instead (Oct 2026), but the Adangal search answered "No RoR-1B Details Found" for every one of those numbers, so no Pahani has been seen live and its PDF is tested with a made-up table only.)
- **Land Market Value (IGRS unit rates)** — fully working, no login or captcha. Outside Hyderabad: village search over a pre-scraped list (`backend/scripts/scrape_market_value_hierarchy.py`). Hyderabad: division + locality name, searched live (the portal matches the start of the name, 3+ letters). Shows only what the official page shows (land ₹/sq. yard and effective date), as our PDF: the portal comments out its apartment-rate column, and its apartment search returns 404.
- **Prohibited Lands (Section 22A)** — fully working, no login or captcha (IGRS `openProhibitedProperties.htm`). Village search over a pre-scraped list (`backend/scripts/scrape_prohibited_lands_hierarchy.py`); Hyderabad is division + SRO office (non-agriculture only). The first 22-A(1) category that's online opens in the PDF preview with the result, and every other category's official PDF (Waqf and Endowment aren't online on the portal either) and each order in the survey-wise list shows there on request. The survey-wise list itself stays a searchable table (a Hyderabad list would be ~750 PDF pages). A Hyderabad SRO list is ~6,000 rows and takes the portal ~30 s, so lists are cached per process for 6 hours.
- **Land Details Search (Bhu Bharati, agri land status)** — fully working, no login or OTP (Bhu Bharati `/knowLandStatus`). Two public search modes: by village + survey/khata number, or by passbook number + the last 4 digits of the owner's Aadhaar. The portal captcha is solved with ddddocr (`backend/core/captcha.py`), retried up to 8 times. Shows the portal's full 16-field record, including Land Status, as our PDF (never the Aadhaar digits). Identical searches arriving together share one portal flow (single-flight); nothing is cached at rest, and the Aadhaar digits and captcha text are never logged.
- **Survey Map** — fully working, no login, captcha or OTP. Pick a village and survey number to get our PDF of its boundary on a satellite photo, with neighbouring survey numbers, corner GPS points (P1, P2, …) and area in acres/guntas; the page adds an "Open in Google Maps" link. Boundaries come from TGRAC's public ArcGIS server (the village maps behind tgrac.telangana.gov.in/digitallandsurvey/lis): the "30 cm" copy first, and Bhunaksha's older "2.5 m" copy for the ~1 village in 4 the 30 cm copy lacks (the page says when a result is from the older map, which can be 20–50 m off). The server takes 13–60 s to find a village's parcels, so each village is fetched once and cached (public map data), and at most 2 look-ups are sent to it at a time. The village list is `backend/data/survey_map_villages.json`, rebuilt with `python -m backend.scripts.scrape_survey_map_villages`. Satellite imagery is Esri World Imagery; check Esri's terms (or swap the provider in `SATELLITE_EXPORT` in `backend/scrapers/survey_map/pdf.py`, and `SATELLITE_TILES` in `frontend/src/views/VillageMap/VillageMapView.jsx` and `backend/scrapers/village_map/client.py`) before commercial use.
- **Village Map** — fully working, no login, captcha or OTP. Pick a village to get its whole survey map as an A3 PDF in the preview with **Download PDF** (the satellite photo, every parcel's outline and survey number, the village name, a north arrow and a "for reference only" note), and under it the same map on screen (roads and streams dashed), with zoom for crowded areas. It uses Survey Map's TGRAC village maps and cache, so a village opened in either tool is ready in both. The photo is stitched from Esri World Imagery tiles (same licence note as Survey Map); the PDF needs `reportlab`.
- **Hydra FTL Map (HMDA lakes)** — fully working, no login, captcha or OTP. Pick a district, mandal and village (or type a lake's name or HMDA lake ID) to list the lakes HMDA has notified there, then open a lake's official **FTL and buffer zone map** in the PDF preview with **Download PDF**, as on the TG-bPASS tool, plus its **FTL on the village survey map (cadastral)** and, where issued, the **survey numbers in the FTL and buffer zone** with their extent and ownership type. The lake's preliminary and final notification dates are shown (no final notification = the boundary is still preliminary). Source: HMDA's lakes portal (lakes.hmda.gov.in), ~3,000 lakes in 7 districts around Hyderabad; its whole list is read once and kept 6 hours, and the last 16 maps are kept 6 hours. Under the maps, **water bodies in the lake's village** from the government's encroachment survey (TGRAC's Tank Information System: each water body's size, survey number where known, status in 2023 and, inside the Outer Ring Road, in 2011, and a map link). That survey is a fixed snapshot, baked into `backend/data/hydra_water_bodies.json` and rebuilt with `python -m backend.scripts.scrape_hydra_water_bodies`.
  - *Problems we hit while building it:*
    - **The government map server's own FTL layers are broken.** TGRAC has a HYDRAA folder with `FTL_Tanks` (2014, 2023, 2025) and `Topo_Tanks`, but their layers point at nothing (no fields, no extent), and `FTL_Query` is empty. HMDA's lakes portal is the only working source of the FTL boundaries, as scanned, signed PDFs.
    - **The PDFs' file names follow no pattern** (an `_` after the lake ID or not, `/` turned into `-`, `…_FTL_final.pdf` for some Hyderabad lakes, even typos such as `700-N-oo33` for `700/N/0033`), so a map can't be linked directly. The tool presses the row's button the way the page does (an ASP.NET postback, sending back the page's ~1.7 MB form state) and follows the redirect, and checks the file it is sent carries that lake's ID or name. (A first check that also wanted the file name to end in FTL/CADASTRAL/SyNo wrongly rejected 12 of the 71 Hyderabad maps; the stress tests caught it.)
    - **The encroachment survey can't be tied to an HMDA lake.** It uses neither HMDA's lake IDs nor (for 9 in 10 water bodies) names, and HMDA's list has no coordinates, so name matching linked only ~20 of ~3,000 lakes. It is shown per village instead, clearly labelled, for the user to match by survey number, size or place on the map. The two sources also spell villages differently (Thimmapalli / Thimmapally); common spelling variants are matched, and where two villages share a name in a district, only the one in the same mandal is used.
    - **The portal's list has quirks:** a few empty rows, and a few lakes listed twice (one copy without the final notification); the fuller row is kept.
  - *Limitations:*
    - Only lakes **HMDA has notified** (its area around Hyderabad, 7 districts); lakes elsewhere in Telangana aren't covered. About half have only a preliminary notification, and only those with a final notification (~1,360) have the survey-number list.
    - The maps are **scans**: the tool can't tell automatically whether a plot or GPS point is inside the FTL or buffer zone; the user reads the survey-number list or the map.
    - The water-body survey shows for **~3 in 4 lakes** (villages it has, under a matching spelling) and may list other water bodies of the same village; the status is the survey's (2023), not today's.
    - About 5 s to read HMDA's list the first time in 6 hours, then 1–3 s per map (0.1–4 MB); the portal is limited to 60 requests a minute, so 20 people opening maps at once wait up to ~40 s.
    - HMDA's server now and then cuts a download short; the user sees "portal isn't responding" and a retry works. If it ever sent a map extremely slowly, the request would wait for it: there is no overall time limit, only 90 s of silence.
    - A few maps listed on HMDA's page have no file behind them (e.g. one survey-number list in Medak); the tool then says no record was found.
- **RERA Certificate (TG-RERA)** — fully working, no login or OTP (rerait.telangana.gov.in). Search by project name, promoter name or registration number (e.g. P02400001224); up to 50 matches per search, with the total. Each project's official PDFs, the Registration Certificate (Form C) and, where issued, the Extension and Special 4-month extension certificates (Form F), show in the PDF preview when picked, exactly as TG-RERA signed them (no front page, which would break the signature). The search captcha is solved with ddddocr (first try in 26 of 26 live searches). The portal's HTTPS server omits its intermediate certificate, so `backend/scrapers/rera/emsign_ssl_ca_g1.pem` ships it (verified against the emSign root in certifi) instead of turning verification off. Results and certificates are public, cached 6 hours.

Not yet built: Bhu Bharati EC (no confirmed working URL found yet), TG-IGRS Encumbrance Certificate (confirmed to require citizen login + OTP — blocked on that decision).

## Frontend

The page is trudocs-state's frontend shell (the TruDocs design shared with Karnataka, from `trudocs-state/frontend-shell`): the TruEstate header with the tools as tabs in three groups, the hero, and a section per tool on desktop; on phones Market Value on the page itself, the other tools as "Explore more" cards that open in a bottom sheet, and a drawer menu.
- `frontend/src/tools.js`: the tools, their order, groups, icons and section ids (one list for the header, drawer, sections and cards)
- `frontend/src/views/<Tool>/<Tool>View.jsx`: one screen per tool; their calls to our backend are in `frontend/src/utils/api.js` (the shell's helper block on top, then one block per tool)
- `frontend/src/components/`: the shell's shared pieces (header, drawer, bottom sheet, loader, status message, PDF viewer) and ours (village search, dropdown with spinner, EC-style document result)
- `frontend/src/content/toolExplainers.js`: the explainer under each tool (an overview, what the record shows, and why the portal makes it hard to find), drawn by `components/common/ToolExplainer.jsx`; one entry per tool id in `tools.js`
- `frontend/src/styles/`: the shell's stylesheets unchanged, plus `telangana.css` for our additions and fixes (two-digit section numbers, 16px fields on phones, Safari dropdowns, wide results that scroll inside their card, maps)

Every tool's result is a PDF in the preview with **Download PDF**, as in the Karnataka EC tools: the portal's own PDFs where it has them (CDMA receipts, TG-bPASS letters, HMDA lake maps, 22-A lists and orders, RERA certificates), otherwise our own PDF of what the page showed (`backend/core/pdf.py`: the site's look, the source and time in the footer, watermarked "Only For Information"; personal records are made from their own search and kept nowhere). Pages keep only what a PDF can't do: the village map's zoom, Survey Map's Google Maps link, the searchable 22-A survey list, and the lists of documents to show. Text with Telugu in it (village names, survey numbers like 1/2అ, names on Bhu Bharati) is set in Hind Guntur (`backend/fonts/`, SIL Open Font License), which has both scripts, and shaped by HarfBuzz (`uharfbuzz`), since Helvetica has no Telugu letters. The preview draws a PDF's first 10 pages (official 22-A lists run to 25 scanned pages, too much for a phone's memory); Download PDF has them all.

Every PDF opens with our front page, the TruEstate cover of the Karnataka tools: the logo, the service's name, and what was searched (a village and survey number, a PTIN, a lake; never an Aadhaar number), sized like the document's first page. The file is named in the same words, e.g. "Land Details Search - Hydersaipet - Survey No. 1.pdf". A PDF its department signed (TG-RERA's certificates) goes out exactly as issued, since an added page would break its signature. The front page is drawn in `backend/core/pdf.py` (fonts Poppins and Montserrat in `backend/fonts/`, SIL Open Font License) and joined to the PDF with `pypdf`; at most 4 are added at once, and the cached official PDFs are kept with theirs, so a crowd asking for one map shares one copy. On each tool the line saying the PDF is ready and **Download PDF** sit at the foot of the search card, as on the Karnataka tools, with the preview below.

## Run locally

Backend:
```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn backend.main:app --reload
```

Frontend (separate terminal, dev mode with hot reload, proxies /api to :8000):
```
cd frontend
npm install
npm run dev
```

Or build the frontend once and let the backend serve it as one process:
```
cd frontend && npm run build && cd ..
.venv/bin/uvicorn backend.main:app
```

Tests (parsers, validation, error mapping and single-flight — no network, synthetic data):
```
.venv/bin/pip install pytest
.venv/bin/python -m pytest tests
```

Load tests (server running) fire N searches at the same moment at the live portals. They all come from one
machine, which counts as one person (30 searches a minute), so start the server for them with a higher limit:
`SEARCHES_PER_MINUTE=1000 .venv/bin/uvicorn backend.main:app`. Market value and prohibited
lands throttle themselves to 2 portal requests a second and cache repeats for 6 hours; land details solves the
captcha for each search, and identical searches share one flow; survey map caches each village and sends
at most 2 searches to the government map server at once; village map shares survey map's cache and builds each PDF once (the last 8 are kept); RERA solves its captcha per search and caches results for 6 hours; CDMA tax looks up PTINs from no town (`--ptin` for one you may look up, which also downloads its first receipt); TG-bPASS looks up made-up file numbers (`--file` for one you may look up, which also downloads its first letter); Hydra FTL opens different lakes' FTL maps (public map data), and `--same` the same lake:
```
.venv/bin/python -m backend.scripts.load_test_market_value --base http://localhost:8000 -n 10
.venv/bin/python -m backend.scripts.load_test_market_value --base http://localhost:8000 -n 10 --same
.venv/bin/python -m backend.scripts.load_test_prohibited_lands --base http://localhost:8000 -n 10
.venv/bin/python -m backend.scripts.load_test_prohibited_lands --base http://localhost:8000 -n 10 --same
.venv/bin/python -m backend.scripts.load_test_land_details --base http://localhost:8000 -n 10
.venv/bin/python -m backend.scripts.load_test_land_details --base http://localhost:8000 -n 10 --same
.venv/bin/python -m backend.scripts.load_test_survey_map --base http://localhost:8000 -n 10
.venv/bin/python -m backend.scripts.load_test_survey_map --base http://localhost:8000 -n 10 --same
.venv/bin/python -m backend.scripts.load_test_village_map --base http://localhost:8000 -n 10
.venv/bin/python -m backend.scripts.load_test_village_map --base http://localhost:8000 -n 10 --same
.venv/bin/python -m backend.scripts.load_test_rera --base http://localhost:8000 -n 10
.venv/bin/python -m backend.scripts.load_test_rera --base http://localhost:8000 -n 10 --same
.venv/bin/python -m backend.scripts.load_test_cdma_tax --base http://localhost:8000 -n 10
.venv/bin/python -m backend.scripts.load_test_cdma_tax --base http://localhost:8000 -n 10 --same
.venv/bin/python -m backend.scripts.load_test_bpass --base http://localhost:8000 -n 10
.venv/bin/python -m backend.scripts.load_test_bpass --base http://localhost:8000 -n 10 --same
.venv/bin/python -m backend.scripts.load_test_hydra_ftl --base http://localhost:8000 -n 10
.venv/bin/python -m backend.scripts.load_test_hydra_ftl --base http://localhost:8000 -n 10 --same
```

Smoke test (server running): one real search per tool, the way the page does it, ending in the PDF a visitor would see; each PDF must open and start with our front page (a signed RERA certificate goes out as issued). Tools that need a person's own number (GHMC, CDMA, TG-bPASS) are checked with a made-up one, which must come back as "not found", unless you pass a number you may look up. A few wrong inputs must be refused before anything reaches a portal. Run it after every deploy:
```
.venv/bin/python -m backend.scripts.smoke_test --base http://localhost:8000
```

The same 12 tools in a real browser, on a desktop window and in Chrome's phone emulation, filled in like a visitor would, with a screenshot of each result (needs `pip install playwright`; it uses the installed Chrome):
```
.venv/bin/python -m backend.scripts.ui_test --base http://localhost:8000 --shots ui-shots
```

## Deploy on Google Cloud Run

The Dockerfile builds the page and the server into one image. Cloud Build builds it from the source, so no Docker is
needed on your machine:
```
gcloud run deploy telangana-trudocs --source . --region asia-south1 \
  --memory 1Gi --cpu 1 --timeout 300 --min-instances 1 --max-instances 1 --allow-unauthenticated
```
- **One instance.** The caches, the limit of 60 requests a minute per government site and the 30 searches a minute
  per person live in the server's memory: a second instance would double what each portal gets and split the caches.
  Share them first (e.g. Redis on Memorystore) before raising `--max-instances`.
- **asia-south1 (Mumbai)** keeps our requests to the government sites inside India; some government sites refuse
  foreign addresses.
- **`--min-instances 1`**: no cold start, so the first search after a quiet spell doesn't wait for the server to load.
- **1 GiB memory**: the server peaked at about 270 MB in the stress tests; big 22-A PDFs (up to 18 MB) need headroom.
- **`--timeout 300`**: the page gives up after 150 s; the slowest sites (22-A PDFs, TGRAC maps) answer within 60 s.
- **The visitor's address** comes from the X-Forwarded-For entry Cloud Run's proxy adds (`TRUST_PROXY_HOPS=1`, set in
  the Dockerfile; use `--set-env-vars TRUST_PROXY_HOPS=2` behind a Google load balancer). Check it once after
  deploying: 31 quick searches from one phone get "Too many searches" while a phone on another network still
  searches. If both are refused, the setting is wrong and everyone shares one limit.
- **Health check**: `/api/health`. **Logs**: one line per API request in Cloud Logging (route, status, time; never
  the numbers searched).
- **Before going live**: confirm the licence for the Esri satellite photos (Survey Map, Village Map).

## Go-live checklist

Checked on this build (22 Nov 2026): 328 tests pass; the smoke test runs 11 of the 12 tools end to end
against the live portals (Adangal: see above), and checks GHMC, CDMA and TG-bPASS with made-up numbers;
the browser test passes all 12 tools on a desktop and on a phone (24 of 24); load tests with 10 people
at once on Prohibited Lands and Market Value and 4 on Survey Map all answer, and the page itself answers
within 250 ms the whole time. The Docker image itself was not built (no Docker or GCP access), but its
steps were: `npm ci` and the build, `pip install -r requirements.txt`, and the server serving the page.

Still to do, in this order:
1. Review and merge `week1/merge-redesign-into-develop` and then this week's fixes into `develop`, and settle
   the layout question: the header's tool tabs (this build) or the v3 desktop sidebar.
2. Decide on Adangal: keep it with its notice, or hide it until the CCLA portal has records again (the hero
   then says 11 document types).
3. Confirm the licence for the Esri satellite photos (Survey Map, Village Map).
4. Deploy with the command above (one instance, asia-south1).
5. On the live address: run the smoke test (`--base https://<address>`), and check the per-person limit with
   31 quick searches from one phone, as described above.
6. Try GHMC Mutation, GHMC Property Tax and TG-bPASS once with a real number someone may look up: the tests
   could only use made-up ones.
7. Known limitation: resizing the window across the phone/desktop width (768 px), for example turning a
   small tablet, redraws the page in the other layout and clears every tool's form and result.
