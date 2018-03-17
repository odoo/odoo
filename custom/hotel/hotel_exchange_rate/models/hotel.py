
from odoo.exceptions import except_orm
from odoo import models, fields, api, _
from decimal import Decimal


class CurrencyExchangeRate(models.Model):

    _inherit = "currency.exchange"

    @api.depends('input_curr', 'out_curr', 'in_amount')
    def _compute_get_currency(self):
        '''
        When you change input_curr, out_curr or in_amount
        it will update the out_amount of the currency exchange
        ------------------------------------------------------
        @param self: object pointer
        '''
        for rec in self:
            rec.out_amount = 0.0
            if rec.input_curr and rec.rate_source == 'online':
                result = rec.get_rate(rec.input_curr.name,
                                      rec.out_curr.name)
                if rec.out_curr:
                    rec.rates = result
                    if rec.rates == Decimal('-1.00'):
                        raise except_orm(_('Warning'),
                                         _('Please Check Your \
                                         Network Connectivity.'))
                    rec.out_amount = (float(result) * float(rec.in_amount))
            elif rec.input_curr and rec.rate_source == 'manual':
                if rec.out_curr:
                    rec.out_amount = (float(rec.rates) * float(rec.in_amount))

    rates = fields.Float('Rate', size=64, default=1.0, index=True)
    rate_source = fields.Selection([('manual', 'Manual'),
                                    ('online', 'Online')],
                                   string='Exchange Rate Source',
                                   default='manual',
                                   required=True)
