from odoo import fields, models

from odoo.addons.iap.tools import iap_tools

# TODO: To be replaced with IAP url once it's ready (ask for DNS)
# TODO: probably https://nemhandel.api.odoo.com or https://mitid.api.odoo.com
IAP_ENDPOINT = 'https://hot-wombat-patient.ngrok-free.app'


class ResCompany(models.Model):
    _inherit = 'res.company'

    mitid_kyc_status = fields.Selection(
        selection=[
            ('processing', "Processing"),
            ('success', "Success"),
            ('fail', "Fail"),
        ],
        groups='base.group_user',
    )
    mitid_authentication_uuid = fields.Char(
        string="Authentication IAP UUID",
        groups='account.group_account_invoice',
    )

    def _mitid_get_iap_url(self):
        return IAP_ENDPOINT

    def _refresh_mitid_authentication_status(self, send_bus=True):
        self.ensure_one()
        response = iap_tools.iap_jsonrpc(f'{self._mitid_get_iap_url()}/api/mitid_id_authentication/1/kyc_status', params={
            'object_uuid': self.mitid_authentication_uuid,
        })
        if response.get('kyb_status') == 'success' and response.get('kyc_status') == 'success':
            self.mitid_kyc_status = 'success'
            if self.env['account.move']._can_commit():
                self.env.cr.commit()
            if not send_bus:  # If called manually from the wizard we do not need the JS to handle it
                return
            nemhandel_registration = self.env['nemhandel.registration'].search([
                ('mitid_authentication_uuid', '=', self.mitid_authentication_uuid),
            ], order='id DESC', limit=1)
            if user := nemhandel_registration.create_uid:
                user._bus_send(
                    'mitid_auth_done',
                    {'nemhandel_registration_id': nemhandel_registration.id},
                )
