# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from odoo.addons.payment import utils as payment_utils


class AccountMove(models.Model):
    _inherit = 'account.move'

    transaction_ids = fields.Many2many(
        string="Transactions", comodel_name='payment.transaction',
        relation='account_invoice_transaction_rel', column1='invoice_id', column2='transaction_id',
        readonly=True, copy=False)
    authorized_transaction_ids = fields.Many2many(
        string="Authorized Transactions", comodel_name='payment.transaction',
        compute='_compute_authorized_transaction_ids', readonly=True, copy=False)
    amount_paid = fields.Monetary(
        string="Amount paid",
        compute='_compute_amount_paid'
    )

    @api.depends('transaction_ids')
    def _compute_authorized_transaction_ids(self):
        for invoice in self:
            invoice.authorized_transaction_ids = invoice.transaction_ids.filtered(
                lambda tx: tx.state == 'authorized'
            )

    @api.depends('transaction_ids')
    def _compute_amount_paid(self):
        """ Sum all the transaction amount for which state is in 'authorized' or 'done'
        """
        for invoice in self:
            invoice.amount_paid = sum(
                invoice.transaction_ids.filtered(
                    lambda tx: tx.state in ('authorized', 'done')
                ).mapped('amount')
            )

    def _has_to_be_paid(self):
        self.ensure_one()
        transactions = self.transaction_ids.filtered(lambda tx: tx.state in ('authorized', 'done'))
        return bool(
            (
                self.amount_residual
                # FIXME someplace we check amount_residual and some other amount_paid < amount_total
                # what is the correct heuristic to check ?
                or not transactions
            )
            and self.state == 'posted'
            and self.payment_state in ('not_paid', 'partial')
            and self.amount_total
            and self.move_type == 'out_invoice'
        )

    def get_portal_last_transaction(self):
        self.ensure_one()
        return self.with_context(active_test=False).transaction_ids._get_last()

    def payment_action_capture(self):
        """ Capture all transactions linked to this invoice. """
        payment_utils.check_rights_on_recordset(self)
        # In sudo mode because we need to be able to read on provider fields.
        self.authorized_transaction_ids.sudo().action_capture()

    def payment_action_void(self):
        """ Void all transactions linked to this invoice. """
        payment_utils.check_rights_on_recordset(self)
        # In sudo mode because we need to be able to read on provider fields.
        self.authorized_transaction_ids.sudo().action_void()

    def action_view_payment_transactions(self):
        action = self.env['ir.actions.act_window']._for_xml_id('payment.action_payment_transaction')

        if len(self.transaction_ids) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.transaction_ids.id
            action['views'] = []
        else:
            action['domain'] = [('id', 'in', self.transaction_ids.ids)]

        return action

    def _get_default_payment_link_values(self):
        self.ensure_one()
        return {
            'description': self.payment_reference,
            'amount': self.amount_residual,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'amount_max': self.amount_residual,
        }
