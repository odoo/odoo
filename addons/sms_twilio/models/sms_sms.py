import hmac
import logging
import re
from collections import defaultdict

from werkzeug.exceptions import NotFound

from odoo import api, fields, models
from odoo.http import request

from odoo.addons.sms_twilio.tools.sms_twilio import (
    generate_twilio_sms_callback_signature,
)

_logger = logging.getLogger(__name__)


class SmsSms(models.Model):
    _inherit = "sms.sms"

    @api.model
    def _receiver_for_twilio_status(self, uuid=None, **path_args):
        if not uuid or not re.match(r"^[0-9a-f]{32}$", uuid):
            _logger.warning(
                "Twilio SMS: update_sms_status received a non-valid uuid='%s'", uuid
            )
            raise NotFound
        sms = self.sudo().search([("uuid", "=", uuid)], limit=1)
        if not sms:
            _logger.warning(
                "Twilio SMS: update_sms_status found no SMS for uuid='%s'", uuid
            )
            raise NotFound
        return sms

    def _inbound_gate_owner(self):
        company = self._get_sms_company().sudo()
        return (
            company,
            self.env._("%(company)s Twilio SMS status callbacks", company=company.name),
            "sms_twilio_status",
        )

    def _verify_inbound_request(self, headers, body):
        self.check_singleton()
        computed_signature = generate_twilio_sms_callback_signature(
            self._get_sms_company().sudo(),
            self.uuid,
            request.httprequest.form.to_dict(),
        )
        x_twilio_signature = headers.get("X-Twilio-Signature", "")
        if not hmac.compare_digest(computed_signature, x_twilio_signature):
            _logger.warning(
                "Twilio SMS: update_sms_status could not validate Twilio signature "
                "with uuid='%s'",
                self.uuid,
            )
            return False
        return True

    sms_twilio_sid = fields.Char(
        related="sms_tracker_id.sms_twilio_sid",
        depends=["sms_tracker_id"],
    )
    record_company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        ondelete="set null",
    )
    failure_type = fields.Selection(
        selection_add=[
            ("twilio_authentication", 'Authentication Error"'),
            ("twilio_callback", "Incorrect callback URL"),
            ("twilio_from_missing", "Missing From Number"),
            ("twilio_from_to", "From / To identic"),
        ]
    )

    # CRUD
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["record_company_id"] = (
                vals.get("record_company_id") or self.env.company.id
            )  # TODO RIGR in master: move this field to SmsSms, and populate it via vals_list from all flows
        return super().create(vals_list)

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        # As we are adding keys in stable, better be sure no-one is getting crashes
        # due to missing translations
        # TODO: remove in master
        res = super().fields_get(allfields=allfields, attributes=attributes)

        existing_selection = res.get("failure_type", {}).get("selection")
        if existing_selection is None:
            return res

        updated_stable = {"twilio_from_missing", "twilio_from_to"}
        need_update = updated_stable - set(dict(self._fields["failure_type"].selection))
        if need_update:
            self.env["ir.model.fields"].invalidate_model(["selection_ids"])
            self.env["ir.model.fields.selection"]._update_selection(
                self._name,
                "failure_type",
                self._fields["failure_type"].selection,
            )
            self.env.registry.clear_cache()
            return super().fields_get(allfields=allfields, attributes=attributes)

        return res

    # SEND
    # ------------------------------------------------------------

    def _split_by_api(self):
        # override to handle twilio or IAP choice, which is company dependent
        # even twilio accounts may differ between companies
        sms_by_company = defaultdict(
            lambda: self.env["sms.sms"]
        )  # TODO RIGR: in master, let's be smarter and group by provider/twilio account (e.g.: IAP/twilio1/twilio2)
        todo_via_super = self.browse()
        for sms in self:
            sms_by_company[sms._get_sms_company()] += sms
        for company, company_sms in sms_by_company.items():
            if company.sms_twilio_config_id.sms_provider == "twilio":
                sms_api = company._get_sms_api_class()(self.env)
                sms_api._set_company(company)
                yield sms_api, company_sms
            else:
                todo_via_super += company_sms
        if todo_via_super:
            yield from super(SmsSms, todo_via_super)._split_by_api()

    def _get_sms_company(self):
        return (
            self.mail_message_id.record_company_id
            or self.record_company_id
            or super()._get_sms_company()
        )

    def _get_send_batch_size(self):
        companies = self._get_sms_company()
        if companies and any(
            company.sms_twilio_config_id.sms_provider == "twilio"
            for company in companies
        ):
            return self.env["ir.config_parameter"]._get_positive_int_param(
                "sms_twilio.session.batch.size", 10
            )
        return super()._get_send_batch_size()

    def _handle_call_result_hook(self, results):
        """
        Store the sid of Twilio on the SMS tracking record (as SMS will be deleted)
        :param results: a list of dict in the form [{
            'uuid': Odoo's id of the SMS,
            'state': State of the SMS in Odoo,
            'sms_twilio_sid': Twilio's id of the SMS,
        }, ...]
        """
        twilio_sms = self.filtered(
            lambda s: s._get_sms_company().sms_twilio_config_id.sms_provider == "twilio"
        )
        grouped_twilio_sms = twilio_sms.grouped("uuid")
        for result in results:
            sms = grouped_twilio_sms.get(result.get("uuid"))
            if sms and sms.sms_tracker_id and result.get("sms_twilio_sid"):
                sms.sms_tracker_id.sms_twilio_sid = result["sms_twilio_sid"]
        super(SmsSms, self - twilio_sms)._handle_call_result_hook(results)
