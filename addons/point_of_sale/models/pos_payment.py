from odoo import api, fields, models, _
from odoo.tools import formatLang


class PosPayment(models.Model):
    """ Used to register payments made in a pos.order.

    See `payment_ids` field of pos.order model.
    The main characteristics of pos.payment can be read from
    `payment_method_id`.
    """

    _name = "pos.payment"
    _description = "Point of Sale Payments"
    _order = "id desc"

    name = fields.Char(string='Label', readonly=True)
    pos_order_id = fields.Many2one('pos.order', string='Order', required=True)
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id', readonly=True, help="Total amount of the payment.")
    payment_method_id = fields.Many2one('pos.payment.method', string='Payment Method', required=True)
    payment_date = fields.Datetime(string='Date', required=True, readonly=True, default=lambda self: fields.Datetime.now())
    currency_id = fields.Many2one('res.currency', string='Currency', related='pos_order_id.currency_id')
    currency_rate = fields.Float(string='Conversion Rate', related='pos_order_id.currency_rate', help='Conversion rate from company currency to order currency.')
    partner_id = fields.Many2one('res.partner', string='Customer', related='pos_order_id.partner_id')
    session_id = fields.Many2one('pos.session', string='Session', related='pos_order_id.session_id', store=True)
    company_id = fields.Many2one('res.company', string='Company', related='pos_order_id.company_id')
    card_type = fields.Char('Type of card used')
    transaction_id = fields.Char('Payment Transaction ID')

    @api.model
    def name_get(self):
        res = []
        for payment in self:
            if payment.name:
                res.append((payment.id, _('%s %s') % (payment.name, formatLang(self.env, payment.amount, currency_obj=payment.currency_id))))
            else:
                res.append((payment.id, formatLang(self.env, payment.amount, currency_obj=payment.currency_id)))
        return res
