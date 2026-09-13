import contextlib
import logging
import time

from odoo import models, tools
from odoo.libs.asset_log import get_asset_logger, log_event
from odoo.libs.debug_log import DebugLog
from odoo.modules import module as _module
from odoo.tools.assets.esbuild_policy import EsbuildCircuit

_fallback_log = get_asset_logger("fallback")
_lock_log = get_asset_logger("lock")

_esbuild_circuit = EsbuildCircuit()
_debug = DebugLog(__name__)


class IrQweb(models.AbstractModel):
    _inherit = "ir.qweb"

    _esbuild_circuit = _esbuild_circuit
    _ESBUILD_COOLDOWN_S: float = 60.0
    _ESBUILD_EXTENDED_COOLDOWN_S: float = 600.0

    def _get_esbuild_config(self):
        return self.env["ir.config_parameter"].sudo()

    def _is_esbuild_fail_closed(self) -> bool:
        default = bool(  # debuglog
            tools.config["test_enable"] or "assets" in tools.config["dev_mode"]
        )
        fail_closed = self._get_esbuild_config().get_param_bool(  # debuglog
            "web.esbuild.fail_closed", default
        )
        _debug.logic("esbuild.fail_closed", value=fail_closed, default=default)
        return fail_closed

    def _get_esbuild_bundles_forced_fallback(self) -> set[str]:
        forced_raw = self._get_esbuild_config().get_param(
            "web.esbuild.force_fallback_bundles", ""
        )
        return {s.strip() for s in forced_raw.split(",") if s.strip()}

    def _get_esbuild_cooldown_key(self, bundle: str) -> tuple[str, str]:
        return (self.env.cr.dbname, bundle)

    def _get_esbuild_circuit_state(self, bundle: str) -> tuple[bool, str]:
        state = _esbuild_circuit.state(  # debuglog
            self._get_esbuild_cooldown_key(bundle), now=time.monotonic()
        )
        _debug.logic(
            "esbuild.circuit_state", bundle=bundle, open=state[0], reason=state[1]
        )
        return state

    def _open_esbuild_circuit(self, bundle: str, reason: str) -> None:
        config = self._get_esbuild_config()
        now = time.monotonic()
        entry = _esbuild_circuit.record_failure(
            self._get_esbuild_cooldown_key(bundle),
            reason,
            now=now,
            cooldown_s=config.get_param_float(
                "web.esbuild.cooldown_s", self._ESBUILD_COOLDOWN_S
            ),
            extended_cooldown_s=config.get_param_float(
                "web.esbuild.extended_cooldown_s", self._ESBUILD_EXTENDED_COOLDOWN_S
            ),
        )
        log_event(
            _fallback_log,
            logging.WARNING,
            "circuit_open",
            bundle=bundle,
            reason=reason,
            cooldown_s=entry.expiry - now,
            fails=entry.failures,
        )

    def _close_esbuild_circuit(self, bundle: str) -> None:
        if _esbuild_circuit.record_success(self._get_esbuild_cooldown_key(bundle)):
            log_event(
                _fallback_log,
                logging.INFO,
                "circuit_close",
                bundle=bundle,
            )

    _ESBUILD_LOCK_RETRIES: int = 1
    _ESBUILD_LOCK_RETRY_SLEEP_S: float = 0.2

    @contextlib.contextmanager
    def _get_esbuild_lock_cursor(self, bundle: str):
        if self.env.cr.readonly and _module.current_test:
            _debug.logic("esbuild.lock_cursor", bundle=bundle, mode="test_readonly")
            yield self.env.cr
            return
        try:
            rw_cr = self.env.registry.cursor(readonly=False)
        except Exception:
            log_event(
                _lock_log,
                logging.WARNING,
                "rw_cursor_unavailable",
                bundle=bundle,
            )
            yield None
            return
        try:
            yield rw_cr
        finally:
            rw_cr.rollback()
            rw_cr.close()

    def _acquire_esbuild_lock(self, bundle: str, cr=None) -> bool:
        if cr is None:
            cr = self.env.cr
        config = self._get_esbuild_config()
        retries = config.get_param_int(
            "web.esbuild.lock_retries", self._ESBUILD_LOCK_RETRIES
        )
        sleep_s = config.get_param_float(
            "web.esbuild.lock_retry_sleep_s", self._ESBUILD_LOCK_RETRY_SLEEP_S
        )
        key = f"esbuild:{bundle}"
        for attempt in range(retries + 1):
            cr.execute(
                "SELECT pg_try_advisory_xact_lock(hashtext(%s))",
                (key,),
            )
            got = cr.fetchone()[0]
            if got:
                log_event(
                    _lock_log,
                    logging.DEBUG,
                    "acquired",
                    bundle=bundle,
                    attempt=attempt,
                )
                return True
            if attempt < retries:
                time.sleep(sleep_s)
        log_event(
            _lock_log,
            logging.INFO,
            "contention",
            bundle=bundle,
            attempts=retries + 1,
        )
        if _debug.logic.enabled:
            cr.execute(
                """
                SELECT a.pid, a.application_name, a.state, a.backend_start,
                       a.xact_start, left(a.query, 300)
                  FROM pg_locks l
                  JOIN pg_stat_activity a ON a.pid = l.pid
                 WHERE l.locktype = 'advisory'
                   AND l.granted
                   AND l.database = (SELECT oid FROM pg_database WHERE datname = current_database())
                   AND l.objid::bigint = hashtext(%s)::bigint & 4294967295
                """,
                (key,),
            )
            _debug.logic(
                "esbuild.lock_holders",
                bundle=bundle,
                own_pid=getattr(cr, "_backend_pid", None),
                holders=cr.fetchall(),
            )
        return False
