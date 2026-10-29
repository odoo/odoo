from odoo import fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import single_email_re

from odoo.addons.iap.tools import iap_tools


# TODO: test VAT, the CVR of the MitID Erhverv test organisation
MITID_TEST_CVR = '90004317'


class NemhandelRegistration(models.TransientModel):
    _inherit = 'nemhandel.registration'

    mitid_authentication_uuid = fields.Char(
        string="Authentication IAP UUID",
        related='company_id.mitid_authentication_uuid',
        store=True,
        readonly=False,
    )
    mitid_kyc_status = fields.Selection(
        string="Authentication status",
        related='company_id.mitid_kyc_status',
        readonly=False,
    )

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _get_kyb_cvr(self):
        self.ensure_one()
        if self.edi_mode in ('demo', 'test'):
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
