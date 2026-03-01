import logging
import socket
from urllib.parse import urlsplit

from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_pk_edi.data.l10n_pk_edi_data import SCENARIOS

_logger = logging.getLogger(__name__)

# Fields below are single values shared by the whole instance, kept in a system parameter
# rather than per company: field name -> (system parameter key, default value).
L10N_PK_EDI_SYSTEM_PARAMS = {
    'l10n_pk_edi_test_auth_token': ('l10n_pk_edi.test_auth_token', ''),
    'l10n_pk_edi_iap_server_ip': ('l10n_pk_edi.iap_server_ip', ''),
    'l10n_pk_edi_test_vat': ('l10n_pk_edi.test_vat', ''),
}


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pk_edi_enable = fields.Boolean(string="Enable E-Invoicing(PK)", help="Enable the Pakistan E-Invoicing features for this company.")
    l10n_pk_edi_whitelisted = fields.Boolean(string="FBR IP Whitelisted")
    l10n_pk_edi_production_auth_token = fields.Char(string="E-invoice(PK) Production Authentication Token", groups='base.group_system')
    l10n_pk_edi_test_auth_token = fields.Char(string="E-invoice(PK) Testing Authentication Token", groups='base.group_system', compute='_compute_l10n_pk_edi_system_params', inverse='_inverse_l10n_pk_edi_test_auth_token')
    l10n_pk_edi_iap_server_ip = fields.Char(string="Odoo Static IP Address", compute='_compute_l10n_pk_edi_system_params', inverse='_inverse_l10n_pk_edi_iap_server_ip')
    l10n_pk_edi_test_vat = fields.Char(
        string="Registered Business Identification Number",
        help="Business Identification Number of a registered business, used as the buyer for FBR sandbox scenarios that require one.",
        compute='_compute_l10n_pk_edi_system_params',
        inverse='_inverse_l10n_pk_edi_test_vat',
    )

    def _compute_l10n_pk_edi_system_params(self):
        icp = self.env['ir.config_parameter'].sudo()
        values = {field_name: icp.get_str(key, default) for field_name, (key, default) in L10N_PK_EDI_SYSTEM_PARAMS.items()}
        for company in self:
            for field_name, value in values.items():
                company[field_name] = value

    def _inverse_l10n_pk_edi_test_auth_token(self):
        self._set_l10n_pk_edi_system_param('l10n_pk_edi_test_auth_token')

    def _inverse_l10n_pk_edi_iap_server_ip(self):
        self._set_l10n_pk_edi_system_param('l10n_pk_edi_iap_server_ip')

    def _inverse_l10n_pk_edi_test_vat(self):
        self._set_l10n_pk_edi_system_param('l10n_pk_edi_test_vat')

    def _set_l10n_pk_edi_system_param(self, field_name):
        key, default = L10N_PK_EDI_SYSTEM_PARAMS[field_name]
        for company in self:
            self.env['ir.config_parameter'].sudo().set_str(key, company[field_name] or default)

    def _get_iap_server_ip(self):
        iap_endpoint = self.env['ir.config_parameter'].sudo().get_str('l10n_pk_edi.iap_endpoint')
        try:
            hostname = urlsplit(iap_endpoint).hostname
            return socket.gethostbyname(hostname)
        except (socket.gaierror, AttributeError):
            return False

    def _l10n_pk_edi_is_test_mode(self):
        self.ensure_one()
        return self.env['ir.config_parameter'].sudo().get_str('l10n_pk_edi.mode', 'production') == 'test'

    def _get_l10n_pk_edi_auth_token(self):
        self.ensure_one()
        return self.l10n_pk_edi_test_auth_token if self._l10n_pk_edi_is_test_mode() else self.l10n_pk_edi_production_auth_token

    # -------------------------------------------------------------------------
    # FBR Sandbox Test Scenarios
    # -------------------------------------------------------------------------

    @api.model
    def _l10n_pk_edi_get_available_scenarios(self):
        return [(scenario["scenarioId"], scenario) for scenario in SCENARIOS]

    def _l10n_pk_edi_check_vat_registered(self):
        """Check with FBR whether this company's Business Identification Number is a registered business."""
        self.ensure_one()
        result = self.env['iap.account']._l10n_pk_connect_to_server(
            is_production=False,
            params={
                'auth_token': self.l10n_pk_edi_test_auth_token,
                'json_payload': {'Registration_No': self.l10n_pk_edi_test_vat.replace('-', '')},
            },
            url_path='/api/l10n_pk_edi/1/registration',
        )
        _logger.info("l10n_pk_edi: registration check response: %s", result)
        if result.get('error'):
            raise UserError(result['error'].get('message', self.env._("Unknown error")))
        return result.get('REGISTRATION_TYPE', '').lower() == 'registered'

    def l10n_pk_edi_run_test_scenarios(self):
        """Run all FBR sandbox test scenarios for this company. Returns the list of failed scenario IDs."""
        self.ensure_one()
        scenarios = self._l10n_pk_edi_get_available_scenarios()
        if not scenarios:
            return []

        missing = []
        if not self.l10n_pk_edi_test_auth_token:
            missing.append(self.env._("Test Authentication Token"))
        if not self.vat:
            missing.append(self.env._("Company Business Identification Number"))
        if not self.l10n_pk_edi_test_vat:
            missing.append(self.env._("Registered Business Identification Number"))
        if missing:
            raise UserError(self.env._("Missing required company fields:\n- %s", "\n- ".join(missing)))

        if not self._l10n_pk_edi_check_vat_registered():
            raise UserError(self.env._("The provided Business Identification Number is not registered with FBR."))

        failed_scenario_ids = []
        for filename, json_payload in scenarios:
            prepared_payload = self._l10n_pk_edi_prepare_scenario_payload(json_payload)
            scenario_id = prepared_payload.get("scenarioId", filename)
            if not self._l10n_pk_edi_run_single_test_scenario(filename, prepared_payload):
                failed_scenario_ids.append(scenario_id)

        # At least one successful response from FBR is enough to consider the IP whitelisted;
        # a scenario failure (or no response at all, e.g. connection lost) must not clear it back.
        if len(failed_scenario_ids) < len(scenarios):
            self.l10n_pk_edi_whitelisted = True
        return failed_scenario_ids

    def _l10n_pk_edi_prepare_scenario_payload(self, json_payload):
        self.ensure_one()
        payload = dict(json_payload)
        payload['sellerNTNCNIC'] = self.vat.replace('-', '')
        if payload.get('buyerNTNCNIC') and payload['buyerNTNCNIC'] != '0000000':
            payload['buyerNTNCNIC'] = self.l10n_pk_edi_test_vat.replace('-', '')
        return payload

    def _l10n_pk_edi_run_single_test_scenario(self, filename, json_payload):
        """Run a single FBR sandbox scenario. Returns True on success."""
        self.ensure_one()
        scenario_id = json_payload.get("scenarioId", filename)

        auth_token = self.l10n_pk_edi_test_auth_token
        if not auth_token:
            return False
        try:
            validate_res = self.env['iap.account']._l10n_pk_connect_to_server(
                is_production=False,
                params={"auth_token": auth_token, "json_payload": json_payload},
                url_path="/api/l10n_pk_edi/1/validate",
            )

            # Validate Response about the invoice
            _logger.info("l10n_pk_edi: scenario %s validate response: %s", scenario_id, validate_res)
            if failure := self.env['iap.account']._l10n_pk_edi_parse_response(validate_res):
                _logger.warning(
                    "l10n_pk_edi: scenario %s rejected at validation: %s", scenario_id, failure["message"],
                )
                return False
            # Post Invoice on the FBR
            post_res = self.env['iap.account']._l10n_pk_connect_to_server(
                is_production=False,
                params={"auth_token": auth_token, "json_payload": json_payload},
                url_path="/api/l10n_pk_edi/1/post",
            )
            _logger.info("l10n_pk_edi: scenario %s post response: %s", scenario_id, post_res)
            if failure := self.env['iap.account']._l10n_pk_edi_parse_response(post_res):
                _logger.warning(
                    "l10n_pk_edi: scenario %s rejected at posting: %s", scenario_id, failure["message"],
                )
                return False
            return True
        except Exception:
            _logger.exception("l10n_pk_edi: scenario %s raised an unexpected exception", scenario_id)
            return False

    # -------------------------------------------------------------------------
    # Validation Methods
    # -------------------------------------------------------------------------

    def _group_by_error_code(self):
        self.ensure_one()
        if not self.vat:
            return (
                ('message', self.env._("Company/ies should have a Business Identification Number.")),
                ('error_code', 'l10n_pk_edi_company_vat_missing'),
                ('level', 'danger'),
            )

        if not self.env['res.partner']._check_vat_number('PK', self.vat):
            return (
                ('message', self.env._("Company/ies has an invalid Business Identification Number.")),
                ('error_code', 'l10n_pk_edi_company_vat_invalid'),
                ('level', 'danger'),
            )

        if not all(self[field] for field in ('street', 'city', 'state_id', 'country_id')):
            return (
                ('message', self.env._("Company/ies should have a complete address, verify their Street, City, State and Country.")),
                ('error_code', 'l10n_pk_edi_company_address_missing'),
                ('level', 'danger'),
            )

        if not self._get_l10n_pk_edi_auth_token():
            token_name = self.env._("Testing") if self._l10n_pk_edi_is_test_mode() else self.env._("Production")
            message = self.env._("Configure the EDI %s Auth Token to enable e-invoicing.") % token_name
            return (
                ('message', message),
                ('error_code', 'l10n_pk_edi_company_auth_key_missing'),
                ('level', 'danger'),
            )
        return False

    def _l10n_pk_edi_export_check(self):
        alert_vals = {}
        for error_tuple, invalid_records in self.grouped(lambda m: m._group_by_error_code()).items():
            if not error_tuple:
                continue
            temp_dict = dict(error_tuple)
            invalid_records_action = (
                invalid_records._get_records_action()
                if temp_dict['error_code'] != 'l10n_pk_edi_company_auth_key_missing'
                else self.env['res.config.settings']._get_records_action(context={**self.env.context, 'module': 'account'})
            )
            alert_vals.update({
                temp_dict['error_code']: {
                    'message': temp_dict['message'],
                    'level': temp_dict['level'],
                    'action': invalid_records_action,
                    'action_text':  self.env._("View Company/ies"),
                },
            })
        return alert_vals
