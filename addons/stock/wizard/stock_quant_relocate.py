# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import fields, models, api, Command
from odoo.exceptions import UserError
from odoo.tools import groupby


class StockQuantRelocate(models.TransientModel):
    _name = 'stock.quant.relocate'
    _description = 'Stock Quantity Relocation'

    quant_ids = fields.Many2many('stock.quant')
    company_id = fields.Many2one(related="quant_ids.company_id")
    dest_location_id = fields.Many2one('stock.location', domain="[('usage', '=', 'internal'), ('company_id', '=', company_id)]")
    dest_package_id_domain = fields.Char(compute="_compute_dest_package_id_domain")
    dest_package_id = fields.Many2one('stock.package', domain="dest_package_id_domain", compute="_compute_dest_package_id", store=True)
    message = fields.Text('Reason for relocation')
    is_partial_package = fields.Boolean(compute='_compute_is_partial_package')
    partial_package_names = fields.Char(compute="_compute_is_partial_package")
    is_multi_location = fields.Boolean(compute='_compute_is_multi_location')

    @api.depends('quant_ids')
    def _compute_is_partial_package(self):
        self.is_partial_package = False
        self.partial_package_names = ''
        for wizard in self:
            packages = wizard.quant_ids.package_id
            incomplete_packages = packages.filtered(lambda p: any(q not in wizard.quant_ids.ids for q in p.quant_ids.ids))
            if packages and incomplete_packages:
                wizard.is_partial_package = True
                wizard.partial_package_names = ', '.join(incomplete_packages.mapped('display_name'))

    @api.depends('dest_location_id', 'quant_ids')
    def _compute_is_multi_location(self):
        self.is_multi_location = False
        for wizard in self:
            if len(wizard.quant_ids.location_id) > 1 and not wizard.dest_location_id:
                wizard.is_multi_location = True

    @api.depends('dest_location_id', 'quant_ids')
    def _compute_dest_package_id_domain(self):
        for wizard in self:
            domain = ['|', ('company_id', '=', wizard.company_id.id), ('company_id', '=', False)]
            if wizard.dest_location_id:
                domain += ['|', ('location_id', '=', False), ('location_id', '=', wizard.dest_location_id.id)]
            elif len(wizard.quant_ids.location_id) == 1:
                domain += ['|', ('location_id', '=', False), ('location_id', '=', wizard.quant_ids.location_id.id)]
            wizard.dest_package_id_domain = domain

    @api.depends('dest_package_id_domain')
    def _compute_dest_package_id(self):
        for wizard in self:
            if wizard.dest_package_id and not wizard.dest_package_id.search_count([('id', '=', wizard.dest_package_id.id)] + literal_eval(wizard.dest_package_id_domain), limit=1):
                wizard.dest_package_id = False

    def action_relocate_quants(self):
        self.ensure_one()
        lot_ids = self.quant_ids.lot_id
        product_ids = self.quant_ids.product_id

        if not self.dest_location_id and not self.dest_package_id:
            return
        self.quant_ids.action_clear_inventory_quantity()

        if self.is_partial_package and not self.dest_package_id:
            quants_to_unpack = self.quant_ids.filtered(lambda q: not all(sub_q in self.quant_ids.ids for sub_q in q.package_id.quant_ids.ids))
            quants_to_unpack.move_quants(location_dest_id=self.dest_location_id, message=self.message, unpack=True)
            self.quant_ids -= quants_to_unpack
        self.quant_ids.move_quants(location_dest_id=self.dest_location_id, package_dest_id=self.dest_package_id, message=self.message)

        if self.env.context.get('default_lot_id', False) and len(lot_ids) == 1:
            return lot_ids.action_lot_open_quants()
        elif self.env.context.get('single_product', False) and len(product_ids) == 1:
            return product_ids.action_open_quants()
        return self.quant_ids.with_context(always_show_loc=1).action_view_quants()

    def action_request_quants_relocation(self):
        self.ensure_one()
        pickings = []
        for warehouse in self.quant_ids.warehouse_id:
            picking_type = (
                warehouse.int_type_id
                if warehouse.int_type_id.active
                else self.env['stock.picking.type'].search(
                    [
                        ('code', '=', 'internal'),
                        ('warehouse_id', '=', warehouse.id),
                    ],
                    limit=1,
                )
            )
            if not picking_type:
                raise UserError(self.env._('You need to create an internal operation type for your warehouse.'))

            if len(self.quant_ids.location_id) > 1:
                grouped_quants = groupby(self.quant_ids.filtered(lambda q: q.warehouse_id == warehouse),
                                         key=lambda q: self._get_parent_location(q.location_id, warehouse.view_location_id))
                for parent, quants in grouped_quants:
                    if parent:
                        location_id = parent.id if len(quants) > 1 else quants[0].location_id.id
                        pickings.append(self._create_moves_and_picking(quants, location_id, picking_type))
            else:
                pickings.append(self._create_moves_and_picking(self.quant_ids, self.quant_ids.location_id.id, picking_type))

        links, placeholders = self._generate_links_and_placeholders(pickings)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': self.env._('The transfer request has been created') if pickings
                    else self.env._('Only products assigned to a warehouse can be relocated'),
                'message': placeholders,
                'links': links,
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def _get_parent_location(self, location_id, view_location_id):
        if view_location_id == location_id.location_id or location_id.location_id.usage == 'view':
            return location_id
        return self._get_parent_location(location_id.location_id, view_location_id)

    def _create_moves_and_picking(self, quants, source_location, picking_type):
        moves = []
        grouped_quants = groupby(quants, key=lambda q: q.product_id)
        for product, quants in grouped_quants:
            move_vals = {
                'product_id': product.id,
                'product_uom_qty': quants[0].quantity,
                'uom_id': quants[0].uom_id.id,
                'location_id': quants[0].location_id.id,
                'location_dest_id': self.dest_location_id.id or source_location,
            }
            if len(quants) > 1:
                move_lines = []
                quantity = 0
                for quant in quants:
                    move_lines.append(
                            Command.create({
                            'product_id': product.id,
                            'quantity': quant.quantity,
                            'uom_id': quant.uom_id.id,
                            'location_id':  quant.location_id.id,
                            'location_dest_id': self.dest_location_id.id or source_location,
                            'company_id': quant.company_id.id,
                        })
                    )
                    quantity += quant.quantity
                move_vals['move_line_ids'] = move_lines
                move_vals['product_uom_qty'] = quantity
                move_vals['location_id'] = source_location
            moves.append(Command.create(move_vals))

        picking = self.env['stock.picking'].create({
                    'picking_type_id': picking_type.id,
                    'origin': f'Relocation Request{f': {self.message}' if self.message else ''}',
                    'location_id': source_location,
                    'location_dest_id': self.dest_location_id.id or source_location,
                    'move_ids': moves,
                })
        picking.action_confirm()
        # Link move_line_ids to the picking
        picking.move_ids.move_line_ids.picking_id = picking
        picking.move_line_ids.result_package_id = self.dest_package_id
        return picking

    def _generate_links_and_placeholders(self, pickings):
        links = []
        placeholders = "\n"
        for picking in pickings:
            links.append({
                'label': picking.name,
                'url': f'/odoo/action-stock.stock_picking_action_picking_type/{picking.id}'
            })
            placeholders += '%s '

        return links, placeholders
