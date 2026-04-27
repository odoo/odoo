# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _create_invoices(self, grouped=False, final=False, date=None):
        """Override to automatically populate all not yet used packages of the latest validated picking. Don't set a
        default if there are backorders or split pickings."""
        invoices = super()._create_invoices(grouped=grouped, final=final, date=date)
        for invoice in invoices:
            root_pickings = invoice._l10n_br_get_pickings()
            root_pickings -= root_pickings.mapped(lambda picking: picking._get_next_transfers())
            is_simple = len(root_pickings) == 1 and all(len(picking._get_next_transfers()) <= 1 for picking in invoice._l10n_br_get_pickings())
            if is_simple:
                invoice.l10n_br_package_ids = invoice.l10n_br_related_package_ids.filtered(
                    lambda package: not package.l10n_br_move_id
                )

        return invoices
