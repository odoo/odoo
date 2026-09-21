import logging

from odoo.db.schema import table_exists
from odoo.libs.sql.builder import SQL

_logger = logging.getLogger(__name__)

# The access log's verdict vocabulary, as the caller's problem document names it.
_CODE_BY_OUTCOME = {
    "unauthenticated": "authentication_failed",
    "address_refused": "ip_not_allowed",
    "rate_limited": "rate_limit_exceeded",
    "unknown_receiver": "endpoint_not_found",
    "caller_limited": "caller_limited",
    "misconfigured": "misconfigured",
    "payload_too_large": "payload_too_large",
}


def migrate(cr, version):
    if not version or not table_exists(cr, "inbound_access_log"):
        return
    codes = SQL(", ").join(
        SQL("(%s, %s)", outcome, code) for outcome, code in _CODE_BY_OUTCOME.items()
    )
    cr.execute(
        SQL(
            """
            INSERT INTO integration_exchange (
                create_uid, write_uid, create_date, write_date,
                direction, channel_id, channel_name, display_name, company_id,
                timestamp, date_completed, last_seen_at, attempt_count,
                state, refusal_reason, status_code, status_category, is_success,
                error_message, error_type, source_ip, user_agent, auth_mode,
                signature_verified, retry_count, cache_hit, duration_ms
            )
            SELECT
                1, 1, l.create_date, l.write_date,
                'inbound',
                CASE WHEN l.gate_id > 0 THEN l.gate_model || ',' || l.gate_id END,
                CASE WHEN l.gate_id > 0 THEN COALESCE(l.gate_name, l.gate_model)
                     ELSE l.gate_model || ': ' || COALESCE(l.gate_name, '?') END,
                CASE WHEN l.gate_id > 0 THEN COALESCE(l.gate_name, l.gate_model)
                     ELSE l.gate_model || ': ' || COALESCE(l.gate_name, '?') END
                    || ': ' || c.code || ' from '
                    || COALESCE(l.source_ip, 'unknown source')
                    || CASE WHEN l.attempt_count > 1 THEN ' ×' || l.attempt_count ELSE '' END,
                l.company_id,
                l.timestamp, l.timestamp, COALESCE(l.last_seen_at, l.timestamp),
                COALESCE(l.attempt_count, 1),
                'refused', c.code, l.status_code,
                CASE WHEN l.status_code >= 500 THEN 'server_error' ELSE 'client_error' END,
                FALSE,
                l.reason, 'other', l.source_ip, l.user_agent, COALESCE(l.mode, 'enforce'),
                FALSE, 0, FALSE, 0
            FROM inbound_access_log l
            JOIN (VALUES %s) AS c(outcome, code) ON c.outcome = l.outcome
            WHERE NOT l.allowed
            ORDER BY l.id
            """,
            codes,
        )
    )
    _logger.info(
        "integration 1.35.0: %d refusals of the inbound access log are exchange rows",
        cr.rowcount,
    )
    cr.execute("DROP TABLE inbound_access_log")
