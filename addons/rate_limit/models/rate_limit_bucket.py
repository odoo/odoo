import logging
from datetime import timedelta
from typing import Any

from odoo import api, fields, models
from odoo.db import get_or_create_row
from odoo.exceptions import UserError
from odoo.libs import token_bucket
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY

from ..tools.caller_rate_limiter import get_caller_rate_limiter

_logger = logging.getLogger(__name__)

MAX_REFILL_SECONDS = 3600


class RateLimitBucket(models.Model):
    _name = "rate.limit.bucket"
    _description = "Rate Limit Token Bucket"
    _rec_name = "bucket_key"

    bucket_key = fields.Char(
        index=True,
        required=True,
        help="Unique key format: model:record_id:company_id or model:record_id:global",
    )
    endpoint_model = fields.Char(
        index=True,
        required=True,
        help="Model name of the rate-limited endpoint (e.g., 'webhook.subscription')",
    )
    endpoint_id = fields.Integer(
        string="Endpoint Record ID",
        index=True,
        required=True,
        help="Database ID of the rate-limited endpoint record",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        index=True,
        help="Company for per-company rate limiting. Empty = endpoint-wide limit.",
    )
    tokens = fields.Float(
        string="Available Tokens",
        default=0.0,
        help="Current number of available tokens in bucket",
    )
    last_refill = fields.Datetime(
        string="Last Refill Time",
        default=fields.Datetime.now,
        help="Timestamp of last token refill",
    )
    last_request_at = fields.Datetime(
        string="Last Request",
        help="Timestamp of last request using this bucket",
    )
    can_reset = fields.Boolean(
        compute="_compute_can_reset",
        help="Whether the endpoint this bucket belongs to can still be "
        "resolved, so a manual reset can look up its capacity.",
    )

    _bucket_key_uniq = models.Constraint(
        "unique(bucket_key)",
        "Rate limit bucket key must be unique!",
    )

    _PERIOD_SECONDS = {
        "second": 1,
        "minute": 60,
        "hour": 3600,
        "day": 86400,
    }

    def _get_period_seconds(self, period: str) -> int:
        try:
            return self._PERIOD_SECONDS[period]
        except KeyError as exc:
            raise ValueError(
                f"Unknown rate-limit period {period!r} "
                f"(valid: {sorted(self._PERIOD_SECONDS)})"
            ) from exc

    def _get_endpoint_config(self) -> tuple[int, int, float]:
        self.check_singleton()

        if self.endpoint_model not in self.env:
            raise ValueError(
                f"Endpoint model {self.endpoint_model!r} not in registry "
                f"(bucket {self.bucket_key}). The owning module may have "
                f"been uninstalled; GC this bucket."
            )

        endpoint = self.env[self.endpoint_model].browse(self.endpoint_id)
        if not endpoint.exists():
            raise ValueError(
                f"Endpoint {self.endpoint_model}:{self.endpoint_id} not "
                f"found (bucket {self.bucket_key})."
            )

        max_requests = getattr(endpoint, "rate_limit_requests", None)
        if max_requests is None:
            max_requests = 100

        period_seconds = None
        candidate = getattr(endpoint, "rate_limit_window_seconds", None)
        if candidate is not None and candidate > 0:
            period_seconds = candidate
        else:
            period = getattr(endpoint, "rate_limit_period", None) or "minute"
            period_seconds = self._get_period_seconds(period)

        refill_rate = (max_requests / period_seconds) if period_seconds else 0.0

        return max_requests, period_seconds, refill_rate

    @api.model
    def consume_for(
        self,
        endpoint_record: Any,
        company_id: int | None = None,
        strict: bool = False,
    ) -> bool:
        bucket = self.sudo().get_or_create_bucket(endpoint_record, company_id)
        return bucket.consume_token(strict=strict)

    @api.model
    def consume_for_key(
        self,
        bucket_key: str,
        *,
        subject_model: str,
        subject_id: int = 0,
        capacity: float,
        refill_rate: float | None = None,
        window_seconds: int = 60,
        strict: bool = False,
        company_id: int | None = None,
    ) -> bool:
        """Consume a token for a subject that is not an endpoint record.

        ``consume_for`` needs something with ``_name``, ``id`` and
        ``rate_limit_requests``, which is right when the thing being limited is
        a configured endpoint. It is not the only thing worth limiting: a user
        id, a peer address and a chat are all rate-limit subjects that no record
        represents, and both callers that had one built a ``SimpleNamespace``
        carrying exactly those three attributes to get past the signature. Two
        independent fakes of one record is the signature asking for this method.

        ``subject_model``/``subject_id`` are what lands in the row's
        ``endpoint_model``/``endpoint_id`` columns, which are required and are
        how ``cron_gc_old_buckets`` and the views group buckets. Name a subject
        namespace there (``mcp_server.ip``), not a model that must resolve --
        nothing browses it, because ``capacity`` and ``refill_rate`` are passed
        explicitly and so ``_get_endpoint_config`` never runs.

        :param bucket_key: the bucket's identity, unique across all subjects
        :param capacity: bucket size, in tokens
        :param refill_rate: tokens per second; defaults to filling ``capacity``
            once per ``window_seconds``
        :param strict: refuse rather than allow when the bucket cannot be read
        """
        if refill_rate is None:
            refill_rate = capacity / window_seconds if window_seconds else 0.0
        bucket = self.sudo()._get_or_create_by_key(
            bucket_key,
            subject_model=subject_model,
            subject_id=subject_id,
            company_id=company_id,
            capacity=capacity,
        )
        return bucket.consume_token(
            strict=strict, capacity=capacity, refill_rate=refill_rate
        )

    @api.model
    def get_or_create_bucket(
        self,
        endpoint_record: Any,
        company_id: int | None = None,
        bucket_key: str | None = None,
    ) -> Any:
        company_part = company_id or "global"
        bucket_key = (
            bucket_key or f"{endpoint_record._name}:{endpoint_record.id}:{company_part}"
        )
        max_requests = getattr(endpoint_record, "rate_limit_requests", None)
        return self._get_or_create_by_key(
            bucket_key,
            subject_model=endpoint_record._name,
            subject_id=endpoint_record.id,
            company_id=company_id,
            capacity=100 if max_requests is None else max_requests,
        )

    @api.model
    def _get_or_create_by_key(
        self,
        bucket_key: str,
        *,
        subject_model: str,
        subject_id: int,
        company_id: int | None,
        capacity: float,
    ) -> Any:
        """The one creation path, racing safely against a concurrent caller.

        Through ``odoo.db.get_or_create_row``, which is the framework's own
        spelling of this: insert inside a *flushing* savepoint, and on
        ``UniqueViolation`` return the row the winner created. The hand-rolled
        version here opened a bare ``SAVEPOINT`` and let the ORM defer the
        INSERT, so the violation escaped the guard and surfaced somewhere else
        entirely -- and its recovery ran ``search()`` after a rollback the ORM
        cache knew nothing about. A flushing savepoint restores that cache; a
        bare one cannot.
        """
        bucket = self.search([("bucket_key", "=", bucket_key)], limit=1)
        if bucket:
            return bucket

        bucket, created = get_or_create_row(
            self.env.cr,
            lambda: self.create(
                {
                    "bucket_key": bucket_key,
                    "endpoint_model": subject_model,
                    "endpoint_id": subject_id,
                    "company_id": company_id,
                    "tokens": capacity,
                    "last_refill": fields.Datetime.now(),
                },
            ),
            lambda: self.search([("bucket_key", "=", bucket_key)], limit=1),
            conflict=f"rate limit bucket {bucket_key!r}",
        )
        if created:
            _logger.info(
                "Created rate limit bucket: %s (capacity: %d)",
                bucket_key,
                capacity,
            )
        return bucket

    STRICT_LOCK_TIMEOUT_MS = 3000

    def _lock_bucket_row(self, strict: bool):
        if not strict:
            self.env.cr.execute(
                """
                SELECT id, tokens, last_refill
                FROM rate_limit_bucket
                WHERE id = %s
                FOR UPDATE SKIP LOCKED
                """,
                [self.id],
            )
            return self.env.cr.fetchone()

        self.env.cr.execute(
            "SELECT set_config('lock_timeout', %s, true)",
            [f"{self.STRICT_LOCK_TIMEOUT_MS}ms"],
        )
        self.env.cr.execute(
            """
            SELECT id, tokens, last_refill
            FROM rate_limit_bucket
            WHERE id = %s
            FOR UPDATE
            """,
            [self.id],
        )
        row = self.env.cr.fetchone()
        self.env.cr.execute("RESET lock_timeout")
        return row

    def _refilled_tokens(
        self,
        current_tokens,
        last_refill,
        now,
        capacity=None,
        refill_rate=None,
    ):
        if capacity is None or refill_rate is None:
            capacity, _period, refill_rate = self._get_endpoint_config()
        elapsed_seconds = (now - last_refill).total_seconds()

        if elapsed_seconds < 0:
            _logger.warning(
                "Backward clock skew detected for bucket %s: elapsed_seconds=%.2f.",
                self.bucket_key,
                elapsed_seconds,
            )
            return current_tokens

        return token_bucket.refill(
            current_tokens,
            elapsed_seconds,
            rate=refill_rate,
            capacity=capacity,
            max_elapsed_seconds=MAX_REFILL_SECONDS,
        )

    def consume_token(
        self,
        strict: bool = False,
        capacity: float | None = None,
        refill_rate: float | None = None,
    ) -> bool:
        self.check_singleton()

        savepoint_name = f"rate_limit_lock_{self.id}"
        self.env.cr.execute(f"SAVEPOINT {savepoint_name}")

        try:
            row = self._lock_bucket_row(strict)
            if not row:
                self.env.cr.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                if strict:
                    _logger.warning(
                        "Rate limit bucket %s locked; denying request (strict mode).",
                        self.bucket_key,
                    )
                    return False
                _logger.debug(
                    "Rate limit bucket %s locked by another transaction, allowing request (best-effort rate limiting).",
                    self.bucket_key,
                )
                return True

            _bucket_id, current_tokens, last_refill = row
            now = fields.Datetime.now()
            new_tokens = self._refilled_tokens(
                current_tokens,
                last_refill,
                now,
                capacity=capacity,
                refill_rate=refill_rate,
            )

            final_tokens = token_bucket.take(new_tokens)
            if final_tokens is not None:
                self.env.cr.execute(
                    """
                    UPDATE rate_limit_bucket
                    SET tokens = %s,
                        last_refill = %s,
                        last_request_at = %s
                    WHERE id = %s
                    """,
                    [final_tokens, now, now, self.id],
                )

                self.env.cr.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                self.invalidate_recordset(
                    ["tokens", "last_refill", "last_request_at"],
                )
                return True

            _logger.warning(
                "Rate limit EXCEEDED: %s (tokens: %.2f, need: 1.0)",
                self.bucket_key,
                new_tokens,
            )
            self.env.cr.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            return False

        except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
            # Two requests contended for this bucket's row. That is a fact about
            # the database, not about the caller's quota, and it must not become
            # a verdict on the request.
            #
            # Every cursor here is REPEATABLE READ, and the strict path takes
            # `FOR UPDATE` on one hot row under a `lock_timeout`. Under
            # concurrency that yields SerializationFailure, LockNotAvailable or
            # DeadlockDetected -- the three the framework names retryable, and
            # which the request layer already retries with a fresh snapshot.
            # Swallowing one into `return False` denied a caller who had quota,
            # and made the STRICTER setting fail harder the more load it saw:
            # measured over HTTP at 3000 tokens/min with a single user, one
            # client passed 160 of 160 while sixteen clients were refused 101 of
            # 160, with 2881 tokens still in the bucket.
            #
            # Re-raised, so the retry happens where it can work. A savepoint
            # rollback would not help: the snapshot is fixed for the
            # transaction, so retrying the same read inside it fails the same
            # way.
            raise

        except Exception as e:
            self.env.cr.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")

            if strict:
                _logger.error(
                    "Error consuming token from bucket %s: %s. Denying request (strict mode).",
                    self.bucket_key,
                    e,
                )
                return False

            _logger.error(
                "Error consuming token from bucket %s: %s. Allowing request to prevent user-facing errors.",
                self.bucket_key,
                e,
            )
            return True

    @api.depends("endpoint_model", "endpoint_id")
    def _compute_can_reset(self):
        for bucket in self:
            resettable = False
            if bucket.endpoint_model in self.env:
                endpoint = self.env[bucket.endpoint_model].browse(
                    bucket.endpoint_id,
                )
                resettable = endpoint.exists()
            bucket.can_reset = resettable

    def reset_bucket(self) -> None:
        for bucket in self:
            try:
                capacity, _period, _refill_rate = bucket._get_endpoint_config()
            except ValueError as exc:
                raise UserError(
                    self.env._(
                        "This bucket's capacity is set by its caller at "
                        "consume time and cannot be resolved for a reset."
                    ),
                ) from exc
            bucket.write(
                {
                    "tokens": capacity,
                    "last_refill": fields.Datetime.now(),
                },
            )
            _logger.info(
                "Reset rate limit bucket: %s (capacity: %d)",
                bucket.bucket_key,
                capacity,
            )

    @api.model
    def cron_gc_old_buckets(self) -> int:
        threshold = fields.Datetime.now() - timedelta(days=30)

        old_buckets = self.search(
            [
                "|",
                "&",
                ("last_request_at", "=", False),
                ("create_date", "<", threshold),
                ("last_request_at", "<", threshold),
            ],
        )

        count = len(old_buckets)
        if count > 0:
            old_buckets.unlink()
            _logger.info(
                "Cleaned up %d old rate limit buckets (unused for 30+ days)",
                count,
            )

        return count

    @api.model
    def cron_cleanup_caller_rate_limiter(self) -> dict[str, int]:
        limiter = get_caller_rate_limiter(self.env)
        cleaned = limiter.cleanup_old_entries(max_age_hours=24)
        stats = limiter.get_stats()
        _logger.info(
            "Rate limiter cleanup complete: removed %d keys, tracking %d active "
            "keys with %d total attempts",
            cleaned,
            stats["total_keys"],
            stats["total_attempts_tracked"],
        )
        return {
            "cleaned": cleaned,
            "active_keys": stats["total_keys"],
            "total_attempts": stats["total_attempts_tracked"],
        }
