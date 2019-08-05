#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, api


class StockZeroQuantityCount(models.TransientModel):

    _name = 'stock.zero.quantity.count'
    _description = 'Zero Quantity Count'

    location_ids = fields.Many2many('stock.location')
    location_names = fields.Char('Locations Names', compute='_compute_location_names')

    @api.depends('location_ids')
    def _compute_location_names(self):
        self.location_names = ', '.join([name[name.find('/')+1:] for name in self.location_ids.mapped('complete_name')])

    def button_confirm_zqc(self):
        to_validate_pick_ids = self.env['stock.picking'].browse(self.env.context.get('to_validate_pick_ids'))
        return to_validate_pick_ids.with_context({'skip_zqc': True})._button_validate()

    def button_inventory(self):
        ids = self.env.context.get('to_validate_pick_ids')
        pickings = self.env['stock.picking'].browse(ids)
        inventory = self.env['stock.inventory'].create({
            'name': 'Zero Quantity Count adjustement',
            'location_ids': [(6, 0, self.location_ids.ids)],
            'start_empty': True
        })

        pickings.inventory_ids |= inventory
        res = inventory.action_start()
        res['context'].update({'to_validate_pick_ids': ids})
        res['target'] = 'new'

        # We override the view to hide the theoritical_qty and difference_qty as they're not relevant
        # when the inventory is triggered from a ZQC
        res['views'] = [(self.env.ref('stock.stock_inventory_line_tree_zqc').id, 'tree')]
        return res
