# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class MrpRoutingWorkcenter(models.Model):
    _name = 'mrp.routing.workcenter'
    _description = 'Work Center Usage'
    _order = 'sequence, id'
    _check_company_auto = True

    name = fields.Char('Operation', required=True)
    workcenter_id = fields.Many2one('mrp.workcenter', 'Work Center', required=True, check_company=True)
    sequence = fields.Integer(
        'Sequence', default=100,
        help="Gives the sequence order when displaying a list of routing Work Centers.")
    bom_id = fields.Many2one(
        'mrp.bom', 'Bill of Material', check_company=True,
        index=True, ondelete='cascade',
        help="The Bill of Material this operation is linked to")
    company_id = fields.Many2one(
        'res.company', 'Company', default=lambda self: self.env.company)
    worksheet_type = fields.Selection([
        ('pdf', 'PDF'), ('google_slide', 'Google Slide'), ('text', 'Text')],
        string="Work Sheet", default="text",
        help="Defines if you want to use a PDF or a Google Slide as work sheet."
    )
    note = fields.Text('Description', help="Text worksheet description")
    worksheet = fields.Binary('PDF')
    worksheet_google_slide = fields.Char('Google Slide', help="Paste the url of your Google Slide. Make sure the access to the document is public.")
    time_mode = fields.Selection([
        ('auto', 'Compute based on tracked time'),
        ('manual', 'Set duration manually')], string='Duration Computation',
        default='manual')
    time_mode_batch = fields.Integer('Based on', default=10)
    time_cycle_manual = fields.Float(
        'Manual Duration', default=60,
        help="Time in minutes:"
        "- In manual mode, time used"
        "- In automatic mode, supposed first time when there aren't any work orders yet")
    time_cycle = fields.Float('Duration', compute="_compute_time_cycle")
    workorder_count = fields.Integer("# Work Orders", compute="_compute_workorder_count")
    workorder_ids = fields.One2many('mrp.workorder', 'operation_id', string="Work Orders")

    @api.depends('time_cycle_manual', 'time_mode', 'workorder_ids')
    def _compute_time_cycle(self):
        manual_ops = self.filtered(lambda operation: operation.time_mode == 'manual')
        for operation in manual_ops:
            operation.time_cycle = operation.time_cycle_manual
        for operation in self - manual_ops:
            data = self.env['mrp.workorder'].read_group([
                ('operation_id', '=', operation.id),
                ('state', '=', 'done')], ['operation_id', 'duration', 'qty_produced'], ['operation_id'],
                limit=operation.time_mode_batch)
            count_data = dict((item['operation_id'][0], (item['duration'], item['qty_produced'])) for item in data)
            if count_data.get(operation.id) and count_data[operation.id][1]:
                operation.time_cycle = (count_data[operation.id][0] / count_data[operation.id][1]) * (operation.workcenter_id.capacity or 1.0)
            else:
                operation.time_cycle = operation.time_cycle_manual

    def _compute_workorder_count(self):
        data = self.env['mrp.workorder'].read_group([
            ('operation_id', 'in', self.ids),
            ('state', '=', 'done')], ['operation_id'], ['operation_id'])
        count_data = dict((item['operation_id'][0], item['operation_id_count']) for item in data)
        for operation in self:
            operation.workorder_count = count_data.get(operation.id, 0)
