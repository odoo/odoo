# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class ExpiryPickingConfirmation(models.TransientModel):
    _inherit = 'expiry.picking.confirmation'

    production_ids = fields.Many2many('mrp.production', readonly=True)
    workorder_id = fields.Many2one('mrp.workorder', readonly=True)

    def _compute_descriptive_fields(self):
        if self.production_ids or self.workorder_id:
            self.show_list = len(self.move_line_ids) > 1
            self.show_lots = bool(self.move_line_ids.lot_id)
            if self.show_list:
                # For multiple expired lots, they are listed in the wizard view.
                self.description = _(
                    "You are going to use some expired components."
                    "\nDo you confirm you want to proceed?"
                )
            else:
                # For one expired lot, its name is written in the wizard message.
                self.description = _(
                    "You are going to use the component %(product_name)s, %(lot_name)s which is expired."
                    "\nDo you confirm you want to proceed?",
                    product_name=self.move_line_ids.product_id.display_name,
                    lot_name=self.move_line_ids.lot_id.name,
                )
        else:
            super()._compute_descriptive_fields()

    def confirm_produce(self):
        ctx = dict(self.env.context, skip_expired=True)
        ctx.pop('default_move_line_ids')
        return self.production_ids.with_context(ctx).button_mark_done()

    def confirm_workorder(self):
        ctx = dict(self.env.context, skip_expired=True)
        ctx.pop('default_move_line_ids')
        return self.workorder_id.with_context(ctx).record_production()
