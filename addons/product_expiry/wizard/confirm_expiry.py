# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ConfirmExpiry(models.TransientModel):
    _name = 'expiry.picking.confirmation'
    _description = 'Confirm Expiry'

    lot_ids = fields.Many2many('stock.lot', readonly=True, required=True)
    picking_ids = fields.Many2many('stock.picking', readonly=True)
    description = fields.Char('Description', compute='_compute_descriptive_fields')
    show_lots = fields.Boolean('Show Lots', compute='_compute_descriptive_fields')

    @api.depends('lot_ids')
    def _compute_descriptive_fields(self):
        # Shows expired lots only if we are more than one expired lot.
        self.show_lots = len(self.lot_ids) > 1
        if self.show_lots:
            # For multiple expired lots, they are listed in the wizard view.
            self.description = _(
                "You are going to deliver some product expired lots."
                "\nDo you confirm you want to proceed ?"
            )
        else:
            # For one expired lot, its name is written in the wizard message.
            self.description = _(
                "You are going to deliver the product %(product_name)s, %(lot_name)s which is expired."
                "\nDo you confirm you want to proceed ?",
                product_name=self.lot_ids.product_id.display_name,
                lot_name=self.lot_ids.name
            )

    def process(self):
        picking_to_validate = self.env.context.get('button_validate_picking_ids')
        if picking_to_validate:
            picking_to_validate = self.env['stock.picking'].browse(picking_to_validate)
            ctx = dict(self.env.context, skip_expired=True)
            ctx.pop('default_lot_ids')
            return picking_to_validate.with_context(ctx).button_validate()
        return True

    def process_no_expired(self):
        """ Don't process for concerned pickings (ones with expired lots), but
        process for all other pickings (in case of multi). """
        # Remove `self.pick_ids` from `button_validate_picking_ids` and call
        # `button_validate` with the subset (if any).
        pickings_to_validate = self.env['stock.picking'].browse(self.env.context.get('button_validate_picking_ids'))
        pickings_to_validate = pickings_to_validate - self.picking_ids
        if pickings_to_validate:
            return pickings_to_validate.with_context(skip_expired=True).button_validate()
        return True
