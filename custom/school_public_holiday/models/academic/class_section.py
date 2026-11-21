from odoo import _, api, fields, models


class UniversityClassSection(models.Model):
    _inherit = "university.class.section"

    holiday_conflict_count = fields.Integer(
        string="Holiday Conflicts",
        compute="_compute_holiday_conflicts",
    )
    has_holiday_conflicts = fields.Boolean(
        string="Has Holiday Conflicts",
        compute="_compute_holiday_conflicts",
    )

    @api.depends("slot_ids.on_holiday", "slot_ids.state", "slot_ids.allow_on_holiday")
    def _compute_holiday_conflicts(self):
        for section in self:
            conflicts = section.slot_ids.filtered(
                lambda s: s.on_holiday and s.state != "cancelled" and not s.allow_on_holiday
            )
            section.holiday_conflict_count = len(conflicts)
            section.has_holiday_conflicts = bool(conflicts)

    def action_view_holiday_conflicts(self):
        self.ensure_one()
        conflicts = self.slot_ids.filtered(
            lambda s: s.on_holiday and s.state != "cancelled" and not s.allow_on_holiday
        )
        return {
            "name": _("Holiday Conflicts for %s") % self.name,
            "type": "ir.actions.act_window",
            "res_model": "university.timetable.slot",
            "view_mode": "list,form,calendar",
            "domain": [("id", "in", conflicts.ids)],
            "context": {"default_section_id": self.id},
        }
