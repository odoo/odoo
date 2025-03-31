# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class ProjectUpdate(models.Model):
    _inherit = "project.update"

    display_timesheet_stats = fields.Boolean(compute="_compute_display_timesheet_stats", export_string_translation=False)
    allocated_time = fields.Integer("Allocated Time", readonly=True)
    timesheet_time = fields.Integer("Timesheet Time", readonly=True)
    timesheet_percentage = fields.Integer(compute="_compute_timesheet_percentage", export_string_translation=False)
    uom_id = fields.Many2one("uom.uom", "Unit Of Measure", readonly=True, export_string_translation=False)

    def _compute_timesheet_percentage(self):
        for update in self:
            update.timesheet_percentage = update.allocated_time and round(update.timesheet_time * 100 / update.allocated_time)

    def _compute_display_timesheet_stats(self):
        for update in self:
            update.display_timesheet_stats = update.project_id.allow_timesheets

    # ---------------------------------
    # ORM Override
    # ---------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        updates = super().create(vals_list)
        encode_uom = self.env.company.timesheet_encode_uom_id
        ratio = self.env.ref("uom.product_uom_hour").ratio / encode_uom.ratio
        for update in updates:
            project = update.project_id
            project.sudo().last_update_id = update
            update.write({
                "uom_id": encode_uom,
                "allocated_time": round(project.allocated_hours / ratio),
                "timesheet_time": round(project.total_timesheet_time / ratio),
            })
        return updates
