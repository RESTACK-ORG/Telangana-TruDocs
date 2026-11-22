"""The 12 tools in a real browser, on a desktop and on a phone, the way a visitor uses them.

Each tool's form is filled in like a visitor would (village search, drop-downs, numbers) and its
button pressed. Then the result is checked: the PDF preview drawn on the page and Download PDF
saving a real PDF, or, for a made-up number, a clear message. The desktop is a 1440-wide window,
2400 tall so a whole tool fits in a plain screenshot: a screenshot past the window's edge makes
Chrome shrink the window to 1x1 for a moment, which flips the page to its phone layout and back
and resets every form.
The phone is Chrome's phone emulation (390x844, touch): the main tool is on the page and the
others open from "Explore more" in a bottom sheet. A screenshot of each result goes to --shots.

Needs Playwright with the installed Chrome (pip install playwright; no browser download). Each
tool reaches its government portal, like the smoke test, so run it by hand.

Usage (server running):
  python -m backend.scripts.ui_test --base http://localhost:8000 --shots ui-shots
  python -m backend.scripts.ui_test --only rera-certificate --device phone
"""
import argparse
import re
import tempfile
import time
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

WAIT = 180_000  # ms: the slowest portals answer within a minute, the page gives up at 150 s
VILLAGE = re.compile("kokapet", re.I)
MADE_UP = {"ghmc": "1234567890", "bpass": "000000/ZZZZ/0000/2020"}


class Fail(Exception):
    pass


def village(scope, name="Kokapet"):
    scope.locator(".typeahead-input-row input").first.fill(name)
    scope.locator(".typeahead-item", has_text=VILLAGE).first.click(timeout=30_000)


def choose_first(select):
    """The first real option of a drop-down, once it has loaded."""
    select.page.wait_for_function("s => !s.disabled && s.options.length > 1", arg=select.element_handle(), timeout=WAIT)
    select.select_option(index=1)


def submit(scope):
    scope.locator("button.submit-btn:visible").first.click()


def shoot(page, scope, out: Path):
    """The tool as it is on screen, without capturing past the window (see the top)."""
    scope.evaluate("el => el.scrollIntoView({block: 'start'})")
    box = scope.bounding_box()
    top = max(box["y"], 0)
    page.screenshot(path=str(out), clip={"x": box["x"], "y": top, "width": box["width"],
                                         "height": min(box["y"] + box["height"], page.viewport_size["height"]) - top})


def expect_pdf(page, scope, out: Path, name: str) -> str:
    done = scope.locator(".pdf-canvas-container canvas, .status-msg.error").first
    done.wait_for(timeout=WAIT)
    error = scope.locator(".status-msg.error")
    if error.count() and error.first.is_visible():
        raise Fail("error shown: " + error.first.inner_text())
    scope.locator(".pdf-canvas-container canvas").first.wait_for(timeout=WAIT)
    with page.expect_download(timeout=60_000) as dl:
        scope.locator("button.download-btn").first.click()
    path = Path(tempfile.gettempdir()) / f"ui-test-{name}.pdf"
    dl.value.save_as(path)
    head = path.read_bytes()[:5]
    size = path.stat().st_size // 1024
    path.unlink()
    if head != b"%PDF-":
        raise Fail("Download PDF did not save a PDF")
    shoot(page, scope, out)
    return f"preview drawn, downloaded {dl.value.suggested_filename} ({size} KB)"


def expect_message(page, scope, out: Path, contains: str) -> str:
    msg = scope.locator(".status-msg.error").first
    msg.wait_for(timeout=WAIT)
    text = msg.inner_text().strip()
    if contains.lower() not in text.lower():
        raise Fail(f"unexpected message: {text}")
    shoot(page, scope, out)
    return f'message: "{text}"'


# ── one function per tool: scope is its desktop section or the phone's sheet ─────────────────

def market_value(page, scope, out):
    village(scope, "Kokapet")
    submit(scope)
    return expect_pdf(page, scope, out, "market-value")


def land_details(page, scope, out):
    village(scope)
    selects = scope.locator("form select")
    choose_first(selects.nth(0))  # survey number
    choose_first(selects.nth(1))  # khata number
    submit(scope)
    return expect_pdf(page, scope, out, "land-details")


def adangal(page, scope, out):
    village(scope)
    scope.get_by_placeholder("e.g. 123 or 5A").fill("1")
    submit(scope)
    return expect_message(page, scope, out, "no record")  # known: the portal finds no Pahani (README)


def prohibited_lands(page, scope, out):
    village(scope)
    submit(scope)
    return expect_pdf(page, scope, out, "prohibited-lands")


def survey_map(page, scope, out):
    village(scope)
    choose_first(scope.locator("form select").first)
    submit(scope)
    return expect_pdf(page, scope, out, "survey-map")


def village_map(page, scope, out):
    village(scope)
    submit(scope)
    return expect_pdf(page, scope, out, "village-map")


def hydra_ftl(page, scope, out):
    scope.locator("label.radio-option", has_text="Lake name or lake ID").click()
    scope.get_by_placeholder("e.g. Erra Cheruvu").fill("Salkam")
    submit(scope)
    scope.locator(".doc-item button.table-action-btn").first.click(timeout=WAIT)
    return expect_pdf(page, scope, out, "hydra-ftl")


def ghmc_mutation(page, scope, out):
    scope.get_by_placeholder("Enter assessment number").fill(MADE_UP["ghmc"])
    submit(scope)
    return expect_message(page, scope, out, "no record")


def ghmc_property_tax(page, scope, out):
    choose_first(scope.locator("form select").first)
    scope.get_by_placeholder("e.g. 1010133899").fill(MADE_UP["ghmc"])
    submit(scope)
    return expect_message(page, scope, out, "no record")


def cdma_tax(page, scope, out):
    scope.get_by_placeholder("e.g. 1113300005").fill("1113300005")  # the example the page itself shows
    submit(scope)
    return expect_pdf(page, scope, out, "cdma-tax")


def building_permission(page, scope, out):
    scope.get_by_placeholder("e.g. 123456/XXXX/0123/2025").fill(MADE_UP["bpass"])
    submit(scope)
    return expect_message(page, scope, out, "no record")


def rera(page, scope, out):
    scope.get_by_placeholder("e.g. Avasa Hills").fill("Prestige Nirvana")
    submit(scope)
    scope.locator(".doc-actions button").first.click(timeout=WAIT)
    return expect_pdf(page, scope, out, "rera")


# (section id, explore card name, test)
TOOLS = [
    ("market-value", "Market Value", market_value),
    ("pattadar-passbook", "Land Details", land_details),
    ("adangal", "Adangal", adangal),
    ("prohibited-lands", "Prohibited Lands", prohibited_lands),
    ("survey-map", "Survey Map", survey_map),
    ("village-map", "Village Map", village_map),
    ("hydra-ftl-map", "Hydra FTL Map", hydra_ftl),
    ("ghmc-mutation", "GHMC Mutation", ghmc_mutation),
    ("ghmc-property-tax", "GHMC Property Tax", ghmc_property_tax),
    ("cdma-tax-receipt", "CDMA Tax Receipt", cdma_tax),
    ("building-permission", "Building Permission", building_permission),
    ("rera-certificate", "RERA Certificate", rera),
]
MAIN_TOOL = "market-value"  # on the phone's page itself; the rest open in a bottom sheet


def run(browser, device: str, base: str, only, shots: Path, pause: float) -> list:
    phone = device == "phone"
    context = browser.new_context(
        viewport={"width": 390, "height": 844} if phone else {"width": 1440, "height": 2400},
        device_scale_factor=2 if phone else 1, is_mobile=phone, has_touch=phone, accept_downloads=True)
    page = context.new_page()
    page.goto(base, wait_until="networkidle")
    results = []
    for tool_id, label, test in TOOLS:
        if only and tool_id not in only:
            continue
        t = time.monotonic()
        out = shots / f"{device}-{tool_id}.png"
        try:
            if not phone:
                scope = page.locator(f"section#{tool_id}")
                scope.scroll_into_view_if_needed()
            elif tool_id == MAIN_TOOL:
                scope = page.locator(".main-content")
            else:
                page.locator(".explore-card").filter(
                    has=page.locator(".explore-card-name", has_text=re.compile(f"^{re.escape(label)}$"))).click()
                scope = page.locator(".bottom-sheet")
                scope.wait_for()
            note, result = test(page, scope, out), "PASS"
        except (Fail, PlaywrightError) as e:
            note, result = str(e).splitlines()[0][:160], "FAIL"
            page.screenshot(path=str(out))
        finally:
            if phone and tool_id != MAIN_TOOL and page.locator(".bottom-sheet-close").count():
                page.locator(".bottom-sheet-close").first.click()
                page.wait_for_timeout(600)
        results.append((device, tool_id, result, time.monotonic() - t, note))
        print(f"{device:7} {tool_id:20} {result:4} {time.monotonic() - t:5.1f}s  {note}", flush=True)
        time.sleep(pause)  # stay under 30 searches a minute per person
    context.close()
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--device", choices=["desktop", "phone", "both"], default="both")
    ap.add_argument("--only", help="comma-separated section ids, e.g. rera-certificate,survey-map")
    ap.add_argument("--shots", default="ui-shots")
    ap.add_argument("--pause", type=float, default=6.0, help="seconds between tools")
    a = ap.parse_args()
    shots = Path(a.shots)
    shots.mkdir(parents=True, exist_ok=True)
    only = set(a.only.split(",")) if a.only else None
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        for device in (["desktop", "phone"] if a.device == "both" else [a.device]):
            results += run(browser, device, a.base.rstrip("/") + "/", only, shots, a.pause)
        browser.close()
    passed = sum(r[2] == "PASS" for r in results)
    print(f"\n{passed}/{len(results)} passed; screenshots in {shots}")


if __name__ == "__main__":
    main()
