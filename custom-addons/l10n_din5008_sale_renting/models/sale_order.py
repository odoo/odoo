# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _compute_l10n_din5008_document_title(self):
        """Override of l10n_din5008_sale to title pickup receipts."""
        for record in self:
            if (
                record.state not in ('draft', 'sent')
                and self._context.get('pickup_receipt')
                and not self._context.get('proforma')
            ):
                record.l10n_din5008_document_title = _("Pickup Receipt")
            else:
                super(SaleOrder, record)._compute_l10n_din5008_document_title()
