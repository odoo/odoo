import logging
import time

import requests

from odoo import api, fields, models
from odoo.libs import redact

from ..tools.connection_gate import CONNECTION_CONTEXT_KEY
from ..tools.exchange_queue import queue_exchange_values

UNRECORDED_PURPOSES = frozenset(
    {
        "discuss_sfu",
        "google_fonts",
        "link_preview",
        "linkedin_thumbnail",
        "mail_plugin_logo",
        "mailing_image",
        "media_library",
        "media_url",
        "remote_image",
        "report_resource",
        "slide_metadata",
        "slide_thumbnail",
        "static_map",
        "unsplash",
        "web_push",
    }
)

CLIENT_PURPOSE_PREFIX = "integration:"

_logger = logging.getLogger(__name__)


class IntegrationEgressPurpose(models.Model):
    _name = "integration.egress.purpose"
    _description = "Outbound Purpose"
    _rec_name = "purpose"
    _order = "purpose"

    purpose = fields.Char(
        index=True,
        readonly=True,
        required=True,
        help="The purpose a caller named when it sent traffic through ir.egress.",
    )

    _purpose_uniq = models.Constraint(
        "unique(purpose)",
        "An outbound purpose is recorded once.",
    )

    @api.model
    def _get_for(self, purpose):
        records = self.sudo().with_context(active_test=False)
        found = records.search([("purpose", "=", purpose)], limit=1)
        if found:
            return found
        self.env.cr.execute(
            """
            INSERT INTO integration_egress_purpose (purpose, create_uid, write_uid,
                                                    create_date, write_date)
            VALUES (%s, %s, %s, now() at time zone 'utc', now() at time zone 'utc')
            ON CONFLICT (purpose) DO NOTHING
            """,
            [purpose, self.env.uid, self.env.uid],
        )
        return records.search([("purpose", "=", purpose)], limit=1)


class IntegrationExchange(models.Model):
    _inherit = "integration.exchange"

    @api.model
    def _selection_channel_models(self):
        return [
            *super()._selection_channel_models(),
            ("integration.egress.purpose", "Outbound Purpose"),
        ]

    @api.model_create_multi
    def create(self, vals_list):
        purposes = {
            vals["egress_purpose"] for vals in vals_list if vals.get("egress_purpose")
        }
        channels = {
            purpose: self.env["integration.egress.purpose"]._get_for(purpose)
            for purpose in purposes
        }
        for vals in vals_list:
            purpose = vals.pop("egress_purpose", None)
            if purpose and not vals.get("channel_id"):
                vals["channel_id"] = (
                    f"integration.egress.purpose,{channels[purpose].id}"
                )
        return super().create(vals_list)


class IrEgress(models.AbstractModel):
    _inherit = "ir.egress"

    @api.model
    def _prepare_session(self, session, *, purpose, policy):
        super()._prepare_session(session, purpose=purpose, policy=policy)
        if purpose.startswith(CLIENT_PURPOSE_PREFIX) or purpose in UNRECORDED_PURPOSES:
            return
        env = self.env
        send = session.request

        def request(*args, **kwargs):
            positional = iter(args)
            method = kwargs.get("method") or next(positional)
            url = kwargs.get("url") or next(positional)
            started = time.monotonic()
            try:
                response = send(*args, **kwargs)
            except requests.RequestException as error:
                _record_egress(env, purpose, method, url, started, error=error)
                raise
            _record_egress(env, purpose, method, url, started, response=response)
            return response

        session.request = request


def _record_egress(env, purpose, method, url, started, response=None, error=None):
    try:
        _queue_egress(env, purpose, method, url, started, response, error)
    except Exception:
        _logger.warning(
            "Could not record the %s exchange with %s", purpose, url, exc_info=True
        )


def _queue_egress(env, purpose, method, url, started, response, error):
    cr = env.cr
    if getattr(cr, "closed", False) or getattr(cr, "readonly", False):
        return
    vals = {
        "direction": "outbound",
        "egress_purpose": purpose,
        "company_id": env.company.id,
        "user_id": env.uid,
        "request_method": (method or "").upper() or False,
        "request_url": redact.mask_url(url),
        "duration_ms": (time.monotonic() - started) * 1000,
        "date_completed": fields.Datetime.now(),
        "tags": f"egress:{purpose}",
        "connection_id": env.context.get(CONNECTION_CONTEXT_KEY) or False,
    }
    if response is not None:
        status = response.status_code
        vals.update(
            {
                "status_code": status,
                "state": "failed" if status >= 400 else "success",
                "error_type": _error_type(status) if status >= 400 else False,
            }
        )
    else:
        vals.update(
            {
                "state": "failed",
                "error_type": "timeout"
                if isinstance(error, requests.Timeout)
                else "network",
                "error_message": redact.mask_text(str(error)),
            }
        )
    queue_exchange_values(env, vals)


def _error_type(status):
    if status == 401:
        return "auth"
    if status == 429:
        return "rate_limit"
    if 400 <= status < 500:
        return "validation"
    return "server"
