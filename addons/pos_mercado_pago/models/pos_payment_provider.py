from odoo import fields, models, _
from odoo.exceptions import UserError


class PosPaymentProvider(models.Model):
    _inherit = 'pos.payment.provider'

    code = fields.Selection(selection_add=[('mercado_pago', 'Mercado Pago')], ondelete={'mercado_pago': 'set default'})
    mp_bearer_token = fields.Char(
        string='Production user token',
        help='Mercado Pago customer production user token: https://www.mercadopago.com.mx/developers/en/reference',
        groups='point_of_sale.group_pos_manager', copy=False)
    mp_webhook_secret_key = fields.Char(
        string='Production secret key',
        help='Mercado Pago production secret key from integration application: https://www.mercadopago.com.mx/developers/panel/app',
        groups='point_of_sale.group_pos_manager', copy=False)

    def write(self, vals):
        for record in self:
            if record.code == 'mercado_pago' and vals.get('mode') == 'test':
                raise UserError(_("This payment provider doesn't have Test Mode."))
        return super().write(vals)
