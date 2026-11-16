"""What a merge can quietly undo, checked across the whole backend.

On 26 Oct a merge into develop brought back older copies of nine backend files without a single
conflict to warn anyone: three throttles went from 60 to 120 requests a minute (and market value
and prohibited lands, one government site, stopped sharing theirs), 11 routes that wait on a
portal went back on the site's shared threads, and three files ended up with the same functions
defined twice. All 235 tests on develop still passed. Each test here fails on that develop.
"""
import ast
import importlib
import inspect
import pathlib
import pkgutil
from collections import Counter, defaultdict
from urllib.parse import urlparse

import backend.routers
import backend.scrapers
from backend.core.rate_limit import RateLimiter

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Routes that only read files we ship, never a government site, so they may use the shared threads.
LOCAL_ROUTES = {
    "adangal.villages_search",
    "market_value.villages_search",
    "pattadar_passbook.villages_search",
    "prohibited_lands.villages_search",
    "survey_map.villages_search",
    "cdma_tax.towns",
    "health.health",
}


def _throttled_modules():
    """Every scraper module with its own portal throttle, by module name."""
    found = {}
    for info in pkgutil.walk_packages(backend.scrapers.__path__, prefix="backend.scrapers."):
        module = importlib.import_module(info.name)
        if isinstance(getattr(module, "_throttle", None), RateLimiter):
            found[info.name] = module
    return found


def test_no_tool_sends_a_portal_more_than_60_requests_a_minute():
    modules = _throttled_modules()
    assert len(modules) >= 10  # the scan really found the tools
    too_fast = {name: m._throttle.min_interval_seconds for name, m in modules.items()
                if m._throttle.min_interval_seconds < 1.0}
    assert not too_fast, f"less than 1 s between requests (over 60 a minute): {too_fast}"


def test_tools_on_the_same_government_site_share_one_throttle():
    by_host = defaultdict(dict)
    for name, module in _throttled_modules().items():
        base_url = getattr(module, "BASE_URL", None)
        if base_url:
            by_host[urlparse(base_url).hostname][name] = module._throttle
    assert len(by_host["registration.telangana.gov.in"]) == 2  # market value and prohibited lands
    for host, throttles in by_host.items():
        assert len({id(t) for t in throttles.values()}) == 1, (
            f"{host} is used by {sorted(throttles)}, which don't share one throttle: "
            "together they would send it more than 60 requests a minute")


def test_every_route_that_waits_on_a_portal_runs_on_its_own_tools_threads():
    shared = []
    for info in pkgutil.iter_modules(backend.routers.__path__):
        router = getattr(importlib.import_module(f"backend.routers.{info.name}"), "router", None)
        if router is None:
            continue
        for route in router.routes:
            endpoint = route.endpoint
            # ToolThreads.route turns a plain def into a coroutine; a plain def runs on the shared pool.
            if not inspect.iscoroutinefunction(endpoint) and f"{info.name}.{endpoint.__name__}" not in LOCAL_ROUTES:
                shared.append(f"{sorted(route.methods)[0]} {route.path}")
    assert not shared, f"on the site's shared threads; wrap them with ToolThreads.route: {shared}"


def test_no_backend_file_defines_the_same_function_twice():
    twice = {}
    for path in sorted((ROOT / "backend").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = Counter(node.name for node in tree.body
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)))
        repeated = sorted(name for name, count in names.items() if count > 1)
        if repeated:
            twice[path.relative_to(ROOT).as_posix()] = repeated
    assert not twice, f"defined twice, as when a merge keeps both copies: {twice}"
