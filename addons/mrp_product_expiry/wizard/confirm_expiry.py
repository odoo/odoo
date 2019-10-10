# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ConfirmExpiry(models.TransientModel):
    _inherit = 'expiry.picking.confirmation'

    produce_id = fields.Many2one('mrp.product.produce', readonly=True)
    workorder_id = fields.Many2one('mrp.workorder', readonly=True)

    @api.depends('lot_ids')
    def _compute_descriptive_fields(self):
        if self.produce_id or self.workorder_id:
            # Shows expired lots only if we are more than one expired lot.
            self.show_lots = len(self.lot_ids) > 1
            if self.show_lots:
                # For multiple expired lots, they are listed in the wizard view.
                self.description = _(
                    "You are going to use some expired components."
                    "\nDo you confirm you want to proceed ?"
                )
            else:
                # For one expired lot, its name is written in the wizard message.
                self.description = _(
                    "You are going to use the component %s, %s which is expired."
                    "\nDo you confirm you want to proceed ?" % (
                        self.lot_ids.product_id.display_name,
                        self.lot_ids.name,
                    )
                )
        else:
            super(ConfirmExpiry, self)._compute_descriptive_fields()

    def confirm_produce(self):
        return self.produce_id.with_context(skip_expired=True).do_produce()

    def confirm_workorder(self):
        return self.workorder_id.with_context(skip_expired=True).record_production()

    def return_to_produce_wizard(self):
        production = self.produce_id.production_id
        action = production.open_produce_product()
        action['context'] = {'default_production_id': production.id}
        return action
