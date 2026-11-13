from odoo import api, fields, models, _


class PaymentEntry(models.Model):
    _name = 'payment.entry'
    _description = 'Payment Entry'
    _order = 'payment_date desc, id desc'

    payment_id = fields.Many2one('customer.payment', string='Payment', required=True, ondelete='cascade')
    payment_date = fields.Date(string='Receiving Date', required=True, default=fields.Date.context_today)
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    note = fields.Text(string='Note')

    currency_id = fields.Many2one('res.currency', string='Currency',
                                   related='payment_id.currency_id', store=True, readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer',
                                  related='payment_id.partner_id', store=True, readonly=True)

    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount < 0:
                raise models.ValidationError(_('Payment amount must be positive.'))
