"""Odoo-side consumer for the ``invoice.result`` AMQP queue.

The aio-pika worker publishes two kinds of messages to ``invoice.result``:

* ``extract.started`` — body ``{"job_uuid": ..., "move_id": N,
  "status": "extracting"}`` → live *extracting* status via ``bus.bus``.
* ``extract.done``    — body ``{"token": "<jwt>"}`` where the JWT claims
  carry the extraction result. Verify the signature (shared secret from
  ``ir.config_parameter`` / ``invoice_agent.jwt_secret``), resolve the
  ``account.move`` by ``ai_job_uuid``, write header + line fields in a
  **fresh** ``api.Environment`` cursor, then push a *ready* bus.bus event.

Why a daemon thread (started from ``post_load``) and not an Odoo
``ir.cron``: the cron runs in the long-polling worker and blocks one
worker per message; a consumer thread owns its own read loop. Why a fresh
cursor per result: the thread outlives any request transaction, so each
write goes through ``registry.cursor()`` and commits immediately.
"""

import contextlib
import json
import logging
import os
import threading
import time

_logger = logging.getLogger(__name__)

try:
    import pika
    import pika.exceptions

    _PIKA_AVAILABLE = True
except ImportError:  # pragma: no cover — stale image without pika
    pika = None  # type: ignore[assignment]
    _PIKA_AVAILABLE = False

EXCHANGE_NAME = "invoice.agent"
QUEUE_RESULT = "invoice.result"
ROUTING_KEY_STARTED = "extract.started"
ROUTING_KEY_DONE = "extract.done"

# Result JWT audience/subject — must match invoice-ai/app/result_signing.py
RESULT_AUDIENCE = "odoo.invoice-agent"
RESULT_ISSUER = "invoice-ai"
RESULT_SUBJECT = "extract.done"


def _connection_params():
    host = os.environ.get("RABBITMQ_HOST", "rabbitmq")
    port = int(os.environ.get("RABBITMQ_PORT", "5672"))
    user = os.environ.get("RABBITMQ_USER", "guest")
    password = os.environ.get("RABBITMQ_PASS", "guest")
    return pika.ConnectionParameters(
        host=host,
        port=port,
        credentials=pika.PlainCredentials(user, password),
        heartbeat=60,
        blocked_connection_timeout=30,
    )


# ---------------------------------------------------------------------------
# Apply helpers (module-level; called with an account.move recordset)
# ---------------------------------------------------------------------------
def _apply_queue_result(move, result):
    """Apply a verified worker result onto ``move``.

    ``result`` is the decoded JWT result dict::

        {"job_uuid", "move_id", "status": "done",
         "parsed_output": InvoiceExtraction.json, "usage", "model"}
    """
    payload = result.get("parsed_output") or {}
    if not isinstance(payload, dict):
        msg = "parsed_output must be a JSON object"
        raise ValueError(msg)
    move.ensure_one()

    # Score through the calibrated blend (self-report + arithmetic +
    # VAT/IBAN rescue) — identical to the synchronous path.
    score, details = move.env["invoice.llm.service"].score_extraction(
        payload,
        ocr_text=move.ocr_text or move.ai_ocr_text,
        ocr_confidence=move.ocr_confidence,
    )
    payload = details.get("rescued_payload") or payload

    # Resolve the vendor (VAT first, fuzzy name second).
    partner = move.env["res.partner"]
    if payload.get("vendor_vat"):
        partner = partner.search(
            [("vat", "=", payload["vendor_vat"]), ("parent_id", "=", False)],
            limit=1,
        )
    if not partner and payload.get("vendor_name"):
        partner = partner.search(
            [("name", "ilike", payload["vendor_name"]), ("parent_id", "=", False)],
            limit=1,
        )

    vals = {
        "ai_extracted_json": payload,
        "extraction_json": json.dumps(payload, default=str),
        "ai_extracted_total": payload.get("amount_total"),
        "ai_confidence": score,
        "ai_review_required": bool(payload.get("review_required")),
        "ai_extraction_status": "extracted",
        "ai_state": "none",  # job round-trip complete
        "ai_model_used": result.get("model"),
        "extraction_model": result.get("model"),
    }
    if partner:
        vals["partner_id"] = partner.id
    for field_name, payload_key in (
        ("invoice_date", "invoice_date"),
        ("invoice_date_due", "due_date"),
        ("ref", "ref"),
    ):
        if payload.get(payload_key):
            vals[field_name] = payload[payload_key]

    line_vals = []
    for line in payload.get("lines") or []:
        if not isinstance(line, dict):
            continue
        try:
            price_unit = float(line.get("price_unit") or 0.0)
            quantity = float(line.get("quantity") or 1.0)
        except (TypeError, ValueError):
            price_unit = 0.0
            quantity = 1.0
        line_vals.append(
            (
                0,
                0,
                {
                    "name": line.get("name") or "Imported line",
                    "price_unit": price_unit,
                    "quantity": quantity,
                    "ai_confidence": line.get("confidence"),
                },
            ),
        )
    if line_vals:
        vals["invoice_line_ids"] = line_vals
    move.write(vals)

    # --- Phase 2: Apply validation verdict (if present) ---
    validation = result.get("validation")
    if isinstance(validation, dict) and validation.get("account_id"):
        move._apply_validation_verdict(validation)

    # Route: sub-threshold or pipeline-flagged extractions land in Needs
    # Review with the reason on the chatter.
    threshold = move._get_ai_min_confidence()
    if move.ai_review_required or score < threshold:
        move._flag_needs_review(
            reason=(
                f"worker extraction confidence {score * 100:.0f}% is below the {threshold * 100:.0f}% "
                "routing threshold"
            ),
        )

    # Persist the token/cost ledger row.
    try:
        move.env["invoice.llm.service"].log_usage(
            move.id,
            result.get("usage") or {},
            model=result.get("model"),
        )
    except Exception:
        _logger.exception(
            "invoice_agent failed to log queue-result usage for move_id=%s",
            move.id,
        )
    _logger.info(
        "invoice_agent queue result applied: move_id=%d score=%.2f",
        move.id,
        score,
    )
    return True


def _publish_live_status(move, status, payload=None):
    """Push a live status notification to move followers via ``bus.bus``."""
    move.ensure_one()
    try:
        partners = move.message_partner_ids
        if not partners and move.partner_id:
            partners = move.partner_id
        notification = {
            "type": "invoice_agent_status",
            "status": status,
            "move_id": move.id,
            "job_uuid": move.ai_job_uuid,
            "display_name": move.display_name,
        }
        if payload:
            notification["payload"] = payload
        if not partners:
            return
        move.env["bus.bus"]._sendone(partners, "invoice_agent", notification)
        _logger.info(
            "invoice_agent live status: move_id=%d status=%s",
            move.id,
            status,
        )
    except Exception:
        _logger.exception(
            "invoice_agent failed to publish live status for move_id=%d",
            move.id,
        )


class _InvoiceAgentResultConsumer:
    """One daemon thread per Odoo process: reads ``invoice.result``."""

    def __init__(self):
        self._thread = None

    def start(self):
        if not _PIKA_AVAILABLE:
            _logger.warning(
                "invoice_agent: pika not installed — result consumer disabled",
            )
            return
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run,
            name="invoice-agent-result-consumer",
            daemon=True,
        )
        self._thread.start()
        _logger.info("invoice_agent: result consumer thread started")

    def _run(self):
        try:
            self._consume_loop()
        except Exception as exc:
            _logger.warning("invoice_agent: result consumer died: %s", exc)

    def _consume_loop(self):
        while True:
            try:
                connection = pika.SelectConnection(
                    _connection_params(),
                    on_open_callback=self._on_open,
                )
                connection.ioloop.start()
            except (pika.exceptions.AMQPError, OSError) as exc:
                _logger.warning(
                    "invoice_agent: result consumer broker error — retrying in 5s: %s",
                    exc,
                )
            time.sleep(5)

    def _on_open(self, connection):
        channel = connection.channel()
        channel.basic_qos(prefetch_count=10)
        channel.queue_declare(queue=QUEUE_RESULT, durable=True)
        channel.queue_bind(
            queue=QUEUE_RESULT,
            exchange=EXCHANGE_NAME,
            routing_key=ROUTING_KEY_STARTED,
        )
        channel.queue_bind(
            queue=QUEUE_RESULT,
            exchange=EXCHANGE_NAME,
            routing_key=ROUTING_KEY_DONE,
        )
        channel.basic_consume(
            QUEUE_RESULT,
            self._on_message,
            consumer_tag="invoice-agent",
        )

    def _on_message(self, channel, method, properties, body):
        try:
            payload = json.loads(body or b"{}")
            if method.routing_key == ROUTING_KEY_STARTED:
                self._handle_started(payload)
            elif method.routing_key == ROUTING_KEY_DONE:
                self._handle_done(payload)
            else:
                _logger.warning(
                    "invoice_agent: unexpected routing key %s",
                    method.routing_key,
                )
        except Exception as exc:
            _logger.error("invoice_agent: result message error: %s", exc)
        finally:
            channel.basic_ack(delivery_tag=method.delivery_tag)

    def _handle_started(self, payload):
        import odoo

        registry = odoo.registry(odoo.tools.config["db_name"])
        cursor = registry.cursor()
        try:
            env = odoo.api.Environment(cursor, odoo.SUPERUSER_ID, {})
            move = self._resolve_move(env, payload)
            if not move:
                return
            _publish_live_status(move, "extracting", payload)
            cursor.commit()
        except Exception as exc:
            _logger.warning("invoice_agent: extract.started failed: %s", exc)
        finally:
            cursor.close()

    def _handle_done(self, payload):
        import odoo

        registry = odoo.registry(odoo.tools.config["db_name"])
        cursor = registry.cursor()
        try:
            env = odoo.api.Environment(cursor, odoo.SUPERUSER_ID, {})
            result = self._verify_result(env, payload)
            if result is None:
                return  # signature/audience rejected — never applied
            if result.get("status") == "failed":
                # The worker dead-lettered the job. Mark the outbox row dead,
                # flag the move for review — nothing is applied, and a
                # redelivered failure is a no-op via the ledger below.
                self._handle_failed_result(env, result)
                cursor.commit()
                return
            if not self._claim_job_uuid(env, result):
                # Idempotency guard (v0.9): a redelivered done-result for an
                # already-applied job_uuid is a no-op — never a second draft.
                _logger.info(
                    "invoice_agent: duplicate result for uuid=%s — skipped",
                    result.get("job_uuid"),
                )
                cursor.commit()
                return
            move = self._resolve_move(env, result)
            if not move:
                _logger.warning(
                    "invoice_agent: no move for result uuid=%s",
                    result.get("job_uuid"),
                )
                cursor.rollback()
                return
            _apply_queue_result(move, result)
            _publish_live_status(move, "ready", result)
            cursor.commit()
        except Exception as exc:
            _logger.warning("invoice_agent: extract.done failed: %s", exc)
            with contextlib.suppress(Exception):
                cursor.rollback()
        finally:
            cursor.close()

    def _claim_job_uuid(self, env, result):
        """Idempotency guard — INSERT ... ON CONFLICT DO NOTHING on the ledger.

        Returns True when this delivery is the first (or the job was never
        applied before); False when the job_uuid is already in the ledger —
        the redelivered message must be a no-op.

        Uses raw SQL so the dedupe is a single atomic statement that commits
        in the same transaction as the apply: a crash mid-apply leaves no
        ledger row and the next redelivery retries safely.
        """
        job_uuid = result.get("job_uuid")
        if not job_uuid:
            _logger.warning("invoice_agent: result carries no job_uuid — skipped")
            return False
        env.cr.execute(
            """
            INSERT INTO invoice_agent_applied_job (job_uuid, applied_at)
            VALUES (%s, NOW())
            ON CONFLICT (job_uuid) DO NOTHING
            """,
            (job_uuid,),
        )
        return env.cr.rowcount > 0

    def _handle_failed_result(self, env, result):
        """Mark the originating job dead + flag the move on a failed result.

        The worker publishes a signed ``status:"failed"`` result when it
        dead-letters a poison message. This marks the outbox row dead (so the
        taskboard shows it) and flags the move for review.
        """
        job_uuid = result.get("job_uuid")
        error = result.get("error") or ""
        if job_uuid:
            env["invoice.agent.job"]._mark_dead(job_uuid, reason=error)
        move = self._resolve_move(env, result)
        if move:
            move.write(
                {
                    "ai_extraction_status": "failed",
                    "ai_error_message": error[:2000] if error else False,
                }
            )
            try:
                move._flag_needs_review(
                    reason=f"extraction was dead-lettered by the worker: {error}",
                )
            except Exception:
                _logger.exception(
                    "invoice_agent: failed to flag move_id=%d for review",
                    move.id,
                )
            _publish_live_status(move, "failed", result)
        _logger.warning(
            "invoice_agent: failed result for uuid=%s: %s",
            job_uuid,
            error[:200] if error else "no error detail",
        )

    def _verify_result(self, env, payload):
        import jwt
        from jwt.exceptions import InvalidTokenError

        from .llm_service import JWT_SECRET_PARAM

        secret = env["ir.config_parameter"].sudo().get_param(JWT_SECRET_PARAM)
        token = payload.get("token") or ""
        if not secret or not token:
            _logger.warning("invoice_agent: missing secret/token for result")
            return None
        try:
            claims = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                audience=RESULT_AUDIENCE,
                leeway=10,
                issuer=RESULT_ISSUER,
            )
        except InvalidTokenError as exc:
            _logger.warning("invoice_agent: rejected result token: %s", exc)
            return None
        if claims.get("sub") != RESULT_SUBJECT:
            _logger.warning("invoice_agent: result token wrong subject")
            return None
        result = claims.get("result")
        if not isinstance(result, dict):
            _logger.warning("invoice_agent: result token carries no payload")
            return None
        return result

    def _resolve_move(self, env, payload):
        move_model = env["account.move"]
        job_uuid = payload.get("job_uuid")
        move_id = payload.get("move_id")
        if job_uuid:
            move = move_model.search([("ai_job_uuid", "=", job_uuid)], limit=1)
            if move:
                return move
        if move_id:
            move = move_model.browse(move_id)
            if move.exists():
                return move
        return None


# ---------------------------------------------------------------------------
# Module-level singleton + post_load hook
# ---------------------------------------------------------------------------
_consumer = _InvoiceAgentResultConsumer()


def start_result_consumer():
    """Start the consumer thread (idempotent). Called from post_load."""
    _consumer.start()


__all__ = ["start_result_consumer"]
