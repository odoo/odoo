import re

from lxml import etree

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

from .hr_homeworking import DAYS
from odoo.addons.base.models.ir_ui_view_base import attach_ir

_debug = DebugLog(__name__)

TODAY_LOCATION_MARKER = "today_location_name"
_MARKER_TOKEN = re.compile(rf"\b{TODAY_LOCATION_MARKER}\b")


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    monday_location_id = fields.Many2one(
        comodel_name="hr.work.location",
        string="Monday",
    )
    tuesday_location_id = fields.Many2one(
        comodel_name="hr.work.location",
        string="Tuesday",
    )
    wednesday_location_id = fields.Many2one(
        comodel_name="hr.work.location",
        string="Wednesday",
    )
    thursday_location_id = fields.Many2one(
        comodel_name="hr.work.location",
        string="Thursday",
    )
    friday_location_id = fields.Many2one(
        comodel_name="hr.work.location",
        string="Friday",
    )
    saturday_location_id = fields.Many2one(
        comodel_name="hr.work.location",
        string="Saturday",
    )
    sunday_location_id = fields.Many2one(
        comodel_name="hr.work.location",
        string="Sunday",
    )
    location_ids = fields.One2many(
        comodel_name="hr.employee.location",
        inverse_name="employee_id",
        string="Exceptional Work Locations",
        groups="hr.group_hr_user",
    )
    exceptional_location_id = fields.Many2one(
        comodel_name="hr.work.location",
        string="Current",
        compute="_compute_exceptional_location_id",
        compute_sudo=True,
        groups="hr.group_hr_user",
        help="This is the exceptional, non-weekly, location set for today.",
    )
    # The marker a view spells where it means "the location this employee works
    # at today". `get_views` rewrites it to the current weekday's field, which is
    # stored and so can be grouped by and edited inline. It carries no column of
    # its own; an unrewritten read still answers, through work_location_name.
    today_location_name = fields.Char(related="work_location_name")
    hr_icon_display = fields.Selection(
        selection_add=[
            ("presence_home", "At Home"),
            ("presence_office", "At Office"),
            ("presence_other", "At Other"),
        ]
    )

    @api.model
    def _get_current_day_location_field(self):
        return DAYS[fields.Date.today().weekday()]

    @api.model
    def _rewrite_today_location_marker(self, arch, dayfield):
        tree = etree.fromstring(arch)
        rewritten = False
        for node in tree.iter():
            if node.tag == "field" and node.get("name") == TODAY_LOCATION_MARKER:
                node.set("name", dayfield)
                rewritten = True
            context = node.get("context")
            if context and _MARKER_TOKEN.search(context):
                node.set("context", _MARKER_TOKEN.sub(dayfield, context))
                rewritten = True
        if not rewritten:
            return arch
        return etree.tostring(tree, encoding="unicode")

    @api.model
    def get_views(self, views, options=None):
        res = super().get_views(views, options)
        dayfield = self._get_current_day_location_field()
        rewritten = []
        for view_type in ("search", "list"):
            view = res["views"].get(view_type)
            if not view:
                continue
            arch = self._rewrite_today_location_marker(view["arch"], dayfield)
            if arch is view["arch"]:
                continue
            view["arch"] = arch
            attach_ir(view)
            rewritten.append(view_type)
        res["models"][self._name]["fields"].update(self.fields_get([dayfield]))
        _debug.logic("get_views.today_location", dayfield=dayfield, views=rewritten)
        return res

    def _get_today_location(self):
        dayfield = self._get_current_day_location_field()
        return {
            employee.id: employee.exceptional_location_id or employee[dayfield]
            for employee in self
        }

    # `location_ids` is declared for its dependency edge alone: the ORM invalidates
    # this field when an exception row is created, moved or deleted. The compute
    # still searches, so the cost stays one query for the whole prefetch set
    # instead of loading every exception an employee has ever had.
    @api.depends("location_ids.date", "location_ids.work_location_id")
    def _compute_exceptional_location_id(self):
        today = fields.Date.today()
        exceptions = self.env["hr.employee.location"].search(
            [("employee_id", "in", self.ids), ("date", "=", today)]
        )
        by_employee = {
            exception.employee_id.id: exception.work_location_id
            for exception in exceptions
        }
        _debug.logic(
            "exceptional_location.resolved",
            employees=self,
            date=today,
            exceptions=len(exceptions),
        )
        for employee in self:
            employee.exceptional_location_id = by_employee.get(employee.id, False)

    @api.depends(*DAYS, "exceptional_location_id", "active")
    def _compute_presence_icon(self):
        super()._compute_presence_icon()
        today_locations = self._get_today_location()
        for employee in self:
            location = today_locations[employee.id]
            if not location or not employee.active:
                continue
            employee.hr_icon_display = f"presence_{location.location_type}"
            employee.show_hr_icon_display = True

    @api.depends(*DAYS, "exceptional_location_id")
    def _compute_work_location_name(self):
        today_locations = self._get_today_location()
        for employee in self:
            employee.work_location_name = today_locations[employee.id].name

    @api.depends(*DAYS, "exceptional_location_id")
    def _compute_work_location_type(self):
        today_locations = self._get_today_location()
        for employee in self:
            employee.work_location_type = today_locations[employee.id].location_type
