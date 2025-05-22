# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import api, fields, models
from odoo.tools import format_date, str2bool
from odoo.tools.translate import _

from odoo.addons.payment import utils as payment_utils
from odoo.tools.image import image_data_uri


class AccountMove(models.Model):
    _inherit = 'account.move'

    transaction_ids = fields.Many2many(
        string="Transactions", comodel_name='payment.transaction',
        relation='account_invoice_transaction_rel', column1='invoice_id', column2='transaction_id',
        readonly=True, copy=False)
    authorized_transaction_ids = fields.Many2many(
        string="Authorized Transactions", comodel_name='payment.transaction',
        compute='_compute_authorized_transaction_ids', readonly=True, copy=False,
        compute_sudo=True)
    transaction_count = fields.Integer(
        string="Transaction Count", compute='_compute_transaction_count'
    )
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
    def _compute_transaction_count(self):
        for invoice in self:
            invoice.transaction_count = len(invoice.transaction_ids)

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
        transactions = self.transaction_ids.filtered(lambda tx: tx.state in ('pending', 'authorized', 'done'))
        pending_transactions = transactions.filtered(
            lambda tx: tx.state in {'pending', 'authorized'}
                       and tx.provider_code not in {'none', 'custom'})
        enabled_feature = str2bool(
            self.env['ir.config_parameter'].sudo().get_param(
                'account_payment.enable_portal_payment'
            )
        )
        return enabled_feature and bool(
            (self.amount_residual or not transactions)
            and self.state == 'posted'
            and self.payment_state in ('not_paid', 'in_payment', 'partial')
            and not self.currency_id.is_zero(self.amount_residual)
            and self.amount_total
            and self.move_type == 'out_invoice'
            and not pending_transactions
        )

    def _get_online_payment_error(self):
        """
        Returns the appropriate error message to be displayed if _has_to_be_paid() method returns False.
        """
        self.ensure_one()
        transactions = self.transaction_ids.filtered(lambda tx: tx.state in ('pending', 'authorized', 'done'))
        pending_transactions = transactions.filtered(
            lambda tx: tx.state in {'pending', 'authorized'}
                       and tx.provider_code not in {'none', 'custom'})
        enabled_feature = str2bool(
            self.env['ir.config_parameter'].sudo().get_param(
                'account_payment.enable_portal_payment'
            )
        )
        errors = []
        if not enabled_feature:
            errors.append(_("This invoice cannot be paid online."))
        if transactions or self.currency_id.is_zero(self.amount_residual):
            errors.append(_("There is no amount to be paid."))
        if self.state != 'posted':
            errors.append(_("This invoice isn't posted."))
        if self.currency_id.is_zero(self.amount_residual):
            errors.append(_("This invoice has already been paid."))
        if self.move_type != 'out_invoice':
            errors.append(_("This is not an outgoing invoice."))
        if pending_transactions:
            errors.append(_("There are pending transactions for this invoice."))
        return '\n'.join(errors)

    @api.private
    def get_portal_last_transaction(self):
        self.ensure_one()
        return self.with_context(active_test=False).sudo().transaction_ids._get_last()

    def payment_action_capture(self):
        """ Capture all transactions linked to this invoice. """
        self.ensure_one()
        payment_utils.check_rights_on_recordset(self)

        # In sudo mode to bypass the checks on the rights on the transactions.
        return self.sudo().transaction_ids.action_capture()

    def payment_action_void(self):
        """ Void all transactions linked to this invoice. """
        payment_utils.check_rights_on_recordset(self)

        # In sudo mode to bypass the checks on the rights on the transactions.
        self.sudo().authorized_transaction_ids.action_void()

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
        next_payment_values = self._get_invoice_next_payment_values()
        amount_max = next_payment_values.get('amount_due')
        additional_info = {}
        open_installments = []
        installment_state = next_payment_values.get('installment_state')
        next_amount_to_pay = next_payment_values.get('next_amount_to_pay')
        if installment_state in ('next', 'overdue'):
            open_installments = []
            for installment in next_payment_values.get('not_reconciled_installments'):
                data = {
                    'type': installment['type'],
                    'number': installment['number'],
                    'amount': installment['amount_residual_currency_unsigned'],
                    'date_maturity': format_date(self.env, installment['date_maturity']),
                }
                open_installments.append(data)

        elif installment_state == 'epd':
            amount_max = next_amount_to_pay  # with epd, next_amount_to_pay is the invoice amount residual
            additional_info.update({
                'has_eligible_epd': True,
                'discount_date': next_payment_values.get('discount_date')
            })

        return {
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'open_installments': open_installments,
            'amount': next_amount_to_pay,
            'amount_max': amount_max,
            **additional_info
        }

    def _generate_portal_payment_qr(self):
        self.ensure_one()
        portal_url = self._get_portal_payment_link()
        barcode = self.env['ir.actions.report'].barcode(barcode_type="QR", value=portal_url, width=128, height=128, quiet=False)
        return image_data_uri(base64.b64encode(barcode))

    def _get_portal_payment_link(self):
        self.ensure_one()
        payment_link_wizard = self.env['payment.link.wizard'].with_context(
            active_id=self.id, active_model=self._name
        ).create({
            'amount': self.amount_residual,
            'res_model': self._name,
            'res_id': self.id,
        })
        return payment_link_wizard.link
