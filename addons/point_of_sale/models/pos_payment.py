from odoo import api, fields, models, _
from odoo.tools import formatLang, float_is_zero
from odoo.exceptions import ValidationError


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
    pos_order_id = fields.Many2one('pos.order', string='Order', required=True, index=True)
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id', readonly=True, help="Total amount of the payment.")
    payment_method_id = fields.Many2one('pos.payment.method', string='Payment Method', required=True)
    payment_date = fields.Datetime(string='Date', required=True, readonly=True, default=lambda self: fields.Datetime.now())
    currency_id = fields.Many2one('res.currency', string='Currency', related='pos_order_id.currency_id')
    currency_rate = fields.Float(string='Conversion Rate', related='pos_order_id.currency_rate', help='Conversion rate from company currency to order currency.')
    partner_id = fields.Many2one('res.partner', string='Customer', related='pos_order_id.partner_id')
    session_id = fields.Many2one('pos.session', string='Session', related='pos_order_id.session_id', store=True, index=True)
    company_id = fields.Many2one('res.company', string='Company', related='pos_order_id.company_id', store=True)
    card_type = fields.Char('Type of card used')
    cardholder_name = fields.Char('Cardholder Name')
    transaction_id = fields.Char('Payment Transaction ID')
    payment_status = fields.Char('Payment Status')
    ticket = fields.Char('Payment Receipt Info')
    is_change = fields.Boolean(string='Is this payment change?', default=False)
    account_move_id = fields.Many2one('account.move', index='btree_not_null')

    @api.depends('amount', 'currency_id')
    def _compute_display_name(self):
        for payment in self:
            if payment.name:
                payment.display_name = f'{payment.name} {formatLang(self.env, payment.amount, currency_obj=payment.currency_id)}'
            else:
                payment.display_name = formatLang(self.env, payment.amount, currency_obj=payment.currency_id)

    @api.constrains('payment_method_id')
    def _check_payment_method_id(self):
        for payment in self:
            if payment.payment_method_id not in payment.session_id.config_id.payment_method_ids:
                raise ValidationError(_('The payment method selected is not allowed in the config of the POS session.'))

    def _export_for_ui(self, payment):
        return {
            'payment_method_id': payment.payment_method_id.id,
            'amount': payment.amount,
            'pos_order_id': payment.pos_order_id.id,
            'payment_status': payment.payment_status,
            'card_type': payment.card_type,
            'cardholder_name': payment.cardholder_name,
            'transaction_id': payment.transaction_id,
            'ticket': payment.ticket,
            'is_change': payment.is_change,
        }

    def export_for_ui(self):
        return self.mapped(self._export_for_ui) if self else []

    def _create_payment_moves(self, is_reverse=False):
        result = self.env['account.move']
        credit_line_ids = []
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
                'ref': _('Invoice payment for %s (%s) using %s', order.name, order.account_move.name, payment_method.name),
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
            lines = self.env['account.move.line'].create([credit_line_vals, debit_line_vals])
            if amounts['amount_converted'] < 0:
                credit_line_ids += lines.filtered(lambda l: l.debit).ids
            else:
                credit_line_ids += lines.filtered(lambda l: l.credit).ids
            payment_move._post()
        return result.with_context(credit_line_ids=credit_line_ids)
