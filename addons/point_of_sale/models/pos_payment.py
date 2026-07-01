from uuid import uuid4

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import formatLang


class PosPayment(models.Model):
    """ Used to register payments made in a pos.order.

    See `payment_ids` field of pos.order model.
    The main characteristics of pos.payment can be read from
    `payment_method_id`.
    """

    _name = 'pos.payment'
    _description = "Point of Sale Payment"
    _order = "id desc"
    _inherit = ['pos.load.mixin']

    name = fields.Char(string='Label', readonly=True)
    pos_order_id = fields.Many2one('pos.order', string='Order', required=True, index=True, ondelete='cascade')
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id', help="Total amount of the payment.")
    payment_method_id = fields.Many2one('pos.payment.method', string='Payment Method', required=True)
    payment_date = fields.Datetime(string='Date', required=True, readonly=True, default=lambda self: fields.Datetime.now())
    currency_id = fields.Many2one('res.currency', string='Currency', related='pos_order_id.currency_id')
    currency_rate = fields.Float(string='Conversion Rate', related='pos_order_id.currency_rate', help='Conversion rate from company currency to order currency.')
    partner_id = fields.Many2one('res.partner', string='Customer', related='pos_order_id.partner_id')
    session_id = fields.Many2one('pos.session', string='Session', related='pos_order_id.session_id', store=True, index=True)
    user_id = fields.Many2one('res.users', string='Employee', related='session_id.user_id')
    company_id = fields.Many2one('res.company', string='Company', related='pos_order_id.company_id', store=True)
    card_type = fields.Char(string='Type of card used', help='The type of the payment card (e.g. CREDIT CARD OR DEBIT CARD)')
    card_brand = fields.Char(string='Brand of card', help='The brand of the payment card (e.g. Visa, AMEX, ...)')
    card_no = fields.Char(string='Card Number(Last 4 Digit)')
    cardholder_name = fields.Char(string='Card Owner name')
    payment_ref_no = fields.Char(string='Payment reference number', help='Payment reference number from payment provider terminal')
    payment_method_authcode = fields.Char(string='Payment APPR Code')
    payment_method_issuer_bank = fields.Char(string='Payment Issuer Bank')
    payment_method_payment_mode = fields.Char(string='Payment Mode')
    transaction_id = fields.Char(string='Payment Transaction ID')
    payment_status = fields.Char(string='Payment Status')
    ticket = fields.Char(string='Payment Receipt Info')
    is_change = fields.Boolean(string='Is this payment change?', default=False)
    account_move_id = fields.Many2one('account.move', index='btree_not_null')
    uuid = fields.Char(string='Uuid', readonly=True, default=lambda self: str(uuid4()), copy=False)
    qr_code = fields.Char(string='QR Code', readonly=True, copy=False)

    _unique_uuid = models.Constraint('unique (uuid)', 'A payment with this uuid already exists')

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('pos_order_id', 'in', [order['id'] for order in data['pos.order']])]

    @api.model
    def _get_additional_payment_fields(self):
        # This method is overridden by payment terminal modules to
        # indicate additional fields that are safe to process from
        # the Self Order Kiosk frontend.
        # It is defined here rather than in `pos_self_order` so that
        # the payment terminal modules don't need to depend on it.
        return []

    @api.depends('amount', 'currency_id')
    def _compute_display_name(self):
        for payment in self:
            if payment.name:
                payment.display_name = f'{payment.name} {formatLang(self.env, payment.amount, currency_obj=payment.currency_id)}'
            else:
                payment.display_name = formatLang(self.env, payment.amount, currency_obj=payment.currency_id)

    @api.constrains('amount')
    def _check_amount(self):
        for payment in self:
            if payment.pos_order_id.state == 'done' or payment.pos_order_id.account_move:
                raise ValidationError(_('You cannot edit a payment for a posted order.'))

    @api.constrains('payment_method_id')
    def _check_payment_method_id(self):
        for payment in self:
            if payment.payment_method_id not in payment.session_id.config_id.payment_method_ids:
                raise ValidationError(_('The payment method selected is not allowed in the config of the POS session.'))
