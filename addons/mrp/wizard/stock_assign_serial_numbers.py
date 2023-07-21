# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from collections import Counter

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from collections import defaultdict


class StockAssignSerialNumbers(models.TransientModel):
    _inherit = 'stock.assign.serial'

    def _default_placeholder(self):
        production_id = self.env['mrp.production'].browse([self._context.get('default_production_id')])
        if production_id.product_id.tracking == 'serial':
            placeholder_value = "SN123,LOT001;3|LOT002;3,SN0120\nSN456,LOT002;3|LOT002;3,SN0121"
        elif production_id.product_id.tracking == 'lot':
            placeholder_value = "LOT123,5,LOT001;3|LOT002;3,SN0120\nLOT124,5,LOT002;3|LOT002;3,SN0121"
        else:
            placeholder_value = ""
        return placeholder_value

    production_id = fields.Many2one('mrp.production', 'Production')
    expected_qty = fields.Float('Expected Quantity', digits='Product Unit of Measure')
    serial_numbers = fields.Text('Produced Serial Numbers')
    produced_qty = fields.Float('Produced Quantity', digits='Product Unit of Measure')
    show_apply = fields.Boolean() # Technical field to show the Apply button
    show_backorders = fields.Boolean() # Technical field to show the Create Backorder and No Backorder buttons
    multiple_lot_components_names = fields.Text() # Names of components with multiple lots, used to show warning
    mark_as_done = fields.Boolean("Valide all the productions after the split")
    lot_numbers = fields.Text("components enter by user", default=_default_placeholder)
    list_of_component = fields.Text(string="list of component")

    def action_open_generate_serial_production(self):
        """ Open the modal to generate stock move line with a serial pattern"""
        return {
            'name': _('Generate Serial Numbers'),
            'res_model': 'stock.generate.serial',
            'type': 'ir.actions.act_window',
            'views': [[False, "form"]],
            'view_id': self.env.ref('mrp.inherit_view_generate_serial').id,
            'target': 'new',
            'context': {
                'from_mass_production': True,
                'default_stock_assign_serial_id': self.id,
            },
        }

    def _get_serial_numbers(self):
        if self.lot_numbers: #Need to remove when mass produce btn remove
            spilt_per_bo = self.lot_numbers.split('\n')
            take_index = 2 if self.production_id.product_id.tracking == 'lot' and not self.production_id.move_raw_ids.filtered(lambda m: m.product_id.tracking == 'serial') else 1
            expected_length = take_index + (sum(self.production_id.move_raw_ids.filtered(lambda m: m.product_id.tracking == 'serial').mapped('product_uom_qty')) / self.production_id.product_qty) + len(self.production_id.move_raw_ids.filtered(lambda m: m.product_id.tracking == 'lot'))
            if self.production_id.product_id.tracking == 'lot' and self.production_id.move_raw_ids.filtered(lambda m: m.product_id.tracking == 'serial') and \
                    any(len(lot_and_qty.split(',')) != expected_length and len(lot_and_qty.split(',')) != 1
                        for lot_and_qty in spilt_per_bo):
                raise UserError("You can not enter Quantity when any components is track by sr!")

            if any(len(lot_and_qty.split(',')) != expected_length and len(lot_and_qty.split(',')) != 1 for lot_and_qty
                   in spilt_per_bo):
                raise UserError("You have entered a some extra or some less component detail!!")

            self.serial_numbers = "\n".join(
                lot_and_qty.replace(',', ';', 1).split(',')[0] if self.production_id.product_id.tracking == 'lot' and not self.production_id.move_raw_ids.filtered(lambda m: m.product_id.tracking == 'serial') else lot_and_qty.split(',')[0]
                for lot_and_qty in spilt_per_bo
            )

        if self.serial_numbers and self.production_id.product_id.tracking != 'lot':
            return list(filter(lambda serial_number: len(serial_number.strip()) > 0, self.serial_numbers.split('\n')))
        elif self.serial_numbers and self.production_id.product_id.tracking == 'lot':
            mo_name = self.serial_numbers.split('\n')
            sn_for_backorders = [count.split(';')[0] for count in mo_name]
            return sn_for_backorders
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
            raise UserError(_('Duplicate Serial Numbers (%s)', ','.join(duplicate_serial_numbers)))
        existing_serial_numbers = self.env['stock.lot'].search([
            ('company_id', '=', self.production_id.company_id.id),
            ('product_id', '=', self.production_id.product_id.id),
            ('name', 'in', serial_numbers),
        ])
        if existing_serial_numbers:
            self.serial_numbers = ""
            self.produced_qty = 0
            raise UserError(_('Existing Serial Numbers (%s)', ','.join(existing_serial_numbers.mapped('display_name'))))
        if len(serial_numbers) > self.expected_qty:
            self.serial_numbers = ""
            self.produced_qty = 0
            raise UserError(_('There are more Serial Numbers than the Quantity to Produce'))
        self.produced_qty = len(serial_numbers)
        self.show_apply = self.produced_qty == self.expected_qty
        self.show_backorders = 0 < self.produced_qty < self.expected_qty

    @api.onchange('lot_numbers')
    def _onchange_lot_numbers(self):
        self.show_apply = bool(self.lot_numbers)

    def _assign_serial_numbers(self, cancel_remaining_quantity=False):
        if self._context.get('make_mo_done'):
            self.mark_as_done = True
        serial_numbers = self._get_serial_numbers()
        split_component = self.lot_numbers and self.lot_numbers.split('\n')

        if split_component:
            self.production_id.do_unreserve()

        if self.production_id.product_id.tracking == 'lot' and not self.production_id.move_raw_ids.filtered(lambda m: m.product_id.tracking == 'serial'):
            mo_name = self.serial_numbers.split('\n')
            amounts = [int(count.split(';')[1]) for count in mo_name]
        else:
            amounts = [1] * len(serial_numbers)

        productions = self.production_id._split_productions(
            {self.production_id: amounts}, cancel_remaining_quantity, set_consumed_qty=False, sml_create=True)

        if split_component and ',' in split_component[0]:
            # user enter components formate : lot_numbers
            #  -----------------------
            # |mo1,sn01,sn02,l1;1|l2:1|
            # |mo2,sn03,sn04,l2;2|    |
            #  -----------------------
            # prepare_component = defaultdict(<class 'list'>, {63: [['sn01', 'sn02'], ['sn03', 'sn04']], 64: [{'l1': 1,'l2': 1}, {'l2': 2}], 63: [['sn001'], ['sn002']]})

            prepare_component = defaultdict(list)
            for production, components in zip(productions, split_component):
                temp_ind = 2 if self.production_id.product_id.tracking == 'lot' and not self.production_id.move_raw_ids.filtered(lambda m: m.product_id.tracking == 'serial') else 1
                for move in production.move_raw_ids.filtered(lambda mv: mv.product_id.tracking != 'none'):
                    comp_per_raw = []
                    if move.product_id.tracking == 'serial':
                        for _comp_qty in range(int(move.product_uom_qty)):
                            comp_per_raw.append(components.split(',')[temp_ind])
                            temp_ind += 1
                    else:
                        pairs_of_lot = re.findall(r'(\w+);(\d+)', components.split(',')[temp_ind])
                        if pairs_of_lot:
                            comp_per_raw = {lot_name: int(qty) for lot_name, qty in pairs_of_lot}
                        else:
                            comp_per_raw = {components.split(',')[temp_ind]: int(move.product_uom_qty)}
                        temp_ind += 1
                    prepare_component[move.product_id.id].append(comp_per_raw)

            comp = 0
            preapre_comp_dict = []
            backorders_len = min(len(serial_numbers), len(productions))
            for mo_len in range(backorders_len):
                for move in productions[mo_len].move_raw_ids.filtered(lambda mv: mv.product_id.tracking != 'none'):
                    if move.product_id.tracking == 'serial':
                        move_line_count = min(len(prepare_component.get(move.product_id.id)[comp]), int(move.product_uom_qty))
                        for i in range(move_line_count):
                            sml = move._prepare_move_line_vals()
                            if prepare_component.get(move.product_id.id)[comp][i]:
                                sml['lot_id'] = self.env['stock.lot'].search([('product_id', '=', move.product_id.id), ('name', '=', prepare_component.get(move.product_id.id)[comp][i])]).id
                                sml['reserved_uom_qty'] = 1
                                if not self._context.get('make_mo_confirmed') and len(serial_numbers) >= len(productions):
                                    sml['qty_done'] = 1
                                if sml['lot_id']:
                                    preapre_comp_dict.append(sml)
                            continue
                    if move.product_id.tracking == 'lot':
                        move_line_count = min(len(prepare_component.get(move.product_id.id)[comp]), int(move.product_uom_qty))
                        for i in range(move_line_count):
                            sml = move._prepare_move_line_vals()
                            if prepare_component.get(move.product_id.id)[comp]:
                                for index, item in enumerate(prepare_component.get(move.product_id.id)[comp].items()):
                                    if i == index:
                                        sml['lot_id'] = self.env['stock.lot'].search([('product_id', '=', move.product_id.id), ('name', '=', item[0])]).id
                                        sml['reserved_uom_qty'] = item[1]
                                        if not self._context.get('make_mo_confirmed') and len(serial_numbers) >= len(productions):
                                            sml['qty_done'] = item[1]
                                        if sml['lot_id']:
                                            preapre_comp_dict.append(sml)
                comp = comp + 1
            self.env['stock.move.line'].create(preapre_comp_dict)
        productions.action_assign()

        if not self._context.get('make_mo_confirmed'):
            for line in productions.move_raw_ids.move_line_ids.filtered(lambda l: not l.qty_done):
                line.qty_done = line.reserved_uom_qty

        production_lots_vals = []
        for serial_name in serial_numbers:
            production_lots_vals.append({
                'product_id': self.production_id.product_id.id,
                'company_id': self.production_id.company_id.id,
                'name': serial_name,
            })
        production_lots = self.env['stock.lot'].create(production_lots_vals)
        for production, production_lot in zip(productions, production_lots):
            production.lot_producing_id = production_lot.id
            for workorder in production.workorder_ids:
                workorder.qty_produced = workorder.qty_producing
            if not self._context.get('make_mo_confirmed'):
                production.qty_producing = production.product_qty

        if productions and len(production_lots) < len(productions):
            productions[-1].move_raw_ids.move_line_ids.write({'qty_done': 0})
            productions[-1].state = "confirmed"

        if self.mark_as_done and len(serial_numbers) >= len(productions):
            for production in productions:
                production.with_context(skip_consumption=True).button_mark_done()

    def apply(self):
        self._assign_serial_numbers()

    def create_backorder(self):
        self._assign_serial_numbers(False)

    def no_backorder(self):
        self._assign_serial_numbers(True)
