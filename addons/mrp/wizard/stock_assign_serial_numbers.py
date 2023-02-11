# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import Counter

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockAssignSerialNumbers(models.TransientModel):
    _inherit = 'stock.assign.serial'

    production_id = fields.Many2one('mrp.production', 'Production')
    expected_qty = fields.Float('Expected Quantity', digits='Product Unit of Measure')
    serial_numbers = fields.Text('Produced Serial Numbers')
    produced_qty = fields.Float('Produced Quantity', digits='Product Unit of Measure')
    show_apply = fields.Boolean(help="Technical field to show the Apply button")
    show_backorders = fields.Boolean(help="Technical field to show the Create Backorder and No Backorder buttons")

    def generate_serial_numbers_production(self):
        if self.next_serial_number and self.next_serial_count:
            generated_serial_numbers = "\n".join(self.env['stock.production.lot'].generate_lot_names(self.next_serial_number, self.next_serial_count))
            self.serial_numbers = "\n".join([self.serial_numbers, generated_serial_numbers]) if self.serial_numbers else generated_serial_numbers
            self._onchange_serial_numbers()
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.act_assign_serial_numbers_production")
        action['res_id'] = self.id
        return action

    def _get_serial_numbers(self):
        if self.serial_numbers:
            return list(filter(lambda serial_number: len(serial_number.strip()) > 0, self.serial_numbers.split('\n')))
        return []

    @api.onchange('serial_numbers')
    def _onchange_serial_numbers(self):
        self.show_apply = False
        self.show_backorders = False
        serial_numbers = self._get_serial_numbers()
        duplicate_serial_numbers = [serial_number for serial_number, counter in Counter(serial_numbers).items() if counter > 1]
        if duplicate_serial_numbers:
            self.serial_numbers = ""
            self.produced_qty = 0
            raise UserError(_('Duplicate Serial Numbers (%s)') % ','.join(duplicate_serial_numbers))
        existing_serial_numbers = self.env['stock.production.lot'].search([
            ('company_id', '=', self.production_id.company_id.id),
            ('product_id', '=', self.production_id.product_id.id),
            ('name', 'in', serial_numbers),
        ])
        if existing_serial_numbers:
            self.serial_numbers = ""
            self.produced_qty = 0
            raise UserError(_('Existing Serial Numbers (%s)') % ','.join(existing_serial_numbers.mapped('display_name')))
        if len(serial_numbers) > self.expected_qty:
            self.serial_numbers = ""
            self.produced_qty = 0
            raise UserError(_('There are more Serial Numbers than the Quantity to Produce'))
        self.produced_qty = len(serial_numbers)
        self.show_apply = self.produced_qty == self.expected_qty
        self.show_backorders = self.produced_qty > 0 and self.produced_qty < self.expected_qty

    def _assign_serial_numbers(self, cancel_remaining_quantity=False):
        serial_numbers = self._get_serial_numbers()
        productions = self.production_id._split_productions(
            {self.production_id: [1] * len(serial_numbers)}, cancel_remaining_quantity, set_consumed_qty=True)
        production_lots_vals = []
        for serial_name in serial_numbers:
            production_lots_vals.append({
                'product_id': self.production_id.product_id.id,
                'company_id': self.production_id.company_id.id,
                'name': serial_name,
            })
        production_lots = self.env['stock.production.lot'].create(production_lots_vals)
        for production, production_lot in zip(productions, production_lots):
            production.lot_producing_id = production_lot.id
            production.qty_producing = production.product_qty
            for workorder in production.workorder_ids:
                workorder.qty_produced = workorder.qty_producing

        if productions and len(production_lots) < len(productions):
            productions[-1].move_raw_ids.move_line_ids.write({'qty_done': 0})
            productions[-1].state = "confirmed"

    def apply(self):
        self._assign_serial_numbers()

    def create_backorder(self):
        self._assign_serial_numbers(False)

    def no_backorder(self):
        self._assign_serial_numbers(True)
