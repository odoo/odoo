# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def _default_encoding_uom_id(self):
        uom = self.env.ref('uom.product_uom_hour', raise_if_not_found=False)
        wtime = self.env.ref('uom.uom_categ_wtime')
        if not uom:
            uom = self.env['uom.uom'].search([('category_id', '=', wtime.id), ('uom_type', '=', 'reference')], limit=1)
        if not uom:
            uom = self.env['uom.uom'].search([('category_id', '=', wtime.id)], limit=1)
        return uom

    module_project_timesheet_synchro = fields.Boolean("Awesome Timesheet",
        compute="_compute_timesheet_modules", store=True, readonly=False)
    module_project_timesheet_holidays = fields.Boolean("Record Time Off",
        compute="_compute_timesheet_modules", store=True, readonly=False)
    project_time_mode_id = fields.Many2one('uom.uom',
        string='Project Time Unit',
        config_parameter='hr_timesheet.project_time_mode_id',
        domain=lambda self: [('category_id', '=', self.env.ref('uom.uom_categ_wtime').id)],
        default=_default_encoding_uom_id,
        readonly=False,
        help="This will set the unit of measure used in projects and tasks.\n"
             "If you use the timesheet linked to projects, don't "
             "forget to setup the right unit of measure in your employees.")
    timesheet_encode_uom_id = fields.Many2one('uom.uom',
        string="Encoding Unit",
        config_parameter='hr_timesheet.timesheet_encode_uom_id',
        domain=lambda self: [('category_id', '=', self.env.ref('uom.uom_categ_wtime').id)],
        default=_default_encoding_uom_id,
        help="""This will set the unit of measure used to encode timesheet. This will simply provide tools
        and widgets to help the encoding. All reporting will still be expressed in hours (default value).""")
    timesheet_min_duration = fields.Integer('Minimal duration', default=15, config_parameter='hr_timesheet.timesheet_min_duration')
    timesheet_rounding = fields.Integer('Rounding up', default=15, config_parameter='hr_timesheet.timesheet_rounding')
    is_encode_uom_days = fields.Boolean(compute='_compute_is_encode_uom_days')

    @api.depends('timesheet_encode_uom_id')
    def _compute_is_encode_uom_days(self):
        product_uom_day = self.env.ref('uom.product_uom_day')
        for settings in self:
            settings.is_encode_uom_days = settings.timesheet_encode_uom_id == product_uom_day

    @api.depends('module_hr_timesheet')
    def _compute_timesheet_modules(self):
        self.filtered(lambda config: not config.module_hr_timesheet).update({
            'module_project_timesheet_synchro': False,
            'module_project_timesheet_holidays': False,
        })
