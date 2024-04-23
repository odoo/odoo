# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import _, api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.misc import clean_context


class PickingType(models.Model):
    _inherit = 'stock.picking.type'

    code = fields.Selection(selection_add=[
        ('repair_operation', 'Repair')
    ], ondelete={'repair_operation': 'cascade'})

    count_repair_confirmed = fields.Integer(
        string="Number of Repair Orders Confirmed", compute='_compute_count_repair')
    count_repair_under_repair = fields.Integer(
        string="Number of Repair Orders Under Repair", compute='_compute_count_repair')
    count_repair_ready = fields.Integer(
        string="Number of Repair Orders to Process", compute='_compute_count_repair')

    default_remove_location_dest_id = fields.Many2one(
        'stock.location', 'Default Remove Destination Location', compute='_compute_default_remove_location_dest_id',
        check_company=True, store=True, readonly=False, precompute=True,
        help="This is the default remove destination location when you create a repair order with this operation type.")

    default_recycle_location_dest_id = fields.Many2one(
        'stock.location', 'Default Recycle Destination Location', compute='_compute_default_recycle_location_dest_id',
        check_company=True, store=True, readonly=False, precompute=True,
        help="This is the default recycle destination location when you create a repair order with this operation type.")

    is_repairable = fields.Boolean(
        'Create Repair Orders from Returns',
        compute='_compute_is_repairable', store=True, readonly=False, default=False,
        help="If ticked, you will be able to directly create repair orders from a return.")
    return_type_of_ids = fields.One2many('stock.picking.type', 'return_picking_type_id')

    def _compute_count_repair(self):
        repair_picking_types = self.filtered(lambda picking: picking.code == 'repair_operation')

        # By default, set count_repair_xxx to False
        self.count_repair_ready = False
        self.count_repair_confirmed = False
        self.count_repair_under_repair = False

        # shortcut
        if not repair_picking_types:
            return

        picking_types = self.env['repair.order']._read_group(
            [
                ('picking_type_id', 'in', repair_picking_types.ids),
                ('state', 'in', ('confirmed', 'under_repair')),
            ],
            groupby=['picking_type_id', 'is_parts_available', 'state'],
            aggregates=['id:count']
        )

        counts = {}
        for pt in picking_types:
            pt_count = counts.setdefault(pt[0].id, {})
            if pt[1]:
                pt_count.setdefault('ready', 0)
                pt_count['ready'] += pt[3]
            pt_count.setdefault(pt[2], 0)
            pt_count[pt[2]] += pt[3]

        for pt in repair_picking_types:
            if pt.id not in counts:
                continue
            pt.count_repair_ready = counts[pt.id].get('ready')
            pt.count_repair_confirmed = counts[pt.id].get('confirmed')
            pt.count_repair_under_repair = counts[pt.id].get('under_repair')

    @api.depends('return_type_of_ids', 'code')
    def _compute_is_repairable(self):
        for picking_type in self:
            if not picking_type.return_type_of_ids:
                picking_type.is_repairable = False  # Reset the user choice as it's no more available.

    def _compute_default_location_src_id(self):
        remaining_picking_type = self.env['stock.picking.type']
        for picking_type in self:
            if picking_type.code != 'repair_operation':
                remaining_picking_type |= picking_type
                continue
            stock_location = picking_type.warehouse_id.lot_stock_id
            picking_type.default_location_src_id = stock_location.id
        super(PickingType, remaining_picking_type)._compute_default_location_src_id()

    def _compute_default_location_dest_id(self):
        repair_picking_type = self.filtered(lambda pt: pt.code == 'repair_operation')
        prod_locations = self.env['stock.location']._read_group(
            [('usage', '=', 'production'), ('company_id', 'in', repair_picking_type.company_id.ids)],
            ['company_id'],
            ['id:min'],
        )
        prod_locations = {l[0].id: l[1] for l in prod_locations}
        for picking_type in repair_picking_type:
            picking_type.default_location_dest_id = prod_locations.get(picking_type.company_id.id)
        super(PickingType, (self - repair_picking_type))._compute_default_location_dest_id()

    @api.depends('code')
    def _compute_default_remove_location_dest_id(self):
        repair_picking_type = self.filtered(lambda pt: pt.code == 'repair_operation')
        company_ids = repair_picking_type.company_id.ids
        company_ids.append(False)
        scrap_locations = self.env['stock.location']._read_group(
            [('scrap_location', '=', True), ('company_id', 'in', company_ids)],
            ['company_id'],
            ['id:min'],
        )
        scrap_locations = {l[0].id: l[1] for l in scrap_locations}
        for picking_type in repair_picking_type:
            picking_type.default_remove_location_dest_id = scrap_locations.get(picking_type.company_id.id)

    @api.depends('code')
    def _compute_default_recycle_location_dest_id(self):
        for picking_type in self:
            if picking_type.code == 'repair_operation':
                stock_location = picking_type.warehouse_id.lot_stock_id
                picking_type.default_recycle_location_dest_id = stock_location.id

    def get_repair_stock_picking_action_picking_type(self):
        action = self.env["ir.actions.actions"]._for_xml_id('repair.action_picking_repair')
        if self:
            action['display_name'] = self.display_name
        return action


class Picking(models.Model):
    _inherit = 'stock.picking'

    is_repairable = fields.Boolean(compute='_compute_is_repairable')
    repair_ids = fields.One2many('repair.order', 'picking_id')
    nbr_repairs = fields.Integer('Number of repairs linked to this picking', compute='_compute_nbr_repairs')

    @api.depends('picking_type_id.is_repairable', 'return_id')
    def _compute_is_repairable(self):
        for picking in self:
            picking.is_repairable = picking.picking_type_id.is_repairable and picking.return_id

    @api.depends('repair_ids')
    def _compute_nbr_repairs(self):
        for picking in self:
            picking.nbr_repairs = len(picking.repair_ids)

    def action_repair_return(self):
        self.ensure_one()
        ctx = clean_context(self.env.context.copy())
        ctx.update({
            'default_location_id': self.location_dest_id.id,
            'default_picking_id': self.id,
            'default_picking_type_id': self.picking_type_id.warehouse_id.repair_type_id.id,
            'default_partner_id': self.partner_id and self.partner_id.id or False,
        })
        return {
            'name': _('Create Repair'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'repair.order',
            'view_id': self.env.ref('repair.view_repair_order_form').id,
            'context': ctx,
        }

    def action_view_repairs(self):
        if self.repair_ids:
            action = {
                'res_model': 'repair.order',
                'type': 'ir.actions.act_window',
            }
            if len(self.repair_ids) == 1:
                action.update({
                    'view_mode': 'form',
                    'res_id': self.repair_ids[0].id,
                })
            else:
                action.update({
                    'name': _('Repair Orders'),
                    'view_mode': 'tree,form',
                    'domain': [('id', 'in', self.repair_ids.ids)],
                })
            return action
