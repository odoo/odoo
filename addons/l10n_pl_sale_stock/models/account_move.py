from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_pl_delivery_date = fields.Date(
        compute='_compute_l10n_pl_delivery_date', store=True,
    )

    @api.depends('line_ids.sale_line_ids.order_id.effective_date')
    def _compute_l10n_pl_delivery_date(self):
        for move in self:
            sale_order_effective_date = list(filter(None, move.line_ids.sale_line_ids.order_id.mapped('effective_date')))
            effective_date_res = max(sale_order_effective_date) if sale_order_effective_date else False
            # if multiple sale order we take the bigger effective_date
            if effective_date_res:
                move.l10n_pl_delivery_date = effective_date_res
