# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.exceptions import UserError


class PosMakeInvoice(models.TransientModel):
    _inherit = 'pos.make.invoice'

    def action_create_invoices(self):
        orders = self.env['pos.order'].browse(self.env.context.get('active_ids'))
        b2c_orders = orders.filtered('l10n_in_b2c_invoice_number')
        if self.consolidated_billing and len(orders) > 1 and b2c_orders:
            raise UserError(self.env._(
                'Consolidated billing is not available for PoS orders with a B2C invoice number. '
                'Invoice them one by one or untick Consolidated Billing.\n\n%s',
                '\n'.join(b2c_orders.mapped('name')),
            ))
        return super().action_create_invoices()
