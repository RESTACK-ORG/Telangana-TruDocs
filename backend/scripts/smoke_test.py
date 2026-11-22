"""One real search per tool, the way the page does it, against a running server.

The check to run after a deploy, or before handing a build over: each tool goes through the same
calls as the page, in the same order, and ends with the PDF a visitor would preview and download.
Each PDF must open, and every PDF but a signed RERA certificate must start with our front page.
Every check reaches its government portal, so run it by hand, not in a loop.

Tools that need a person's own number (GHMC, CDMA, TG-bPASS) are checked with a made-up one,
which must come back as a clear "not found". Pass a number you are allowed to look up to check
the whole path instead. A few wrong inputs are checked too: they must be refused with a message
before anything reaches a portal.

The calls are spaced out (--pace) to stay under the server's 30 searches a minute per person.

Usage (server running):
  .venv/bin/python -m backend.scripts.smoke_test --base http://localhost:8000
  .venv/bin/python -m backend.scripts.smoke_test --only rera,survey-map
  .venv/bin/python -m backend.scripts.smoke_test --cdma-ptin <PTIN> --bpass-file <file no.>
"""
import argparse
import io
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from pypdf import PdfReader

DATA = Path(__file__).resolve().parent.parent / "data"
VILLAGE = "KOKAPET"  # Rangareddy, on the edge of Hyderabad: every land tool knows it
MADE_UP = {"ghmc": "1234567890", "cdma": "1000000000", "bpass": "000000/ZZZZ/0000/2020"}


class Fail(Exception):
    pass


class NotFound(Exception):
    """The portal answered "no record": right for a made-up number, a finding for a real one."""


class Api:
    def __init__(self, base: str, pace: float):
        self.base, self.pace, self.calls, self._last = base.rstrip("/"), pace, 0, 0.0

    def call(self, method: str, path: str, body=None, timeout: float = 180):
        wait = self.pace - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.monotonic()
        self.calls += 1
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"content-type": "application/json"} if data else {})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.headers, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()

    @staticmethod
    def _detail(raw: bytes) -> str:
        try:
            detail = json.loads(raw).get("detail", "")
        except (ValueError, AttributeError):
            return raw[:80].decode("utf-8", "replace")
        return detail if isinstance(detail, str) else json.dumps(detail)[:120]

    def json(self, method: str, path: str, body=None):
        status, _, raw = self.call(method, path, body)
        if status == 404:
            raise NotFound(self._detail(raw))
        if status != 200:
            raise Fail(f"{method} {path.split('?')[0]} answered {status}: {self._detail(raw)}")
        return json.loads(raw)

    def pdf(self, method: str, path: str, body=None, front_page: bool = True) -> str:
        status, headers, raw = self.call(method, path, body)
        if status == 404:
            raise NotFound(self._detail(raw))
        if status != 200:
            raise Fail(f"{method} {path.split('?')[0]} answered {status}: {self._detail(raw)}")
        if not raw.startswith(b"%PDF"):
            raise Fail(f"{path.split('?')[0]} did not send a PDF ({headers.get('content-type')})")
        reader = PdfReader(io.BytesIO(raw))
        if front_page and "TruEstate" not in (reader.pages[0].extract_text() or ""):
            raise Fail(f"{path.split('?')[0]}: the PDF has no TruEstate front page")
        name = re.search(r'filename="([^"]+)"', headers.get("content-disposition", ""))
        return f"PDF {len(reader.pages)} p, {len(raw) // 1024} KB" + (f', "{name.group(1)}"' if name else "")


def _village(file: str, key: str = "village") -> dict:
    rows = json.loads((DATA / file).read_text(encoding="utf-8"))
    return next((r for r in rows if r[key].split("|")[0].strip().upper() == VILLAGE), rows[0])


def _q(**params) -> str:
    return urllib.parse.urlencode(params)


# ── one function per tool: returns a note, raises Fail or NotFound ───────────────────────────

def market_value(api, a):
    v = _village("market_value_hierarchy.json")
    body = {k: v[k] for k in ("district_id", "mandal_id", "mandal", "village_id", "village")}
    note = f"{v['village']}: " + api.pdf("POST", "/api/market-value/pdf", body)
    division = api.json("GET", "/api/market-value/hyderabad/divisions")[0]
    locality = api.json("GET", f"/api/market-value/hyderabad/localities?{_q(division_id=division['value'], q='SEC')}")
    if not locality:
        return note + "; Hyderabad: no locality starting SEC"
    body = {"district_id": "16_1", "division_id": division["value"],
            "locality_id": locality[0]["value"], "locality": locality[0]["label"]}
    return note + f"; Hyderabad {locality[0]['label']}: " + api.pdf("POST", "/api/market-value/pdf", body)


def land_details(api, a):
    v = _village("pattadar_hierarchy.json")
    surveys = api.json("GET", f"/api/pattadar/survey-options/{v['village_id']}")
    if not surveys:
        raise Fail("the village's survey list came back empty")
    khatas = api.json("GET", f"/api/pattadar/khata-options/{v['village_id']}?{_q(survey_no=surveys[0]['value'])}")
    if not khatas:
        raise Fail("the survey's khata list came back empty")
    body = {"district_id": v["district_id"], "mandal_id": v["mandal_id"], "village_id": v["village_id"],
            "survey_no": surveys[0]["value"], "khata_id": khatas[0]["value"]}
    return f"{len(surveys)} surveys, {len(khatas)} khatas: " + api.pdf("POST", "/api/pattadar/pdf", body)


def adangal(api, a):
    v = _village("adangal_hierarchy.json")
    surveys = api.json("GET", f"/api/adangal/survey-options/{v['village_id']}")
    survey = surveys[0]["value"] if surveys else "1"
    body = {"district_id": v["district_id"], "division_id": v["division_id"], "mandal_id": v["mandal_id"],
            "village_id": v["village_id"], "survey_or_khata_value": survey, "option": "surveyNo"}
    return f"{len(surveys)} surveys listed; survey {survey}: " + api.pdf("POST", "/api/adangal/pdf", body)


def prohibited_lands(api, a):
    v = _village("prohibited_lands_hierarchy.json")
    place = {"district_id": v["district_id"], "mandal_id": v["mandal_id"], "village_id": v["village_id"], "sro_code": ""}
    data = api.json("POST", "/api/prohibited-lands/categories", place)
    online = [(k, c) for k, cs in data.get("categories", {}).items() for c in cs if c.get("available")]
    if not online:
        return f"{v['village']}: no 22A list online for this village"
    kind, first = online[0]
    note = f"{len(online)} lists online; " + api.pdf("GET", f"/api/prohibited-lands/pdf?{_q(**place, kind=kind, formtype=first['formtype'])}")
    rows = api.json("POST", "/api/prohibited-lands/survey-list", {**place, "kind": kind})
    return note + f"; survey-wise list: {len(rows.get('rows', rows)) if isinstance(rows, (dict, list)) else '?'} rows"


def survey_map(api, a):
    v = _village("survey_map_villages.json")
    surveys = api.json("GET", f"/api/survey-map/survey-options/{v['dmv']}")
    if not surveys:
        raise Fail("the village's survey list came back empty")
    body = {"dmv": v["dmv"], "survey_no": surveys[0]["value"]}
    parcel = api.json("POST", "/api/survey-map/parcel", body)
    return (f"{v['village']}: {len(surveys)} surveys, {len(parcel.get('corners', []))} corners; "
            + api.pdf("POST", "/api/survey-map/pdf", body))


def village_map(api, a):
    v = _village("survey_map_villages.json")
    data = api.json("GET", f"/api/village-map/map/{v['dmv']}")
    parcels = data.get("parcels") or data.get("features") or []
    return f"{v['village']}: {len(parcels)} parcels; " + api.pdf("GET", f"/api/village-map/pdf/{v['dmv']}")


def hydra_ftl(api, a):
    places = api.json("GET", "/api/hydra-ftl/places")
    found = api.json("GET", f"/api/hydra-ftl/lakes?{_q(q='cheruvu')}")
    if not found.get("lakes"):
        raise Fail("no lake found for 'cheruvu'")
    lake = api.json("GET", f"/api/hydra-ftl/lake?{_q(key=found['lakes'][0]['key'])}")
    docs = lake.get("documents") or []
    if not docs:
        return f"{len(places)} districts, {found['total']} lakes; first lake has no map online"
    return (f"{len(places)} districts, {found['total']} lakes; {len(docs)} maps: "
            + api.pdf("GET", f"/api/hydra-ftl/document?{_q(key=lake['key'], kind=docs[0]['kind'])}"))


def ghmc_mutation(api, a):
    return api.pdf("POST", "/api/ghmc/mutation/pdf", {"assessment_number": a.ghmc_assessment or MADE_UP["ghmc"]})


def ghmc_property_tax(api, a):
    circles = api.json("GET", "/api/ghmc/circles")
    circle = a.ghmc_circle or circles[0]["value"]
    return f"{len(circles)} circles; " + api.pdf("POST", "/api/ghmc/property-tax/pdf",
                                                    {"circle": circle, "ptin": a.ghmc_ptin or MADE_UP["ghmc"]})


def cdma_tax(api, a):
    towns = api.json("GET", "/api/cdma-tax/towns")
    ptin = a.cdma_ptin or MADE_UP["cdma"]
    data = api.json("POST", "/api/cdma-tax/property", {"ptin": ptin})
    return (f"{sum(len(d['towns']) for d in towns)} towns; {len(data.get('receipts', []))} receipts; "
            + api.pdf("GET", f"/api/cdma-tax/pdf/{ptin}"))


def building_permission(api, a):
    data = api.json("POST", "/api/bpass/application", {"file_no": a.bpass_file or MADE_UP["bpass"]})
    docs = data.get("documents") or []
    if not docs:
        return "application found, no letters on the portal"
    return f"{len(docs)} letters: " + api.pdf("GET", f"/api/bpass/document?{_q(file_no=data['file_no'], kind=docs[0]['kind'])}")


def rera(api, a):
    found = api.json("POST", "/api/rera/search", {"project_name": "PRESTIGE"})
    project = next((p for p in found.get("projects", []) if p.get("certificates")), None)
    if not project:
        raise Fail("no project with a certificate for 'PRESTIGE'")
    cert = project["certificates"][0]
    return (f"{found['total']} projects; signed certificate: "
            + api.pdf("GET", f"/api/rera/certificate?{_q(kind=cert['kind'], token=cert['token'], project=project['project'])}",
                      front_page=False))


TOOLS = {
    "market-value": market_value, "land-details": land_details, "adangal": adangal,
    "prohibited-lands": prohibited_lands, "survey-map": survey_map, "village-map": village_map,
    "hydra-ftl": hydra_ftl, "ghmc-mutation": ghmc_mutation, "ghmc-property-tax": ghmc_property_tax,
    "cdma-tax": cdma_tax, "building-permission": building_permission, "rera": rera,
}
NEEDS_OWN_NUMBER = {"ghmc-mutation": "ghmc_assessment", "ghmc-property-tax": "ghmc_ptin",
                    "cdma-tax": "cdma_ptin", "building-permission": "bpass_file"}

# Wrong inputs: each must be refused with a message (400 or 422) before anything reaches a portal.
BAD_INPUTS = [
    ("POST", "/api/cdma-tax/property", {"ptin": "12AB"}),
    ("POST", "/api/ghmc/mutation/pdf", {"assessment_number": "12-34"}),
    ("POST", "/api/bpass/application", {"file_no": "<script>"}),
    ("POST", "/api/pattadar/pdf-by-passbook", {"passbook_no": "T1", "aadhaar_last4": "12"}),
    ("POST", "/api/rera/search", {}),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--only", help="comma-separated tool names: " + ", ".join(TOOLS))
    ap.add_argument("--pace", type=float, default=2.2, help="seconds between calls (30 a minute is the limit)")
    ap.add_argument("--ghmc-assessment")
    ap.add_argument("--ghmc-ptin")
    ap.add_argument("--ghmc-circle")
    ap.add_argument("--cdma-ptin")
    ap.add_argument("--bpass-file")
    a = ap.parse_args()
    api = Api(a.base, a.pace)

    names = a.only.split(",") if a.only else list(TOOLS)
    passed = 0
    print(f"{'tool':20} {'result':9} {'time':>6}  note")
    for name in names:
        t = time.monotonic()
        made_up = name in NEEDS_OWN_NUMBER and not getattr(a, NEEDS_OWN_NUMBER[name])
        try:
            note = TOOLS[name](api, a)
            result = "PASS"
            if made_up:
                result, note = "FAIL", "a made-up number was found: " + note
        except NotFound as e:
            result, note = ("PASS", f"made-up number: \"{e}\"") if made_up else ("NOT FOUND", str(e))
        except Fail as e:
            result, note = "FAIL", str(e)
        except Exception as e:  # the server itself: connection refused, timeout
            result, note = "ERROR", repr(e)[:160]
        passed += result == "PASS"
        print(f"{name:20} {result:9} {time.monotonic() - t:5.1f}s  {note}", flush=True)

    refused = 0
    for method, path, body in BAD_INPUTS:
        status, _, raw = api.call(method, path, body)
        ok = status in (400, 422) and bool(Api._detail(raw))
        refused += ok
        print(f"  wrong input {path:34} -> {status} {'refused' if ok else 'NOT REFUSED'}: {Api._detail(raw)[:70]}")
    print(f"\n{passed}/{len(names)} tools passed | {refused}/{len(BAD_INPUTS)} wrong inputs refused | {api.calls} calls")


if __name__ == "__main__":
    main()
