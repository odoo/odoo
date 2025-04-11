# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import fields, models, api


class StockQuantRelocate(models.TransientModel):
    _name = 'stock.quant.relocate'
    _description = 'Stock Quantity Relocation'

    quant_ids = fields.Many2many('stock.quant')
    company_id = fields.Many2one(related="quant_ids.company_id")
    dest_location_id = fields.Many2one('stock.location', domain="[('usage', '=', 'internal'), ('company_id', '=', company_id)]")
    dest_package_id_domain = fields.Char(compute="_compute_dest_package_id_domain")
    dest_package_id = fields.Many2one('stock.quant.package', domain="dest_package_id_domain", compute="_compute_dest_package_id", store=True)
    message = fields.Text('Note')
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

        if not self.dest_location_id and not self.dest_package_id:
            return

        location_quants_map = {}
        for quant in self.quant_ids:
            location_quants_map.setdefault(quant.location_id, []).append(quant)

        pickings = self.env['stock.picking']
        all_moves = self.env['stock.move']

        for location, quants in location_quants_map.items():
            picking_vals = {
                'picking_type_id': self.env.ref('stock.picking_type_internal').id,
                'location_id': location.id,
                'location_dest_id': self.dest_location_id.id ,
                'move_type': 'direct',
                'state': 'draft',
                'note': self.message,
                'origin': 'Relocation Wizard',
            }
            picking = self.env['stock.picking'].create(picking_vals)

            move_records = self.env['stock.move']
            for quant in quants:
                move = self.env['stock.move'].create({
                    'picking_id': picking.id,
                    'product_id': quant.product_id.id,
                    'name': quant.product_id.name,
                    'product_uom_qty': quant.quantity,
                    'product_uom': quant.product_id.uom_id.id,
                    'location_id': quant.location_id.id,
                    'location_dest_id': self.dest_location_id.id,
                    'state': 'draft'
                })
                move_records |= move
            all_moves |= move_records

            picking.action_confirm()
            pickings |= picking

        for move in all_moves:
            if  move.exists() and move.move_line_ids:
                move.move_line_ids.write({'result_package_id': self.dest_package_id.id})

        if pickings:
            return self._get_internal_transfer_notification(pickings)

    def _get_internal_transfer_notification_links(self, pickings):
        links = []
        for picking in pickings:
            links.append({
                'label': picking.name,
                'url': f'/web#id={picking.id}&model=stock.picking&view_type=form'
            })

        return links if links else False

    def _get_internal_transfer_notification(self, pickings):
            links = self._get_internal_transfer_notification_links(pickings)
            if not links:
                return False

            message = '\n'.join(['%s'] * len(links))

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': ('Internal Transfers'),
                    'message': message,
                    'links': links,
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
