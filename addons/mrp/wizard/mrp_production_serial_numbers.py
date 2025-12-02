# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MrpProductionSerials(models.TransientModel):
    _name = 'mrp.production.serials'
    _description = 'Assign serial numbers to production order'

    production_id = fields.Many2one('mrp.production', 'Production')

    workorder_id = fields.Many2one('mrp.workorder', 'Workorder')

    lot_name = fields.Char('First SN', compute="_compute_lot_name", store=True, readonly=False)
    lot_quantity = fields.Integer('Number of SN', compute="_compute_lot_quantity", store=True, readonly=False)

    serial_numbers = fields.Text('Produced Serial Numbers', compute="_compute_lot_name", store=True, readonly=False)

    @api.depends('production_id')
    def _compute_lot_name(self):
        for wizard in self:
            wizard.serial_numbers = '\n'.join(self.production_id.lot_producing_ids.mapped('name'))
            if wizard.lot_name:
                continue
            wizard.lot_name = self.production_id.lot_producing_ids[:1].name
            if not wizard.lot_name:
                wizard.lot_name = self.production_id.product_id.serial_prefix_format + self.production_id.product_id.next_serial

    @api.depends('production_id')
    def _compute_lot_quantity(self):
        for wizard in self:
            wizard.lot_quantity = wizard.production_id.product_qty

    @api.onchange('serial_numbers')
    def _onchange_serial_numbers(self):
        lot_names = list(filter(lambda s: len(s.strip()) > 0, self.serial_numbers.split('\n'))) if self.serial_numbers else []
        self.serial_numbers = '\n'.join(list(dict.fromkeys(lot_names)))  # remove duplicate lot names

    def action_generate_serial_numbers(self):
        self.ensure_one()
        if self.lot_name and self.lot_quantity:
            lots = self.env['stock.lot'].generate_lot_names(self.lot_name, self.lot_quantity)
            self.serial_numbers = '\n'.join([lot['lot_name'] for lot in lots])
            self._onchange_serial_numbers()
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.action_assign_serial_numbers")
        action['res_id'] = self.id
        return action

    def action_apply(self):
        self.ensure_one()
        lots = list(filter(lambda serial_number: len(serial_number.strip()) > 0, self.serial_numbers.split('\n'))) if self.serial_numbers else []
        existing_lots = self.env['stock.lot'].search([
            '|', ('company_id', '=', False), ('company_id', '=', self.production_id.company_id.id),
            ('product_id', '=', self.production_id.product_id.id),
            ('name', 'in', lots),
        ])
        existing_lot_names = existing_lots.mapped('name')
        new_lots = []
        for lot_name in lots:
            if lot_name in existing_lot_names:
                continue

            if self.lot_name == self.production_id.product_id.serial_prefix_format + self.production_id.product_id.next_serial:
                if self.production_id.product_id.lot_sequence_id:
                    lot_name = self.production_id.product_id.lot_sequence_id.next_by_id()
                else:
                    lot_name = self.env['ir.sequence'].next_by_code('stock.lot.serial')
            new_lots.append({
                'name': lot_name,
                'product_id': self.production_id.product_id.id
            })
        self.production_id.lot_producing_ids = existing_lots + self.env['stock.lot'].create(new_lots)
        if self.production_id.qty_producing != len(self.production_id.lot_producing_ids):
            self.production_id.qty_producing = len(self.production_id.lot_producing_ids)
        (self.workorder_id or self.production_id).set_qty_producing()
