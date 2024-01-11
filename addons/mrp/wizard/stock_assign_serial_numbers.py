# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from collections import Counter

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from collections import defaultdict


class StockAssignSerialNumbers(models.TransientModel):
    _inherit = 'stock.assign.serial'

    production_id = fields.Many2one('mrp.production', 'Production')
    expected_qty = fields.Float('Expected Quantity', digits='Product Unit of Measure')
    serial_numbers = fields.Text('Produced Serial Numbers')
    produced_qty = fields.Float('Produced Quantity', digits='Product Unit of Measure')
    show_apply = fields.Boolean() # Technical field to show the Apply button
    show_backorders = fields.Boolean() # Technical field to show the Create Backorder and No Backorder buttons
    multiple_lot_components_names = fields.Text() # Names of components with multiple lots, used to show warning
    mark_as_done = fields.Boolean("Valide all the productions after the split")
    lot_numbers = fields.Text("components enter by user")
    list_of_component = fields.Html(string="list of component")

    def generate_serial_numbers_production(self):
        if self.next_serial_number and self.next_serial_count:
            self.lot_numbers = "\n".join(lot['lot_name'] for lot in self.env['stock.lot'].generate_lot_names(self.next_serial_number, self.next_serial_count))
            self._onchange_lot_numbers()
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.act_assign_serial_numbers_production")
        action['res_id'] = self.id
        return action

    def _get_serial_numbers(self):
        if self.lot_numbers:
            spilt_per_bo = self.lot_numbers.strip().split('\n')
            expected_length = 1 + (sum(self.production_id.move_raw_ids.filtered(lambda m: m.product_id.tracking == 'serial').mapped('product_uom_qty')) / self.production_id.product_qty) + len(self.production_id.move_raw_ids.filtered(lambda m: m.product_id.tracking == 'lot'))
            if any(len(lot_and_qty.split(',')) != expected_length for lot_and_qty in spilt_per_bo) and any(len(lot_and_qty.split(',')) != 1 for lot_and_qty in spilt_per_bo):
                raise UserError("You have entered a some extra or some less component detail!!")

            sn_for_backorders = [count.split(',')[0] for count in spilt_per_bo]
            return sn_for_backorders
        return []

    @api.onchange('lot_numbers')
    def _onchange_lot_numbers(self):
        self.show_apply = False
        lot_numbers = self._get_serial_numbers()
        duplicate_lot_numbers = [serial_number for serial_number, counter in Counter(lot_numbers).items() if counter > 1]
        if duplicate_lot_numbers:
            self.lot_numbers = ""
            self.produced_qty = 0
            raise UserError(_('Duplicate Serial Numbers (%s)') % ','.join(duplicate_lot_numbers))
        existing_lot_numbers = self.env['stock.lot'].search([
            ('company_id', '=', self.production_id.company_id.id),
            ('product_id', '=', self.production_id.product_id.id),
            ('name', 'in', lot_numbers),
        ])
        if existing_lot_numbers:
            self.lot_numbers = ""
            self.produced_qty = 0
            raise UserError(_('Existing Serial Numbers (%s)') % ','.join(existing_lot_numbers.mapped('display_name')))
        if len(lot_numbers) > self.expected_qty:
            self.lot_numbers = ""
            self.produced_qty = 0
            raise UserError(_('There are more Serial Numbers than the Quantity to Produce'))
        self.produced_qty = len(lot_numbers)
        self.show_apply = bool(self.lot_numbers)

    def _assign_serial_numbers(self, cancel_remaining_quantity=False):
        lot_numbers = self._get_serial_numbers()
        if self._context.get('make_mo_done'):
            self.mark_as_done = True

        split_component = self.lot_numbers and self.lot_numbers.split('\n')
        total_lot_count = len(split_component[0].split(',')) if split_component else 0
        components_lots = []
        set_consumed_qty = True
        if total_lot_count > 1:
            components_lots = [sc.split(',')[1:] for sc in split_component]
            set_consumed_qty = False
            self.production_id.do_unreserve()

        productions = self.production_id.with_context(sml_create=True)._split_productions(
            {self.production_id: [1] * len(lot_numbers)}, cancel_remaining_quantity, set_consumed_qty=set_consumed_qty)
        if components_lots and not all(null_list == [''] for null_list in components_lots):
            # user enter components formate : lot_numbers
            #  -----------------------
            # |mo1,sn01,sn02,l1;1|l2:1|
            # |mo2,sn03,sn04,l2;2|    |
            #  -----------------------
            # prepare_component = defaultdict(<class 'list'>, {63: [['sn01', 'sn02'], ['sn03', 'sn04']], 64: [{'l1': 1,'l2': 1}, {'l2': 2}], 63: [['sn001'], ['sn002']]})

            prepare_component = defaultdict(list)
            for production, components in zip(productions, components_lots):
                temp_ind = 0
                for move in production.move_raw_ids.filtered(lambda mv: mv.product_id.tracking != 'none'):
                    comp_per_raw = []
                    if move.product_id.tracking == 'serial':
                        for _comp_qty in range(int(move.product_uom_qty)):
                            comp_per_raw.append(components[temp_ind])
                            temp_ind += 1
                    else:
                        pairs_of_lot = re.findall(r'(\w+);(\d+)', components[temp_ind])
                        if pairs_of_lot:
                            comp_per_raw = {lot_name: int(qty) for lot_name, qty in pairs_of_lot}
                        else:
                            comp_per_raw = {components[temp_ind]: int(move.product_uom_qty)}
                        temp_ind += 1
                    prepare_component[move.product_id.id].append(comp_per_raw)

            comp = 0
            preapre_comp_dict = []
            backorders_len = min(len(lot_numbers), len(productions))
            for mo_len in range(backorders_len):
                for move in productions[mo_len].move_raw_ids.filtered(lambda mv: mv.product_id.tracking != 'none'):
                    if move.product_id.tracking == 'serial':
                        move_line_count = min(len(prepare_component.get(move.product_id.id)[comp]), int(move.product_uom_qty))
                        for i in range(move_line_count):
                            sml = move._prepare_move_line_vals()
                            if prepare_component.get(move.product_id.id)[comp][i]:
                                sml['lot_id'] = self.env['stock.lot'].search([('product_id', '=', move.product_id.id), ('name', '=', prepare_component.get(move.product_id.id)[comp][i])]).id
                                sml['quantity'] = 1
                                if sml['lot_id']:
                                    preapre_comp_dict.append(sml)
                                else:
                                    prepare_stock_lot_values = {
                                        'product_id': move.product_id.id,
                                        'company_id': move.company_id.id,
                                        'name': prepare_component.get(move.product_id.id)[comp][i],
                                    }
                                    sml['lot_id'] = self.env['stock.lot'].create(prepare_stock_lot_values).id
                                    sml['quantity'] = 1
                                    preapre_comp_dict.append(sml)

                    if move.product_id.tracking == 'lot':
                        move_line_count = min(len(prepare_component.get(move.product_id.id)[comp]), int(move.product_uom_qty))
                        for i in range(move_line_count):
                            sml = move._prepare_move_line_vals()
                            if prepare_component.get(move.product_id.id)[comp]:
                                for index, item in enumerate(prepare_component.get(move.product_id.id)[comp].items()):
                                    if i == index:
                                        sml['lot_id'] = self.env['stock.lot'].search([('product_id', '=', move.product_id.id), ('name', '=', item[0])]).id
                                        sml['quantity'] = item[1]
                                        if sml['lot_id']:
                                            preapre_comp_dict.append(sml)
                                        else:
                                            prepare_stock_lot_values = {
                                                'product_id': move.product_id.id,
                                                'company_id': move.company_id.id,
                                                'name': item[0],
                                            }
                                            sml['lot_id'] = self.env['stock.lot'].create(prepare_stock_lot_values).id
                                            sml['quantity'] = item[1]
                                            preapre_comp_dict.append(sml)
                comp = comp + 1
            self.env['stock.move.line'].create(preapre_comp_dict)
        productions.action_assign()

        if not self._context.get('make_mo_confirmed'):
            productions.move_raw_ids.move_line_ids.filtered(lambda l: l.quantity and not l.picked).write({'picked': True})

        production_lots_vals = []
        for serial_name in lot_numbers:
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
            productions[-1].move_raw_ids.move_line_ids.write({'quantity': 0})
            productions[-1].state = "confirmed"

        if self.mark_as_done and len(lot_numbers) >= len(productions):
            for production in productions:
                production.with_context(skip_consumption=True).button_mark_done()

    def apply(self):
        self._assign_serial_numbers()

    def create_backorder(self):
        self._assign_serial_numbers(False)

    def no_backorder(self):
        self._assign_serial_numbers(True)
