from odoo import api, fields, models, _
from odoo.tools import formatLang, float_is_zero
from odoo.exceptions import ValidationError
from uuid import uuid4


class PosPayment(models.Model):
    """ Used to register payments made in a pos.order.

    See `payment_ids` field of pos.order model.
    The main characteristics of pos.payment can be read from
    `payment_method_id`.
    """

    _name = "pos.payment"
    _description = "Point of Sale Payments"
    _order = "id desc"
    _inherit = ['pos.load.mixin']

    name = fields.Char(string='Label', readonly=True)
    pos_order_id = fields.Many2one('pos.order', string='Order', required=True, index=True)
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

    @api.model
    def _load_pos_data_domain(self, data):
        return [('pos_order_id', 'in', [order['id'] for order in data['pos.order']['data']])]

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
            if payment.pos_order_id.state in ['invoiced', 'done']:
                raise ValidationError(_('You cannot edit a payment for a posted order.'))
            elif payment.pos_order_id.nb_print > 0:
                raise ValidationError(_('You cannot edit a payment for a printed order.'))

    @api.constrains('payment_method_id')
    def _check_payment_method_id(self):
        for payment in self:
            if payment.payment_method_id not in payment.session_id.config_id.payment_method_ids:
                raise ValidationError(_('The payment method selected is not allowed in the config of the POS session.'))

    def _create_payment_moves(self, is_reverse=False):
        result = self.env['account.move']
        for payment in self:
            order = payment.pos_order_id
            payment_method = payment.payment_method_id
            if payment_method.type == 'pay_later' or float_is_zero(payment.amount, precision_rounding=order.currency_id.rounding):
                continue
            accounting_partner = self.env["res.partner"]._find_accounting_partner(payment.partner_id)
            pos_session = order.session_id
            journal = pos_session.config_id.journal_id
            payment_move = self.env['account.move'].with_context(default_journal_id=journal.id).create({
                'journal_id': journal.id,
                'date': fields.Date.context_today(order, order.date_order),
                'ref': _('Invoice payment for %(order)s (%(account_move)s) using %(payment_method)s', order=order.name, account_move=order.account_move.name, payment_method=payment_method.name),
                'pos_payment_ids': payment.ids,
            })
            result |= payment_move
            payment.write({'account_move_id': payment_move.id})
            amounts = pos_session._update_amounts({'amount': 0, 'amount_converted': 0}, {'amount': payment.amount}, payment.payment_date)
            credit_line_vals = pos_session._credit_amounts({
                'account_id': accounting_partner.with_company(order.company_id).property_account_receivable_id.id,  # The field being company dependant, we need to make sure the right value is received.
                'partner_id': accounting_partner.id,
                'move_id': payment_move.id,
            }, amounts['amount'], amounts['amount_converted'])
            is_split_transaction = payment.payment_method_id.split_transactions
            if is_split_transaction and is_reverse:
                reversed_move_receivable_account_id = accounting_partner.with_company(order.company_id).property_account_receivable_id.id
            elif is_reverse:
                reversed_move_receivable_account_id = payment.payment_method_id.receivable_account_id.id or self.company_id.account_default_pos_receivable_account_id.id
            else:
                reversed_move_receivable_account_id = self.company_id.account_default_pos_receivable_account_id.id
            debit_line_vals = pos_session._debit_amounts({
                'account_id': reversed_move_receivable_account_id,
                'move_id': payment_move.id,
                'partner_id': accounting_partner.id if is_split_transaction and is_reverse else False,
            }, amounts['amount'], amounts['amount_converted'])
            self.env['account.move.line'].create([credit_line_vals, debit_line_vals])
            payment_move._post()
        return result
