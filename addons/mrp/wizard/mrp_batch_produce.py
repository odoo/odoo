# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from collections import defaultdict, deque

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MrpBatchProduct(models.TransientModel):
    _name = 'mrp.batch.produce'
    _description = 'Produce a batch of production order'

    production_id = fields.Many2one('mrp.production', 'Production')

    production_text_help = fields.Text('Explanation for batch production', compute='_compute_production_text_help')
    production_text = fields.Text('Batch Production')

    lot_name = fields.Char('First Lot/SN', compute="_compute_lot_name", store=True, readonly=False)
    lot_qty = fields.Integer('Number of SN', compute="_compute_lot_qty", store=True, readonly=False)

    component_separator = fields.Char('Component separator', default=',', required=True)
    lots_separator = fields.Char('Lot separator', default='|', required=True)
    lots_quantity_separator = fields.Char('Lot quantity separator', default=';', required=True)

    @api.depends('production_id')
    def _compute_lot_name(self):
        for wizard in self:
            if wizard.lot_name:
                continue
            wizard.lot_name = self.production_id.lot_producing_id.name
            if not wizard.lot_name:
                wizard.lot_name = self.env['stock.lot']._get_next_serial(self.production_id.company_id, self.production_id.product_id)

    @api.depends('production_id')
    def _compute_lot_qty(self):
        for wizard in self:
            wizard.lot_qty = wizard.production_id.product_qty

    @api.depends('production_id', 'component_separator')
    def _compute_production_text_help(self):
        basic_text = _("Write one line per finished product to produce, with serial numbers as follows:\n")
        for wizard in self:
            finished_product = wizard.production_id.product_id.display_name
            text = basic_text + finished_product
            for move_raw in wizard.production_id.move_raw_ids:
                if move_raw.product_id.tracking == "none":
                    continue
                text += wizard.component_separator + move_raw.product_id.display_name
            wizard.production_text_help = text

    def action_prepare(self):
        return self._production_text_to_object(mark_done=False)

    def action_done(self):
        return self._production_text_to_object(mark_done=True)

    def action_generate_production_text(self):
        self.ensure_one()
        if not self.lot_name:
            raise UserError(_('Please specify the first serial number you would like to use.'))
        lots_name = self.env['stock.lot'].generate_lot_names(self.lot_name, self.lot_qty)
        self.production_text = '\n'.join([lot['lot_name'] for lot in lots_name])
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.action_mrp_batch_produce")
        action['res_id'] = self.id
        return action

    def _production_text_to_object(self, mark_done=False):
        self.ensure_one()
        if not self.production_text:
            raise UserError(_('Please specify the serial number you would like to use.'))
        productions_amount = []
        productions_lot_list = []
        components_list = []
        for production_line in deque(self.production_text.split("\n")):
            production_line = production_line.strip()
            if not production_line:
                continue
            components_line = deque(production_line.split(self.component_separator))
            finished_line = components_line.popleft()
            finished_move = self.production_id.move_finished_ids.filtered(lambda m: m.product_id == self.production_id.product_id)
            finished_lot, finished_qty = self._get_lot_and_qty(finished_move, finished_line)
            productions_amount.append(finished_qty)
            productions_lot_list.append(finished_lot)
            components_list.append(components_line)

        productions = self.production_id._split_productions({self.production_id: productions_amount})
        lots = self.env['stock.lot'].search(
            domain=[
                ('company_id', 'in', [self.production_id.product_id.company_id.id, False]),
                ('name', 'in', productions_lot_list),
                ('product_id', '=', self.production_id.product_id.id)
            ]
        )
        existing_lot_names = lots.mapped('name')
        raw_lots = []
        for lot_name in productions_lot_list:
            if lot_name in existing_lot_names:
                continue
            raw_lots.append({
                'name': lot_name,
                'product_id': productions.product_id.id
            })
        lots = lots + self.env['stock.lot'].create(raw_lots)

        productions_to_set = set()
        for production, finished_lot in zip(productions, lots):
            production.lot_producing_id = finished_lot
            self._process_components(production, components_list.pop(0))
            productions_to_set.add(production.id)

        productions = self.env['mrp.production'].browse(productions_to_set)
        for production in productions:
            production.qty_producing = production.product_uom_qty
            production.set_qty_producing()
            production.move_raw_ids.picked = True

        if mark_done:
            return productions.with_context(from_wizard=True).button_mark_done()
        return

    def _process_components(self, production, components_line):
        lot_names = []
        mls_to_unlink = set()
        moves_vals = defaultdict(list)
        for move_raw in production.move_raw_ids:
            if move_raw.product_id.tracking == "none" or not components_line:
                continue
            component_line = components_line.popleft().strip()
            mls_lines = component_line.split(self.lots_separator)
            for ml_line in mls_lines:
                lot_name, qty = self._get_lot_and_qty(move_raw, ml_line)
                moves_vals[move_raw].append((qty, lot_name))
                lot_names.append(lot_name)

        lots = {(l.name, l.product_id): l for  l in self.env['stock.lot'].search([('name', 'in', lot_names)])}
        mls_vals = []
        for move, mls in moves_vals.items():
            if mls:
                mls_to_unlink |= set(move.move_line_ids.ids)
            for qty, lot_name in mls:
                ml_vals = self._prepapre_move_line_vals(move, qty, lot_name, lots)
                mls_vals.append(ml_vals)
        self.env['stock.move.line'].browse(mls_to_unlink).unlink()
        self.env['stock.move.line'].create(mls_vals)

    def _prepapre_move_line_vals(self, move, qty, lot_name, lots):
        ml_vals = move._prepare_move_line_vals(qty)
        lot = lots.get((lot_name, move.product_id))
        if not lot:
            if not move.picking_type_id.use_create_components_lots:
                raise UserError(_('Lot %s does not exist.', lot_name))
            lot = self.env['stock.lot'].create({
                'name': lot_name,
                'product_id': move.product_id.id
            })
            lots[(lot_name, move.product_id)] = lot
        ml_vals['lot_id'] = lots[(lot_name, move.product_id)].id
        ml_vals['picked'] = True
        return ml_vals

    def _get_lot_and_qty(self, move, text):
        if self.lots_quantity_separator in text:
            lot_name, qty = re.match(r'(.+)%s(.+)' % (self.lots_quantity_separator), text).groups()
            return lot_name, float(qty)
        elif move.product_id.tracking == "none":
            return False, float(text)
        elif move.product_id.tracking == "serial":
            return text, 1
        else:
            return text, move.product_uom_qty
