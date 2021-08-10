# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug import urls

from odoo import fields, models


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(
        selection_add=[('odoo', "Odoo Payments")], ondelete={'odoo': 'set default'})
    odoo_adyen_account_id = fields.Many2one(
        related='company_id.adyen_account_id', required_if_provider='odoo')

    def odoo_create_adyen_account(self):
        return self.env['adyen.account'].action_create_redirect()

    def _odoo_get_api_url(self):
        self.ensure_one()
        proxy_url = self.env['ir.config_parameter'].sudo().get_param('adyen_platforms.proxy_url')
        url = 'v1/pay_by_link' if self.state == 'enabled' else 'v1/test_pay_by_link'
        return urls.url_join(proxy_url, url)

    def _odoo_compute_shopper_reference(self, partner_id):
        """ Compute a unique reference of the partner for Adyen.

        This is used for the `shopperReference` field in communications with Adyen.

        :param recordset partner_id: The partner making the transaction, as a `res.partner` id
        :return: The unique reference for the partner
        :rtype: str
        """
        return f'{self.odoo_adyen_account_id.adyen_uuid}_{partner_id}'

    def _get_default_payment_method_id(self):
        self.ensure_one()
        if self.provider != 'odoo':
            return super()._get_default_payment_method_id()
        return self.env.ref('payment_odoo.payment_method_odoo').id
