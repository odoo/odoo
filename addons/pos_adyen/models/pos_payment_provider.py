from odoo import fields, models


class PosPaymentProvider(models.Model):
    _inherit = 'pos.payment.provider'

    code = fields.Selection(selection_add=[('adyen', 'Adyen')], ondelete={'adyen': 'set default'})
    adyen_api_key = fields.Char(
        string='Adyen API key',
        help='Used when connecting to Adyen: https://docs.adyen.com/user-management/how-to-get-the-api-key/#description',
        copy=False, groups='base.group_erp_manager')
