# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

from odoo.addons.l10n_ph_qrph_maya import const


class PosOrder(models.Model):
    _inherit = 'pos.order'

    l10n_ph_qrph_transaction_ids = fields.One2many(
        comodel_name='l10n_ph.qrph.transaction',
        inverse_name='res_id',
        string="QRPH Transactions",
        domain=[('res_model', '=', 'pos.order')],
        groups='account.group_account_invoice',
        copy=False,
    )

    @api.model
    def _process_order(self, order, existing_order):
        order_uuid = order.get('uuid')
        order_id = super()._process_order(order, existing_order)
        pos_order = self.browse(order_id)
        # An order reaches the database once it is paid, so the codes shown to pay it were minted
        # against its uuid and are only now attachable to the record itself.
        # sudo: the cashier storing the order may read the transactions of its orders, not write them.
        self.env['l10n_ph.qrph.transaction'].sudo().search([
            ('pos_order_uuid', '=', order_uuid),
            ('company_id', '=', pos_order.company_id.id),
            ('res_id', '=', False),
        ]).res_id = order_id
        if pos_order.state in ('paid', 'done'):
            pos_order._l10n_ph_qrph_settle_transactions()
        return order_id

    def _l10n_ph_qrph_settle_transactions(self):
        """ Mark as settled the paid QRPH transactions that paid the QRPH payments of this order.

        This keeps a transaction from paying a second time once its payment is recorded.
        """
        self.ensure_one()
        # sudo: the cashier storing the order may read the transactions of its orders, not write them.
        transactions = self.env['l10n_ph.qrph.transaction'].sudo().search([
            ('res_model', '=', 'pos.order'),
            ('res_id', '=', self.id),
            ('state', '=', 'paid'),
            ('settled_date', '=', False),
        ])
        qrph_payments = self.payment_ids.filtered(
            lambda payment: payment.payment_method_id.payment_method_type == 'bank_qr_code'
            and payment.payment_method_id.qr_code_method == const.QR_METHOD
        )
        for payment in qrph_payments:
            settled = transactions.filtered(
                lambda transaction: transaction.currency_id.compare_amounts(transaction.amount, payment.amount) >= 0,
            )[:1]
            settled.settled_date = fields.Datetime.now()
            transactions -= settled
