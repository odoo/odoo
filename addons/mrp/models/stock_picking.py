# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    code = fields.Selection(selection_add=[
        ('mrp_operation', 'Manufacturing')
    ], ondelete={'mrp_operation': 'cascade'})
    count_mo_todo = fields.Integer(string="Number of Manufacturing Orders to Process",
        compute='_get_mo_count')
    count_mo_waiting = fields.Integer(string="Number of Manufacturing Orders Waiting",
        compute='_get_mo_count')
    count_mo_late = fields.Integer(string="Number of Manufacturing Orders Late",
        compute='_get_mo_count')
    use_create_components_lots = fields.Boolean(
        string="Create New Lots/Serial Numbers for Components",
        help="Allow to create new lot/serial numbers for the components",
        default=False,
    )
    use_auto_consume_components_lots = fields.Boolean(
        string="Consume Reserved Lots/Serial Numbers automatically",
        help="Allow automatic consumption of tracked components that are reserved",
    )

    def _get_mo_count(self):
        mrp_picking_types = self.filtered(lambda picking: picking.code == 'mrp_operation')
        if not mrp_picking_types:
            self.count_mo_waiting = False
            self.count_mo_todo = False
            self.count_mo_late = False
            return
        domains = {
            'count_mo_waiting': [('reservation_state', '=', 'waiting')],
            'count_mo_todo': ['|', ('state', 'in', ('confirmed', 'draft', 'progress', 'to_close')), ('is_planned', '=', True)],
            'count_mo_late': [('date_planned_start', '<', fields.Date.today()), ('state', '=', 'confirmed')],
        }
        for field in domains:
            data = self.env['mrp.production']._read_group(domains[field] +
                [('state', 'not in', ('done', 'cancel')), ('picking_type_id', 'in', self.ids)],
                ['picking_type_id'], ['picking_type_id'])
            count = {x['picking_type_id'] and x['picking_type_id'][0]: x['picking_type_id_count'] for x in data}
            for record in mrp_picking_types:
                record[field] = count.get(record.id, 0)
        remaining = (self - mrp_picking_types)
        if remaining:
            remaining.count_mo_waiting = False
            remaining.count_mo_todo = False
            remaining.count_mo_late = False

    def get_mrp_stock_picking_action_picking_type(self):
        action = self.env["ir.actions.actions"]._for_xml_id('mrp.mrp_production_action_picking_deshboard')
        if self:
            action['display_name'] = self.display_name
        return action

    @api.onchange('code')
    def _onchange_code(self):
        if self.code == 'mrp_operation':
            self.use_create_lots = True
            self.use_existing_lots = True

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    has_kits = fields.Boolean(compute='_compute_has_kits')

    @api.depends('move_ids')
    def _compute_has_kits(self):
        for picking in self:
            picking.has_kits = any(picking.move_ids.mapped('bom_line_id'))

    def _less_quantities_than_expected_add_documents(self, moves, documents):
        documents = super(StockPicking, self)._less_quantities_than_expected_add_documents(moves, documents)

        def _keys_in_groupby(move):
            """ group by picking and the responsible for the product the
            move.
            """
            return (move.raw_material_production_id, move.product_id.responsible_id)

        production_documents = self._log_activity_get_documents(moves, 'move_dest_ids', 'DOWN', _keys_in_groupby)
        return {**documents, **production_documents}
