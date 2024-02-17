# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _l10n_hu_edi_fix_fields(self):
        """
        This method is invoiked *before* the posting of an invoice. It sets various variables, for example delivery date.
        The devilvery date is the delivery of the goods.
        """
        for move in self:
            sale_order_effective_date = list(
                filter(None, move.line_ids.sale_line_ids.order_id.mapped("effective_date"))
            )
            # if multiple sale order we take the bigger effective_date
            effective_date_res = max(sale_order_effective_date) if sale_order_effective_date else False
            if effective_date_res:
                move.delivery_date = effective_date_res

        super()._l10n_hu_edi_fix_fields()
