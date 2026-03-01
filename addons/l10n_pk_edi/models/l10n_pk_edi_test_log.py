import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_pk_edi.data.l10n_pk_edi_data import SCENARIOS

_logger = logging.getLogger(__name__)


class L10nPkEdiTestLog(models.Model):
    _name = "l10n_pk_edi.test.log"
    _description = "Pakistan EDI Test Log"
    _order = "name"

    name = fields.Char(string="Reference", required=True, readonly=True, copy=False, index=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        readonly=True,
        default=lambda self: self.env.company,
        index=True,
    )
    state = fields.Selection(
        selection=[
            ("success", "Success"),
            ("failed", "Failed"),
        ],
        string="Result",
        readonly=True,
        index=True,
    )
    error_message = fields.Text(string="Error Details", readonly=True)
    payload = fields.Text(string="Request Payload", readonly=True)
    response = fields.Text(string="Server Response", readonly=True)

    @api.model
    def get_available_scenarios(self):
        return [(scenario["scenarioId"], scenario) for scenario in SCENARIOS]

    @api.model
    def run_test_scenarios(self):
        scenarios = self.get_available_scenarios()
        if not scenarios:
            return self.env["l10n_pk_edi.test.log"]

        company = self.env.company
        missing = []
        if not company.l10n_pk_edi_test_vat or company.l10n_pk_edi_test_vat_verified != 'registered':
            missing.append(_("Registered Business NTN/CNIC (Requires to be verified)"))
        if not company.l10n_pk_edi_test_auth_token:
            missing.append(_("Test Authentication Token"))
        if not company.vat:
            missing.append(_("Company NTN/CNIC"))
        if missing:
            raise UserError(_("Missing required company fields:\n- %s", "\n- ".join(missing)))

        scenario_ids = [payload.get("scenarioId", fname) for fname, payload in scenarios]
        existing_failed = {
            rec.name: rec
            for rec in self.sudo().search([
                ("name", "in", scenario_ids),
                ("company_id", "=", company.id),
                ("state", "=", "failed"),
            ])
        }

        logs = self.env["l10n_pk_edi.test.log"]
        for filename, json_payload in scenarios:
            logs |= self._run_single_test_scenario(filename, self._prepare_scenario_payload(json_payload, company), company, existing_failed)
        return logs

    def _prepare_scenario_payload(self, json_payload, company):
        payload = dict(json_payload)
        payload['sellerNTNCNIC'] = company.vat
        if payload.get('buyerNTNCNIC') and payload['buyerNTNCNIC'] != '0000000':
            payload['buyerNTNCNIC'] = company.l10n_pk_edi_test_vat or '0000000'
        return payload

    @api.model
    def _extract_error_message(self, response):
        err = response.get("error") or {}
        vr = err.get("validationResponse") or response.get("validationResponse") or {}
        return (
            err.get("message")
            or (err.get("fault") or {}).get("description")
            or vr.get("error")
            or str(err or response)
        )

    @api.model
    def _run_single_test_scenario(self, filename, json_payload, company, existing_failed):
        scenario_id = json_payload.get("scenarioId", filename)
        error_message = None
        last_response = None
        state = "failed"

        auth_token = company.l10n_pk_edi_test_auth_token
        if not auth_token:
            error_message = "Missing test authentication token configured on company settings."
        else:
            try:
                params = {"auth_token": auth_token, "json_payload": json_payload}
                validate_res = self.env["iap.account"]._l10n_pk_connect_to_server(
                    False, params, "/api/l10n_pk_edi/1/validate",
                )
                last_response = validate_res
                vr = (validate_res.get("error") or {}).get("validationResponse") or validate_res.get("validationResponse") or {}
                if validate_res.get("error") or vr.get("status") not in (None, "Valid"):
                    error_message = self._extract_error_message(validate_res)
                else:
                    post_res = self.env["iap.account"]._l10n_pk_connect_to_server(
                        False, params, "/api/l10n_pk_edi/1/post",
                    )
                    last_response = post_res
                    if post_res.get("error"):
                        error_message = self._extract_error_message(post_res)
                    else:
                        state = "success"
            except Exception as exc:
                _logger.exception("l10n_pk_edi: scenario %s raised an unexpected exception", scenario_id)
                error_message = str(exc)

        vals = {
            "state": state,
            "error_message": error_message,
            "payload": json.dumps(json_payload, indent=2),
            "response": json.dumps(last_response, indent=2) if last_response else None,
        }
        if scenario_id in existing_failed:
            existing_failed[scenario_id].write(vals)
            return existing_failed[scenario_id]
        return self.sudo().create([{"name": scenario_id, "company_id": company.id, **vals}])

    def action_rerun(self):
        by_name = {rec.name: rec for rec in self}
        scenario_by_id = {
            payload.get("scenarioId", filename): (filename, payload)
            for filename, payload in self.get_available_scenarios()
        }
        for rec in self:
            filename, json_payload = scenario_by_id.get(rec.name)
            if not (filename and json_payload):
                _logger.warning("l10n_pk_edi: no test data file found for scenario %s", rec.name)
                continue
            prepared_payload = self._prepare_scenario_payload(json_payload, rec.company_id)
            self._run_single_test_scenario(filename, prepared_payload, rec.company_id, by_name)
