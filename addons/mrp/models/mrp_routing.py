# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError


class MrpRoutingWorkcenter(models.Model):
    _name = 'mrp.routing.workcenter'
    _description = 'Work Center Usage'
    _order = 'bom_id, sequence, id'
    _check_company_auto = True

    name = fields.Char('Operation', required=True)
    active = fields.Boolean(default=True)
    workcenter_id = fields.Many2one('mrp.workcenter', 'Work Center', required=True, check_company=True)
    sequence = fields.Integer(
        'Sequence', default=100,
        help="Gives the sequence order when displaying a list of routing Work Centers.")
    bom_id = fields.Many2one(
        'mrp.bom', 'Bill of Material',
        index=True, ondelete='cascade', required=True, check_company=True)
    company_id = fields.Many2one('res.company', 'Company', related='bom_id.company_id')
    worksheet_type = fields.Selection([
        ('pdf', 'PDF'), ('google_slide', 'Google Slide'), ('text', 'Text')],
        string="Worksheet", default="text"
    )
    note = fields.Html('Description')
    worksheet = fields.Binary('PDF')
    worksheet_google_slide = fields.Char('Google Slide', help="Paste the url of your Google Slide. Make sure the access to the document is public.")
    time_mode = fields.Selection([
        ('auto', 'Compute based on tracked time'),
        ('manual', 'Set duration manually')], string='Duration Computation',
        default='manual')
    time_mode_batch = fields.Integer('Based on', default=10)
    time_computed_on = fields.Char('Computed on last', compute='_compute_time_computed_on')
    time_cycle_manual = fields.Float(
        'Manual Duration', default=60,
        help="Time in minutes:"
        "- In manual mode, time used"
        "- In automatic mode, supposed first time when there aren't any work orders yet")
    time_cycle = fields.Float('Duration', compute="_compute_time_cycle")
    workorder_count = fields.Integer("# Work Orders", compute="_compute_workorder_count")
    workorder_ids = fields.One2many('mrp.workorder', 'operation_id', string="Work Orders")
    possible_bom_product_template_attribute_value_ids = fields.Many2many(related='bom_id.possible_product_template_attribute_value_ids')
    bom_product_template_attribute_value_ids = fields.Many2many(
        'product.template.attribute.value', string="Apply on Variants", ondelete='restrict',
        domain="[('id', 'in', possible_bom_product_template_attribute_value_ids)]",
        help="BOM Product Variants needed to apply this line.")
    allow_operation_dependencies = fields.Boolean(related='bom_id.allow_operation_dependencies')
    blocked_by_operation_ids = fields.Many2many('mrp.routing.workcenter', relation="mrp_routing_workcenter_dependencies_rel",
                                     column1="operation_id", column2="blocked_by_id",
                                     string="Blocked By", help="Operations that need to be completed before this operation can start.",
                                     domain="[('allow_operation_dependencies', '=', True), ('id', '!=', id), ('bom_id', '=', bom_id)]",
                                     copy=False)
    needed_by_operation_ids = fields.Many2many('mrp.routing.workcenter', relation="mrp_routing_workcenter_dependencies_rel",
                                     column1="blocked_by_id", column2="operation_id",
                                     string="Blocks", help="Operations that cannot start before this operation is completed.",
                                     domain="[('allow_operation_dependencies', '=', True), ('id', '!=', id), ('bom_id', '=', bom_id)]",
                                     copy=False)

    @api.depends('time_mode', 'time_mode_batch')
    def _compute_time_computed_on(self):
        for operation in self:
            operation.time_computed_on = _('%i work orders') % operation.time_mode_batch if operation.time_mode != 'manual' else False

    @api.depends('time_cycle_manual', 'time_mode', 'workorder_ids')
    def _compute_time_cycle(self):
        manual_ops = self.filtered(lambda operation: operation.time_mode == 'manual')
        for operation in manual_ops:
            operation.time_cycle = operation.time_cycle_manual
        for operation in self - manual_ops:
            data = self.env['mrp.workorder'].search([
                ('operation_id', '=', operation.id),
                ('qty_produced', '>', 0),
                ('state', '=', 'done')],
                limit=operation.time_mode_batch,
                order="date_finished desc, id desc")
            # To compute the time_cycle, we can take the total duration of previous operations
            # but for the quantity, we will take in consideration the qty_produced like if the capacity was 1.
            # So producing 50 in 00:10 with capacity 2, for the time_cycle, we assume it is 25 in 00:10
            # When recomputing the expected duration, the capacity is used again to divide the qty to produce
            # so that if we need 50 with capacity 2, it will compute the expected of 25 which is 00:10
            total_duration = 0  # Can be 0 since it's not an invalid duration for BoM
            cycle_number = 0  # Never 0 unless infinite item['workcenter_id'].capacity
            for item in data:
                total_duration += item['duration']
                capacity = item['workcenter_id']._get_capacity(item.product_id)
                cycle_number += tools.float_round((item['qty_produced'] / capacity or 1.0), precision_digits=0, rounding_method='UP')
            if cycle_number:
                operation.time_cycle = total_duration / cycle_number
            else:
                operation.time_cycle = operation.time_cycle_manual

    def _compute_workorder_count(self):
        data = self.env['mrp.workorder']._read_group([
            ('operation_id', 'in', self.ids),
            ('state', '=', 'done')], ['operation_id'], ['__count'])
        count_data = {operation.id: count for operation, count in data}
        for operation in self:
            operation.workorder_count = count_data.get(operation.id, 0)

    @api.constrains('blocked_by_operation_ids')
    def _check_no_cyclic_dependencies(self):
        if not self._check_m2m_recursion('blocked_by_operation_ids'):
            raise ValidationError(_("You cannot create cyclic dependency."))

    def action_archive(self):
        res = super().action_archive()
        bom_lines = self.env['mrp.bom.line'].search([('operation_id', 'in', self.ids)])
        bom_lines.write({'operation_id': False})
        return res

    def copy_to_bom(self):
        if 'bom_id' in self.env.context:
            bom_id = self.env.context.get('bom_id')
            for operation in self:
                operation.copy({'bom_id': bom_id})
            return {
                'view_mode': 'form',
                'res_model': 'mrp.bom',
                'views': [(False, 'form')],
                'type': 'ir.actions.act_window',
                'res_id': bom_id,
            }

    def copy_existing_operations(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Select Operations to Copy'),
            'res_model': 'mrp.routing.workcenter',
            'view_mode': 'tree,form',
            'domain': ['|', ('bom_id', '=', False), ('bom_id.active', '=', True)],
            'context' : {
                'bom_id': self.env.context["bom_id"],
                'tree_view_ref': 'mrp.mrp_routing_workcenter_copy_to_bom_tree_view',
            }
        }

    def _skip_operation_line(self, product):
        """ Control if a operation should be processed, can be inherited to add
        custom control.
        """
        self.ensure_one()
        # skip operation line if archived
        if not self.active:
            return True
        if product._name == 'product.template':
            return False
        return not product._match_all_variant_values(self.bom_product_template_attribute_value_ids)

    def _get_comparison_values(self):
        if not self:
            return False
        self.ensure_one()
        return tuple(self[key] for key in  ('name', 'company_id', 'workcenter_id', 'time_mode', 'time_cycle_manual', 'bom_product_template_attribute_value_ids'))
