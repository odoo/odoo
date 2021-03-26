# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug import urls

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(
        selection_add=[('odoo', "Odoo Payments")], ondelete={'odoo': 'set default'})
    odoo_adyen_account_id = fields.Many2one(
        related='company_id.adyen_account_id', required_if_provider='odoo')
    odoo_adyen_payout_id = fields.Many2one(
        string="Adyen Payout", comodel_name='adyen.payout', required_if_provider='odoo',
        domain='[("adyen_account_id", "=", odoo_adyen_account_id)]')

    @api.constrains('provider', 'state')
    def _check_state_is_not_test(self):
        if any(a.provider == 'odoo' and a.state == 'test' for a in self):
            raise ValidationError(_("Odoo Payments is not available in test mode."))

    def odoo_create_adyen_account(self):
        return self.env['adyen.account'].action_create_redirect()

    def _odoo_get_api_url(self):
        self.ensure_one()
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('adyen_platforms.proxy_url')
        return urls.url_join(proxy_url, 'pay_by_link')

    def _odoo_compute_shopper_reference(self, partner_id):
        """ Compute a unique reference of the partner for Adyen.

        This is used for the `shopperReference` field in communications with Adyen.

        :param recordset partner_id: The partner making the transaction, as a `res.partner` id
        :return: The unique reference for the partner
        :rtype: str
        """
        return f'{self.odoo_adyen_account_id.adyen_uuid}_{partner_id}'
