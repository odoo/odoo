from odoo import fields, models

class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('cinetpay', 'CinetPay')], ondelete={'cinetpay': 'set default'})
    cinetpay_api_key = fields.Char(string="API Key", required_if_provider='cinetpay')
    cinetpay_site_id = fields.Char(string="Site ID", required_if_provider='cinetpay')
    cinetpay_notify_url = fields.Char(string="Notify URL", readonly=True, compute='_compute_notify_url')

    def _compute_notify_url(self):
        for provider in self:
            provider.cinetpay_notify_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') + '/payment/cinetpay/notify'
