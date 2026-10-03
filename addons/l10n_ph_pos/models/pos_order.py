# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    l10n_ph_qrph_transaction_ids = fields.Many2many(
        comodel_name='l10n_ph.qrph.transaction',
        string="QRPH Codes",
        groups='account.group_account_invoice',
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        # EXTENDS point_of_sale
        orders = super().create(vals_list)
        # An order reaches the database once it is paid, so the codes shown to pay it were minted
        # against its uuid and are only now attachable to the record itself.
        # sudo: the cashier storing the order is not the accountant the codes are readable by.
        transactions = self.env['l10n_ph.qrph.transaction'].sudo().search([
            ('model', '=', 'pos.order'),
            ('model_id', 'in', orders.mapped('uuid')),
        ])
        if transactions:
            transactions_per_uuid = transactions.grouped('model_id')
            for order in orders:
                if minted := transactions_per_uuid.get(order.uuid):
                    order.sudo().l10n_ph_qrph_transaction_ids = minted
        return orders
