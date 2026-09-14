import logging
import zlib
from typing import Any

from werkzeug.exceptions import Forbidden

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.http import request

CALLER_CHECK_KEY = "inbound_caller_check"

_logger = logging.getLogger(__name__)


class IntegrationReceiver(models.Model):
    _name = "integration.receiver"
    _inherit = ["mixin.integration.receiver"]
    _description = "Integration Receiver"
    _order = "sequence, id"

    auth_type = fields.Selection(
        selection_add=[("caller_check", "Checked by the receiving controller")],
        ondelete={"caller_check": "set default"},
    )
    res_model = fields.Char(
        string="Serves Model",
        index=True,
        readonly=True,
        help="The model of the record whose inbound calls this receiver admits.",
    )
    res_id = fields.Many2oneReference(
        model_field="res_model",
        string="Serves Record",
        index=True,
        readonly=True,
    )
    res_purpose = fields.Char(
        string="Serves Purpose",
        index=True,
        readonly=True,
        help="Which of the record's inbound flows this receiver admits, when a record "
        "receives more than one.",
    )
    processing_mode = fields.Selection(default="sync")
    duplicate_detection_enabled = fields.Boolean(default=False)

    @api.model
    def _for_record(self, record, name, purpose=None):
        record.check_singleton()
        domain = [
            ("res_model", "=", record._name),
            ("res_id", "=", record.id),
            ("res_purpose", "=", purpose or False),
        ]
        receivers = self.sudo().with_context(active_test=False)
        receiver = receivers.search(domain, limit=1)
        if receiver:
            return receiver
        company = record["company_id"] if "company_id" in record._fields else None
        with self.env.registry.cursor() as receiver_cr:
            receiver_cr.execute(
                "SELECT pg_advisory_xact_lock(%s, %s)",
                [zlib.crc32(record._name.encode()) & 0x7FFFFFFF, record.id],
            )
            committed = receivers.with_env(receivers.env(cr=receiver_cr))
            receiver = committed.search(domain, limit=1) or committed.create(
                {
                    "name": name,
                    "code": "_".join(
                        str(part)
                        for part in (record._table, record.id, purpose)
                        if part
                    ),
                    "res_model": record._name,
                    "res_id": record.id,
                    "res_purpose": purpose or False,
                    "auth_type": "caller_check",
                    "company_id": company.id if company else False,
                    "rate_limit_enabled": True,
                    "rate_limit_requests": 600,
                    "rate_limit_window_seconds": 60,
                }
            )
            receiver_id = receiver.id
        return receivers.browse(receiver_id)

    def _authenticate_scheme_caller_check(
        self, headers: dict[str, Any], body: Any
    ) -> bool:
        check = self.env.context.get(CALLER_CHECK_KEY)
        if check is None:
            raise ValidationError(
                self.env._(
                    "Receiver %s is checked by its controller, which passed no check.",
                    self.display_name,
                )
            )
        try:
            check()
        except Forbidden:
            return False
        except Exception:
            _logger.warning(
                "%s: the caller's check failed on a malformed request",
                self.display_name,
                exc_info=True,
            )
            return False
        return True

    def _admit_checked_request(self, check, event_type=None):
        self.check_singleton()
        httprequest = request.httprequest
        with self.env.registry.cursor() as verdict_cr:
            allowed, _status, _reason = self.with_env(
                self.env(
                    cr=verdict_cr, context={**self.env.context, CALLER_CHECK_KEY: check}
                )
            )._check_inbound_request(
                dict(httprequest.headers),
                body=httprequest.get_data(cache=True),
                remote_addr=httprequest.remote_addr,
            )
        if allowed:
            self._record_inbound_exchange(
                method=httprequest.method,
                path=httprequest.path,
                remote_addr=httprequest.remote_addr,
                user_agent=httprequest.headers.get("User-Agent"),
                event_type=event_type,
            )
        return allowed
