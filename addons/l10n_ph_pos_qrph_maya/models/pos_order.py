# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    l10n_ph_qrph_transaction_ids = fields.One2many(
        comodel_name='l10n_ph.qrph.transaction',
        inverse_name='res_id',
        string="QRPH Codes",
        domain=[('res_model', '=', 'pos.order')],
        groups='account.group_account_invoice',
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        # An order reaches the database once it is paid, so the codes shown to pay it were minted
        # against its uuid and are only now attachable to the record itself.
        # sudo: the cashier storing the order is not the accountant the codes are readable by.
        transactions = self.env['l10n_ph.qrph.transaction'].sudo().search([
            ('pos_order_uuid', 'in', orders.mapped('uuid')),
            ('res_id', '=', False),
        ])
        if transactions:
            transactions_per_uuid = transactions.grouped('pos_order_uuid')
            for order in orders:
                if minted := transactions_per_uuid.get(order.uuid):
                    minted.res_id = order.id
        return orders
