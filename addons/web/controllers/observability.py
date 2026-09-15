import heapq
import logging
import math
import threading
import time

from odoo import modules
from odoo.http import Controller, Response, request, route
from odoo.libs.json import loads as json_loads
from odoo.tools import config

from ..tools import debug_log as dbg

_logger = logging.getLogger(__name__)

_RATE_LIMIT_WINDOW_S = 60
_RATE_LIMIT_MAX = 120
_RATE_LIMIT_MAX_KEYS = 10_000
_rate_lock = threading.Lock()
_rate_state: dict[str, list[float]] = {}


def _is_rate_limited(key: str) -> bool:
    now = time.monotonic()
    with _rate_lock:
        if len(_rate_state) > _RATE_LIMIT_MAX_KEYS:
            cutoff = now - _RATE_LIMIT_WINDOW_S
            before = len(_rate_state)
            for stale in [k for k, v in _rate_state.items() if v[0] < cutoff]:
                del _rate_state[stale]
            dbg.performance.debug(
                "[rate] sweep: %d keys -> %d after stale eviction",
                before,
                len(_rate_state),
            )
            if len(_rate_state) > _RATE_LIMIT_MAX_KEYS:
                low_water = _RATE_LIMIT_MAX_KEYS * 9 // 10
                evict_n = len(_rate_state) - low_water
                dbg.logic.debug(
                    "[rate] sweep: still %d keys, evict %d oldest",
                    len(_rate_state),
                    evict_n,
                )
                for k in heapq.nsmallest(
                    evict_n, _rate_state, key=lambda k: _rate_state[k][0]
                ):
                    del _rate_state[k]
        state = _rate_state.get(key)
        if state is None or now - state[0] >= _RATE_LIMIT_WINDOW_S:
            if state is not None:
                dbg.logic.debug("[rate] %s: window expired after %d", key, state[1])
            _rate_state[key] = [now, 1]
            return False
        if state[1] >= _RATE_LIMIT_MAX:
            dbg.logic.debug("[rate] %s: limited at %d", key, state[1])
            return True
        state[1] += 1
        return False


def _get_client_rate_key(prefix: str) -> str:
    uid = request.session.uid
    ident = f"uid:{uid}" if uid else f"ip:{request.httprequest.remote_addr or 'anon'}"
    return f"{prefix}:{ident}"


_MAX_LATENCY_MS = 60_000
_MAX_CLS = 5.0
_MAX_URL_LEN = 500
_MAX_UA_LEN = 500
_MAX_ERROR_MSG_LEN = 4_096
_MAX_ERROR_STACK_LEN = 4_096
_MAX_ERROR_CAUSE_LEN = 4_096
_MAX_ERROR_FILENAME_LEN = 500

_JS_ERROR_KINDS = frozenset(
    {
        "error",
        "unhandledrejection",
        "module_rebind",
        "service_start",
        "asset_load_error",
    }
)
_JS_ERROR_PHASES = frozenset({"pre_boot", "post_boot", "boot_mount_failed"})


def _get_clamped_metric(value, maximum: float) -> float | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    if not math.isfinite(value) or value < 0 or value > maximum:
        return None
    return float(value)


def _get_capped_str(raw, cap: int) -> str:
    return raw[:cap] if isinstance(raw, str) else ""


def _get_positive_int(raw) -> int:
    return int(raw) if isinstance(raw, (int, float)) and raw >= 0 else 0


def _read_beacon_payload(prefix: str) -> tuple[dict | None, Response | None]:
    dbg.lifecycle.debug(
        "[%s] beacon: %s bytes=%d",
        prefix,
        dbg.req(),
        len(request.httprequest.data or b""),
    )
    if _is_rate_limited(_get_client_rate_key(prefix)):
        dbg.logic.debug("[%s] beacon: rate limited -> 429", prefix)
        return None, Response("", status=429, mimetype="text/plain")
    try:
        payload = json_loads(request.httprequest.data or b"{}")
    except ValueError, TypeError:
        dbg.logic.debug("[%s] beacon: invalid json -> 400", prefix)
        return None, Response("invalid json", status=400, mimetype="text/plain")
    if not isinstance(payload, dict):
        dbg.logic.debug(
            "[%s] beacon: payload is %s -> 400", prefix, type(payload).__name__
        )
        return None, Response("invalid payload", status=400, mimetype="text/plain")
    return payload, None


def _prepare_js_error_values(payload: dict) -> dict | None:
    message = _get_capped_str(payload.get("message"), _MAX_ERROR_MSG_LEN)
    if not message:
        return None

    kind = payload.get("kind") if payload.get("kind") in _JS_ERROR_KINDS else "error"

    return {
        "message": message,
        "kind": kind,
        "phase": (
            payload.get("phase")
            if payload.get("phase") in _JS_ERROR_PHASES
            else "unknown"
        ),
        "filename": _get_capped_str(payload.get("filename"), _MAX_ERROR_FILENAME_LEN),
        "url": _get_capped_str(payload.get("url"), _MAX_URL_LEN),
        "user_agent": _get_capped_str(payload.get("user_agent"), _MAX_UA_LEN),
        "stack": _get_capped_str(payload.get("stack"), _MAX_ERROR_STACK_LEN),
        "cause": _get_capped_str(payload.get("cause"), _MAX_ERROR_CAUSE_LEN),
        "line": _get_positive_int(payload.get("line")),
        "col": _get_positive_int(payload.get("col")),
        "reloaded": (
            bool(payload.get("reloaded"))
            if kind == "asset_load_error" and "reloaded" in payload
            else None
        ),
    }


class Observability(Controller):
    @route(
        "/web/observability/cwv",
        type="http",
        auth="public",
        sitemap=False,
        methods=["POST"],
        csrf=False,
    )
    def cwv(self) -> Response:  # noqa: E8528 - a sendBeacon telemetry post, which cannot carry a CSRF token
        payload, refusal = _read_beacon_payload("cwv")
        if refusal is not None:
            return refusal

        lcp = _get_clamped_metric(payload.get("lcp"), _MAX_LATENCY_MS)
        fcp = _get_clamped_metric(payload.get("fcp"), _MAX_LATENCY_MS)
        ttfb = _get_clamped_metric(payload.get("ttfb"), _MAX_LATENCY_MS)
        inp = _get_clamped_metric(payload.get("inp"), _MAX_LATENCY_MS)
        cls = _get_clamped_metric(payload.get("cls"), _MAX_CLS)
        url = _get_capped_str(payload.get("url"), _MAX_URL_LEN).split("?", 1)[0]
        user_agent = _get_capped_str(payload.get("user_agent"), _MAX_UA_LEN)
        pageview_id = _get_capped_str(payload.get("pageview_id"), 64)

        if lcp is None and fcp is None and ttfb is None and cls is None and inp is None:
            dbg.logic.debug("[cwv] beacon: no metric survived clamping -> 204")
            return Response("", status=204)

        if not url:
            dbg.logic.debug("[cwv] beacon: no url -> 204")
            return Response("", status=204)

        uid = request.session.uid or False
        _logger.info(
            "[cwv] uid=%s url=%r lcp=%s fcp=%s cls=%s ttfb=%s inp=%s ua=%r",
            uid or "anon",
            url,
            lcp,
            fcp,
            cls,
            ttfb,
            inp,
            user_agent,
        )
        Metric = request.env["web.cwv.metric"].sudo()
        values = {
            "url": url,
            "user_id": uid,
            "lcp": lcp,
            "fcp": fcp,
            "cls": cls,
            "ttfb": ttfb,
            "inp": inp,
            "user_agent": user_agent or False,
            "pageview_id": pageview_id or False,
        }
        with dbg.timer(request.env, "[cwv] record beacon pageview=%s", pageview_id):
            Metric._record_beacon(values)
        return Response("", status=204)

    @route(
        "/web/observability/js_error",
        type="http",
        auth="public",
        sitemap=False,
        methods=["POST"],
        csrf=False,
    )
    def js_error(self) -> Response:  # noqa: E8528 - a sendBeacon telemetry post, which cannot carry a CSRF token
        payload, refusal = _read_beacon_payload("js_error")
        if refusal is not None:
            return refusal

        beacon = _prepare_js_error_values(payload)
        if beacon is None:
            dbg.logic.debug("[js_error] beacon: no message -> 204")
            return Response("", status=204)

        uid = request.session.uid or False
        in_test = bool(modules.module.current_test) or config["test_enable"]
        level = (
            logging.DEBUG
            if beacon["kind"] == "module_rebind" and in_test
            else logging.WARNING
        )
        dbg.logic.debug(
            "[js_error] beacon: kind=%s phase=%s in_test=%s -> level=%s",
            beacon["kind"],
            beacon["phase"],
            in_test,
            logging.getLevelName(level),
        )
        _logger.log(
            level,
            "[js_error] uid=%s phase=%s kind=%s reloaded=%s msg=%r cause=%r"
            " at %r:%d:%d url=%r ua=%r stack=%r",
            uid or "anon",
            beacon["phase"],
            beacon["kind"],
            beacon["reloaded"],
            beacon["message"],
            beacon["cause"],
            beacon["filename"],
            beacon["line"],
            beacon["col"],
            beacon["url"],
            beacon["user_agent"],
            beacon["stack"],
        )
        reloaded = beacon["reloaded"]
        with dbg.timer(request.env, "[js_error] record beacon kind=%s", beacon["kind"]):
            request.env["web.js.error"].sudo()._record_beacon(
                {
                    "user_id": uid,
                    **beacon,
                    "reloaded": (
                        None
                        if reloaded is None
                        else ("reloaded" if reloaded else "suppressed")
                    ),
                }
            )
        return Response("", status=204)
