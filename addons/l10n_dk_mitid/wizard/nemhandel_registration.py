import logging

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import single_email_re

from odoo.addons.iap.tools import iap_tools

_logger = logging.getLogger(__name__)

# TODO: test VAT, the CVR of the MitID Erhverv test organisation
MITID_TEST_CVR = '90004317'


class NemhandelRegistration(models.TransientModel):
    _inherit = 'nemhandel.registration'

    mitid_authentication_uuid = fields.Char(
        related='company_id.mitid_authentication_uuid',
        store=True,
        readonly=False,
    )
    mitid_kyc_status = fields.Selection(
        related='company_id.mitid_kyc_status',
        readonly=False,
    )
    # The differences between the company and the CVR register, found before the authentication
    mitid_company_differences = fields.Json()
    mitid_company_differences_html = fields.Html(compute='_compute_mitid_company_differences_html')

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('mitid_company_differences')
    def _compute_mitid_company_differences_html(self):
        for wizard in self:
            wizard.mitid_company_differences_html = wizard.mitid_company_differences and self.env['ir.qweb']._render(
                'l10n_dk_mitid.mitid_company_differences',
                {'differences': wizard.mitid_company_differences},
            )

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _mitid_get_company_differences(self):
        """ Checks the company data against the CVR register before the authentication.

        :return: the differences with the CVR register, see `res.company._mitid_get_company_differences`
        """
        self.ensure_one()
        company = self.company_id
        if not company.company_registry:
            if self.edi_mode != 'demo':
                raise UserError(self.env._("Please set the CVR number (Company ID) of your company before authenticating it."))
            # The test authentication uses the test CVR, not the company one
            return []
        try:
            company_info = company._mitid_get_company_info()
        except Exception:  # noqa: BLE001
            # The CVR register being unreachable must not block the authentication
            _logger.warning("Could not check the company %s against the CVR register", company.id, exc_info=True)
            return []
        if error := company_info.get('error'):
            # 102: invalid CVR, 104: CVR not found. The test companies are not in the CVR register.
            if company_info.get('code') in {102, 104} and self.edi_mode == 'prod':
                raise UserError(error)
            _logger.info("Could not check the company %s against the CVR register: %s", company.id, error)
            return []
        return company._mitid_get_company_differences(company_info)

    def _get_kyb_cvr(self):
        self.ensure_one()
        if self.edi_mode == 'demo':
            return MITID_TEST_CVR
        return self.company_id.company_registry

    def _get_status_notification_data(self):
        self.ensure_one()
        if self.mitid_kyc_status == 'success':
            if self.l10n_dk_nemhandel_proxy_state == 'in_verification':
                # Registered before the KYB was required, the participant still has to confirm the SMS code
                next_action = self._action_open_nemhandel_form()
            elif self.l10n_dk_nemhandel_proxy_state != 'not_registered':
                # Registered before the KYB was required, nothing more to do
                next_action = {'type': 'ir.actions.client', 'tag': 'soft_reload'}
            else:
                # The authentication is the first step of the registration, continue with it
                next_action = self.button_nemhandel_registration_sms()
            return {
                'message': self.env._("Company verified."),
                'type': 'success',
                'sticky': True,
                'next': next_action,
            }
        elif self.mitid_kyc_status == 'fail':
            return {
                'message': self.env._("Authentication failed."),
                'type': 'danger',
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        return {
            'message': self.env._("Status updated."),
            'type': 'info',
            'sticky': False,
            'next': self._action_open_nemhandel_form(),
        }

    def _display_status_notification(self):
        data = self._get_status_notification_data()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': data['message'],
                'type': data['type'],
                'sticky': data['sticky'],
                'next': data['next'],
            },
        }

    def display_status_notification_from_uuid(self):
        self.ensure_one()
        return self._display_status_notification()

    # -------------------------------------------------------------------------
    # BUSINESS ACTIONS
    # -------------------------------------------------------------------------

    def button_trigger_authentication(self):
        self.ensure_one()
        if not self.contact_email or not single_email_re.match(self.contact_email):
            raise ValidationError(self.env._("Invalid email address '%s'", self.contact_email))
        # The company data must match the CVR register before authenticating it
        if differences := self._mitid_get_company_differences():
            self.mitid_company_differences = differences
            return self._action_open_nemhandel_form()
        self.mitid_company_differences = False

        base_url = self.company_id._mitid_get_iap_url()
        response = iap_tools.iap_jsonrpc(f'{base_url}/api/id_authentication/1/authentication', params={
            'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            'vat': self._get_kyb_cvr(),
            'auth_email': self.contact_email,
            'company_name': self.company_id.name,
            'localization': 'DK',
            'db_url': self.get_base_url(),
        })
        if error := response.get('error'):
            raise UserError(error)

        self.mitid_authentication_uuid = response.get('object_uuid')

        if not self.mitid_authentication_uuid or not response.get('url_hash'):
            raise UserError(self.env._("Something wrong happened."))
        self.mitid_kyc_status = 'processing'

        return {
            'type': 'ir.actions.act_url',
            'url': f'{base_url}/api/id_authentication/1/authentication_portal/{response["url_hash"]}',
            'target': 'new',
        }

    def button_mitid_update_company(self):
        """ Updates the company with the data of the CVR register, then continues with the authentication. """
        self.ensure_one()
        self.company_id._mitid_write_cvr_values({
            difference['field']: difference['value']
            for difference in self.mitid_company_differences or []
        })
        self.mitid_company_differences = False
        return self.button_trigger_authentication()

    def button_mitid_discard_company_differences(self):
        self.ensure_one()
        self.mitid_company_differences = False
        return self._action_open_nemhandel_form()

    def button_refresh_authentication(self):
        self.ensure_one()
        self.company_id._refresh_mitid_authentication_status(send_bus=False)
        return self._display_status_notification()

    def button_open_authentication_link(self):
        self.ensure_one()
        base_url = self.company_id._mitid_get_iap_url()
        response = iap_tools.iap_jsonrpc(f'{base_url}/api/id_authentication/1/get_authentication_hash', params={
            'db_uuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
            'vat': self._get_kyb_cvr(),
            'auth_email': self.contact_email,
            'object_uuid': self.mitid_authentication_uuid,
        })
        if error := response.get('error'):
            raise UserError(error)

        if not response.get('url_hash'):
            raise UserError(self.env._("Something wrong happened."))

        return {
            'type': 'ir.actions.act_url',
            'url': f'{base_url}/api/id_authentication/1/authentication_portal/{response["url_hash"]}',
            'target': 'new',
        }

    def button_cancel_authentication(self):
        self.ensure_one()
        self.mitid_kyc_status = 'fail'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': self.env._("Authentication cancelled"),
                'type': 'danger',
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def button_deregister_nemhandel_participant(self):
        # Reset the kyc status
        self.mitid_kyc_status = False
        return super().button_deregister_nemhandel_participant()
