# coding: utf-8

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    payment_token_id = fields.Many2one('payment.token',
        string='Saved payment token', domain=[('acquirer_id.capture_manually', '=', False)],
        help='Note that tokens from acquirers set to only authorize transactions (instead of capturing the amount) are not available.')

    payment_transaction_id = fields.Many2one('payment.transaction', string='Transaction', copy=False)

    payment_transaction_acquirer_name = fields.Char(related='payment_transaction_id.acquirer_id.name',
                                                    string='Transaction Acquirer Name')
    payment_transaction_capture = fields.Boolean(related='payment_transaction_id.capture',
                                                 string='Transaction Capture')
    payment_transaction_pending = fields.Boolean(related='payment_transaction_id.pending',
                                                 string='Transaction Pending')

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        res = {}
        if self.partner_id:
            partners = self.partner_id | self.partner_id.commercial_partner_id | self.partner_id.commercial_partner_id.child_ids
            res['domain'] = {'payment_token_id': [('partner_id', 'in', partners.ids), ('acquirer_id.capture_manually', '=', False)]}

        return res

    @api.onchange('payment_method_id', 'journal_id')
    def _onchange_payment_method(self):
        if self.payment_method_code == 'electronic':
            self.payment_token_id = self.env['payment.token'].search([('partner_id', '=', self.partner_id.id), ('acquirer_id.capture_manually', '=', False)], limit=1)
        else:
            self.payment_token_id = False

    @api.multi
    def post(self):
        payments_to_send = self.filtered(lambda p: p.payment_transaction_id and not p.payment_transaction_id.pending)
        for trans in payments_to_send.mapped('payment_transaction_id'):
            trans.s2s_do_transaction()
        return super(AccountPayment, self - payments_to_send).post()

    @api.multi
    def with_transaction(self, vals):
        ''' Create a payment transaction and attach it to the payment.

        If a transaction already exists for this payment, this method does nothing.

        :param vals: The values to create the transaction.
        :return self
        '''

        # The transaction could already exist, see the create method.
        if any(p.payment_transaction_id for p in self):
            raise ValidationError(_('A payment can\'t have more than one transaction.'))

        for pay in self:
            trans_vals = vals if len(self) == 1 else vals.copy()
            trans_vals['payment_id'] = pay.id

            pay.payment_transaction_id = self.env['payment.transaction'].create(vals)

        return self

    @api.model
    def create(self, vals):
        payment = super(AccountPayment, self).create(vals)

        # Handle the following scenario:
        # - Register a payment using a journal having electronic debit method.
        # - Use an existing token.
        # In this case, the transaction must be created at the payment creation.
        if payment.payment_token_id:
            if payment.payment_token_id.acquirer_id.capture_manually:
                raise ValidationError(
                    _('This feature is not available for payment acquirers set to the "Capture" mode.\n'
                      'Please use a token from another provider than %s.') % payment.payment_token_id.acquirer_id.name)

            transaction_vals = {
                'acquirer_id': payment.payment_token_id.acquirer_id.id,
                'type': 'server2server',
            }

            return payment.with_transaction(transaction_vals)
        return payment

    @api.multi
    def _check_payment_transaction_id(self):
        if any(not p.payment_transaction_id for p in self):
            raise ValidationError(_('Only payments linked to some transactions can be proceeded.'))

    @api.multi
    def action_capture(self):
        self._check_payment_transaction_id()
        payment_transaction_ids = self.mapped('payment_transaction_id')
        if any(not t or not t.capture for t in payment_transaction_ids):
            raise ValidationError(_('Only transactions having the capture status can be captured.'))
        payment_transaction_ids.s2s_capture_transaction()

    @api.multi
    def action_void(self):
        self._check_payment_transaction_id()
        payment_transaction_ids = self.mapped('payment_transaction_id')
        if any(not t.capture for t in payment_transaction_ids):
            raise ValidationError(_('Only transactions having the capture status can be voided.'))
        payment_transaction_ids.s2s_void_transaction()
