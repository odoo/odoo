# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import _, api, fields, models
from odoo.osv import expression


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
    count_mo_in_progress = fields.Integer(string="Number of Manufacturing Orders In Progress",
        compute='_get_mo_count')
    count_mo_to_close = fields.Integer(string="Number of Manufacturing Orders To Close",
        compute='_get_mo_count')
    use_create_components_lots = fields.Boolean(
        string="Create New Lots/Serial Numbers for Components",
        help="Allow to create new lot/serial numbers for the components",
        default=False,
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
        remaining.count_mo_in_progress = remaining.count_mo_to_close = False
        domains = {
            'count_mo_waiting': [('reservation_state', '=', 'waiting')],
            'count_mo_todo': [('state', '=', 'confirmed')],
            'count_mo_late': [('date_start', '<', fields.Date.today()), ('state', '=', 'confirmed')],
            'count_mo_in_progress': [('state', '=', 'progress')],
            'count_mo_to_close': [('state', '=', 'to_close')],
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

    def _get_aggregated_records_by_date(self):
        production_picking_types = self.filtered(lambda picking: picking.code == 'mrp_operation')
        other_picking_types = (self - production_picking_types)

        records = super(StockPickingType, other_picking_types)._get_aggregated_records_by_date()
        mrp_records = self.env['mrp.production']._read_group(
            [
                ('picking_type_id', 'in', production_picking_types.ids),
                ('state', '=', 'confirmed')
            ],
            ['picking_type_id'],
            ['date_start' + ':array_agg'],
        )
        # Make sure that all picking type IDs are represented, even if empty
        picking_type_id_to_dates = {i: [] for i in production_picking_types.ids}
        picking_type_id_to_dates.update({r[0].id: r[1] for r in mrp_records})
        mrp_records = [(i, d, self.env._('Confirmed')) for i, d in picking_type_id_to_dates.items()]
        return records + mrp_records


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    has_kits = fields.Boolean(compute='_compute_has_kits')
    production_count = fields.Integer(
        "Count of MO generated",
        compute='_compute_mrp_production_ids',
        groups='mrp.group_mrp_user')

    production_ids = fields.Many2many(
        'mrp.production',
        compute='_compute_mrp_production_ids',
        groups='mrp.group_mrp_user')

    @api.depends('move_ids')
    def _compute_has_kits(self):
        for picking in self:
            picking.has_kits = any(picking.move_ids.bom_line_id)

    @api.depends('group_id')
    def _compute_mrp_production_ids(self):
        for picking in self:
            production_ids = picking.group_id.mrp_production_ids | picking.move_ids.move_dest_ids.raw_material_production_id
            # Filter out unwanted MO types
            picking.production_ids = production_ids.filtered(lambda p: p.picking_type_id.active)
            picking.production_count = len(picking.production_ids)

    def action_detailed_operations(self):
        action = super().action_detailed_operations()
        action['context']['has_kits'] = self.has_kits
        return action

    def action_view_mrp_production(self):
        self.ensure_one()
        action = {
            'name': _("Manufacturing Orders"),
            'res_model': 'mrp.production',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.production_ids.ids)],
            'view_mode': 'list,form',
        }
        if self.production_count == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.production_ids.id,
            })
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

    @api.model
    def get_action_click_graph(self):
        picking_type_id = self.env.context["picking_type_id"]
        picking_type_code = self.env["stock.picking.type"].browse(picking_type_id).code

        if picking_type_code == "mrp_operation":
            action = self._get_action("mrp.action_picking_tree_mrp_operation_graph")
            action["domain"] = expression.AND([
                literal_eval(action["domain"] or '[]'), [('picking_type_id', '=', picking_type_id)]
            ])
            allowed_company_ids = self.env.context.get("allowed_company_ids", [])
            if allowed_company_ids:
                action["context"].update({
                    "default_company_id": allowed_company_ids[0],
                })
            return action

        return super().get_action_click_graph()
