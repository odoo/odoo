# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from odoo import api, fields, models, _


class ExpiryPickingConfirmation(models.TransientModel):
    _name = 'expiry.picking.confirmation'
    _description = 'Confirm Expiry'

    move_line_ids = fields.Many2many('stock.move.line', readonly=True, required=True)
    description = fields.Char('Description', compute='_compute_descriptive_fields')
    show_lots = fields.Boolean('Show Lots', compute='_compute_descriptive_fields')

    @api.depends('move_line_ids')
    def _compute_descriptive_fields(self):
        # Shows expired lots only if we are more than one expired lot.
        self.show_lots = len(self.move_line_ids.mapped('lot_id')) > 1
        if self.show_lots:
            # For multiple expired lots, they are listed in the wizard view.
            self.description = _(
                "You are going to process some products with expired lots."
                "\nDo you confirm you want to proceed?"
            )
        else:
            # For one expired lot, its name is written in the wizard message.
            self.description = _(
                "You are going to process the product %(product_name)s, %(lot_name)s which is expired or should at least be removed from stock."
                "\nDo you confirm you want to proceed?",
                product_name=", ".join(self.move_line_ids.mapped('product_id.display_name')),
                lot_name=", ".join(self.move_line_ids.mapped('lot_id.name'))
            )

    def process(self):
        picking_to_validate = self.env.context.get('button_validate_picking_ids')
        if picking_to_validate:
            picking_to_validate = self.env['stock.picking'].browse(picking_to_validate)
            ctx = dict(self.env.context, skip_expired=True)
            ctx.pop('default_move_line_ids')
            return picking_to_validate.with_context(ctx).button_validate()
        return True

    def process_no_expired(self):
        """ Remove the expired mls and confirm the picking. """
        pickings_to_validate = self.env['stock.picking'].browse(self.env.context.get('button_validate_picking_ids'))
        self.move_line_ids.filtered(
            lambda ml: ml.use_expiration_date and ml.removal_date and ml.removal_date < datetime.now()
        ).unlink()
        return pickings_to_validate.button_validate()
