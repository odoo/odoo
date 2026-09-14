import hashlib
import json
import logging
from datetime import timedelta
from typing import Any

import psycopg.errors

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResponseCache(models.Model):
    _name = "integration.response.cache"
    _description = "Response Cache"
    _order = "last_accessed desc"
    _rec_name = "cache_key"

    cache_key = fields.Char(
        index=True,
        required=True,
    )
    endpoint_id = fields.Many2one(
        comodel_name="integration.service",
        index=True,
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        index=True,
        required=True,
    )

    request_url = fields.Char(required=True)
    request_params_hash = fields.Char()

    response_body = fields.Json(required=True)
    response_headers = fields.Json()
    status_code = fields.Integer(default=200)

    date_created = fields.Datetime(
        default=fields.Datetime.now,
        index=True,
        required=True,
    )
    date_expiration = fields.Datetime(
        index=True,
        required=True,
    )
    is_expired = fields.Boolean(
        compute="_compute_is_expired",
        search="_search_is_expired",
    )
    ttl_seconds = fields.Integer()

    hit_count = fields.Integer(default=0)
    last_accessed = fields.Datetime(default=fields.Datetime.now)

    _cache_lookup_idx = models.Index(
        "(cache_key, company_id, date_expiration)",
    )
    _expires_cleanup_idx = models.Index(
        "(date_expiration)",
    )

    _cache_key_company_uniq = models.Constraint(
        "unique(cache_key, company_id)",
        "Cache key must be unique per company!",
    )

    @api.depends("date_expiration")
    def _compute_is_expired(self):
        now = fields.Datetime.now()
        for cache in self:
            cache.is_expired = cache.date_expiration < now

    def _search_is_expired(self, operator: str, value: Any):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            return NotImplemented
        now = fields.Datetime.now()
        if (operator == "=") == value:
            return [("date_expiration", "<", now)]
        return [("date_expiration", ">=", now)]

    @api.model
    def get_cached_response(
        self,
        endpoint_code: str,
        url: str,
        params: dict[str, Any] | None = None,
        company_id: int | None = None,
        credential_id: int | None = None,
    ) -> dict[str, Any] | None:
        if company_id is None:
            company_id = self.env.company.id

        cache_key = self._generate_cache_key(endpoint_code, url, params, credential_id)
        cache_entry = self.search(
            [
                ("cache_key", "=", cache_key),
                ("company_id", "=", company_id),
                ("date_expiration", ">", fields.Datetime.now()),
            ],
            limit=1,
        )

        if cache_entry:
            cache_entry.sudo().write(
                {
                    "hit_count": cache_entry.hit_count + 1,
                    "last_accessed": fields.Datetime.now(),
                }
            )

            _logger.debug("Cache HIT: %s", cache_key)

            return {
                "body": cache_entry.response_body,
                "headers": cache_entry.response_headers,
                "status_code": cache_entry.status_code,
                "from_cache": True,
            }

        _logger.debug("Cache MISS: %s", cache_key)
        return None

    @api.model
    def set_cached_response(
        self,
        endpoint_code: str,
        url: str,
        response: dict[str, Any],
        ttl: int | None = None,
        params: dict[str, Any] | None = None,
        company_id: int | None = None,
        credential_id: int | None = None,
    ):
        if company_id is None:
            company_id = self.env.company.id

        service = self.env["integration.service"].search(
            [
                ("code", "=", endpoint_code),
            ],
            limit=1,
        )
        if not service or not service.cache_enabled:
            return

        if ttl is None:
            ttl = service.cache_ttl or 300

        cache_key = self._generate_cache_key(endpoint_code, url, params, credential_id)
        params_hash = self._generate_params_hash(params)
        now = fields.Datetime.now()
        date_expiration = now + timedelta(seconds=ttl)

        try:
            with self.env.cr.savepoint():
                self.env.cr.execute(
                    """
                    INSERT INTO integration_response_cache (
                        cache_key, endpoint_id, company_id, request_url,
                        request_params_hash, response_body, response_headers,
                        status_code, date_created, date_expiration, ttl_seconds,
                        hit_count, last_accessed, create_uid, create_date,
                        write_uid, write_date
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (cache_key, company_id)
                    DO UPDATE SET
                        endpoint_id = EXCLUDED.endpoint_id,
                        request_url = EXCLUDED.request_url,
                        request_params_hash = EXCLUDED.request_params_hash,
                        response_body = EXCLUDED.response_body,
                        response_headers = EXCLUDED.response_headers,
                        status_code = EXCLUDED.status_code,
                        date_expiration = EXCLUDED.date_expiration,
                        ttl_seconds = EXCLUDED.ttl_seconds,
                        write_uid = EXCLUDED.write_uid,
                        write_date = EXCLUDED.write_date
                    """,
                    (
                        cache_key,
                        service.id,
                        company_id,
                        url,
                        params_hash,
                        json.dumps(response.get("body", "")),
                        json.dumps(response.get("headers", {})),
                        response.get("status_code", 200),
                        now,
                        date_expiration,
                        ttl,
                        0,
                        now,
                        self.env.uid,
                        now,
                        self.env.uid,
                        now,
                    ),
                )
            _logger.debug("Cache SET: %s (TTL: %ds)", cache_key, ttl)

        except psycopg.errors.SerializationFailure as e:
            _logger.warning(
                "Cache serialization failure (savepoint rolled back): %s", e
            )

        except Exception:
            _logger.exception("Error saving cache (savepoint rolled back)")

    @api.model
    def invalidate_cache(
        self,
        endpoint_code: str | None = None,
        url_pattern: str | None = None,
        company_id: int | None = None,
    ) -> int:
        domain = []

        if endpoint_code:
            service = self.env["integration.service"].search(
                [
                    ("code", "=", endpoint_code),
                ],
                limit=1,
            )
            if service:
                domain.append(("endpoint_id", "=", service.id))

        if url_pattern:
            domain.append(("request_url", "ilike", url_pattern))

        if company_id:
            domain.append(("company_id", "=", company_id))

        entries = self.search(domain)
        count = len(entries)
        entries.unlink()
        _logger.info("Invalidated %d cache entries", count)
        return count

    @api.model
    def _generate_cache_key(
        self,
        endpoint_code: str,
        url: str,
        params: dict[str, Any] | None = None,
        credential_id: int | None = None,
    ) -> str:
        content = f"{endpoint_code}:{credential_id or 0}:{url}"

        if params:
            params_str = (
                json.dumps(params, sort_keys=True)
                if isinstance(params, dict)
                else str(params)
            )
            content += f":{params_str}"

        return hashlib.sha256(content.encode()).hexdigest()

    @api.model
    def _generate_params_hash(self, params: dict[str, Any] | None) -> str | bool:
        if not params:
            return False

        params_str = (
            json.dumps(params, sort_keys=True)
            if isinstance(params, dict)
            else str(params)
        )
        return hashlib.md5(params_str.encode()).hexdigest()[:16]

    @api.autovacuum
    def _gc_expired_cache(self):
        self.flush_model()
        now = fields.Datetime.now()
        self.env.cr.execute(
            "DELETE FROM integration_response_cache WHERE date_expiration < %s",
            (now,),
        )

        count = self.env.cr.rowcount
        if count:
            _logger.info("Garbage collected %d expired cache entries", count)

    @api.autovacuum
    def _gc_least_used_cache(self):
        self.flush_model()

        max_entries = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("integration.max_cache_entries", "10000"),
        )

        self.env.cr.execute("SELECT COUNT(*) FROM integration_response_cache")
        total_count = self.env.cr.fetchone()[0]

        if total_count > max_entries:
            to_delete = total_count - max_entries

            self.env.cr.execute(
                """
                DELETE FROM integration_response_cache
                WHERE id IN (
                    SELECT id FROM integration_response_cache
                    ORDER BY hit_count ASC, last_accessed ASC, id ASC
                    LIMIT %s
                )
                """,
                (to_delete,),
            )

            self.invalidate_model()

            count = self.env.cr.rowcount
            _logger.info(
                "Garbage collected %d least-used cache entries (limit: %d)",
                count,
                max_entries,
            )
