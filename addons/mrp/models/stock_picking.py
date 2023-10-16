# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    code = fields.Selection(selection_add=[
        ('mrp_operation', 'Manufacturing')
    ], ondelete={'mrp_operation': lambda recs: recs.write({'code': 'incoming', 'active': False})})
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

    auto_print_done_production_order = fields.Boolean(
        "Auto Print Done Production Order",
        help="If this checkbox is ticked, Odoo will automatically print the production order of a MO when it is done.")
    auto_print_done_mrp_product_labels = fields.Boolean(
        "Auto Print Produced Product Labels",
        help="If this checkbox is ticked, Odoo will automatically print the product labels of a MO when it is done.")
    mrp_product_label_to_print = fields.Selection(
        [('pdf', 'PDF'), ('zpl', 'ZPL')],
        "Product Label to Print", default='pdf')
    auto_print_done_mrp_lot = fields.Boolean(
        "Auto Print Produced Lot Label",
        help="If this checkbox is ticked, Odoo will automatically print the lot/SN label of a MO when it is done.")
    done_mrp_lot_label_to_print = fields.Selection(
        [('pdf', 'PDF'), ('zpl', 'ZPL')],
        "Lot/SN Label to Print", default='pdf')
    auto_print_mrp_reception_report = fields.Boolean(
        "Auto Print Allocation Report",
        help="If this checkbox is ticked, Odoo will automatically print the allocation report of a MO when it is done and has assigned moves.")
    auto_print_mrp_reception_report_labels = fields.Boolean(
        "Auto Print Allocation Report Labels",
        help="If this checkbox is ticked, Odoo will automatically print the allocation report labels of a MO when it is done.")
    auto_print_generated_mrp_lot = fields.Boolean(
        "Auto Print Generated Lot/SN Label",
        help='Automatically print the lot/SN label when the "Create a new serial/lot number" button is used.')
    generated_mrp_lot_label_to_print = fields.Selection(
        [('pdf', 'PDF'), ('zpl', 'ZPL')],
        "Generated Lot/SN Label to Print", default='pdf')

    @api.depends('code')
    def _compute_use_create_lots(self):
        super()._compute_use_create_lots()
        for picking_type in self:
            if picking_type.code == 'mrp_operation':
                picking_type.use_create_lots = True

    @api.depends('code')
    def _compute_use_existing_lots(self):
        super()._compute_use_existing_lots()
        for picking_type in self:
            if picking_type.code == 'mrp_operation':
                picking_type.use_existing_lots = True

    def _get_mo_count(self):
        mrp_picking_types = self.filtered(lambda picking: picking.code == 'mrp_operation')
        remaining = (self - mrp_picking_types)
        remaining.count_mo_waiting = remaining.count_mo_todo = remaining.count_mo_late = False
        domains = {
            'count_mo_waiting': [('reservation_state', '=', 'waiting')],
            'count_mo_todo': ['|', ('state', 'in', ('confirmed', 'draft', 'progress', 'to_close')), ('is_planned', '=', True)],
            'count_mo_late': [('date_start', '<', fields.Date.today()), ('state', '=', 'confirmed')],
        }
        for key, domain in domains.items():
            data = self.env['mrp.production']._read_group(domain +
                [('state', 'not in', ('done', 'cancel')), ('picking_type_id', 'in', mrp_picking_types.ids)],
                ['picking_type_id'], ['__count'])
            count = {picking_type.id: count for picking_type, count in data}
            for record in mrp_picking_types:
                record[key] = count.get(record.id, 0)

    def get_mrp_stock_picking_action_picking_type(self):
        action = self.env["ir.actions.actions"]._for_xml_id('mrp.mrp_production_action_picking_deshboard')
        if self:
            action['display_name'] = self.display_name
        return action

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    has_kits = fields.Boolean(compute='_compute_has_kits')

    @api.depends('move_ids')
    def _compute_has_kits(self):
        for picking in self:
            picking.has_kits = any(picking.move_ids.mapped('bom_line_id'))

    def action_detailed_operations(self):
        action = super().action_detailed_operations()
        action['context']['has_kits'] = self.has_kits
        return action

    def _less_quantities_than_expected_add_documents(self, moves, documents):
        documents = super(StockPicking, self)._less_quantities_than_expected_add_documents(moves, documents)

        def _keys_in_groupby(move):
            """ group by picking and the responsible for the product the
            move.
            """
            return (move.raw_material_production_id, move.product_id.responsible_id)

        production_documents = self._log_activity_get_documents(moves, 'move_dest_ids', 'DOWN', _keys_in_groupby)
        return {**documents, **production_documents}
