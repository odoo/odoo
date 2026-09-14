from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrResumeLine(models.Model):
    _inherit = "hr.resume.line"

    event_id = fields.Many2one(
        comodel_name="event.event",
        string="Onsite Course",
        compute="_compute_event_id",
        store=True,
        index="btree_not_null",
        readonly=True,
        domain="[('is_multi_slots', '=', True), ('registration_ids', 'any', [('partner_id.employee', '=', True)])]",
    )
    course_type = fields.Selection(
        selection_add=[("onsite", "Onsite")],
        ondelete={"onsite": "cascade"},
    )

    @api.onchange("event_id")
    def _onchange_event_id(self):
        if not self.name and self.event_id:
            self.name = self.event_id.name

    @api.depends("course_type")
    def _compute_event_id(self):
        _debug.logic("onsite_event_cleared", lines=self)
        for resume_line in self:
            if resume_line.course_type != "onsite":
                resume_line.event_id = False

    def _compute_color(self):
        super()._compute_color()
        for resume_line in self:
            if resume_line.course_type == "onsite":
                resume_line.color = "#714a66"
