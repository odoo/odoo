from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    hr_attendance_config_id = fields.Many2one(
        comodel_name="hr_attendance.config",
        compute="_compute_hr_attendance_config_id",
        search="_search_hr_attendance_config_id",
    )

    def _search_hr_attendance_config_id(self, operator, value):
        return self._search_config_link("hr_attendance.config", operator, value)

    def _compute_hr_attendance_config_id(self):
        configs = self.env["hr_attendance.config"]._for_each(self)
        by_company = dict(zip(configs.mapped("company_id").ids, configs, strict=True))
        for company in self:
            company.hr_attendance_config_id = by_company.get(company.id, False)

    def _check_hr_presence_control(self, at_install):
        for company in self.env["res.company"].sudo().search([]):
            if at_install and company.hr_config_id.hr_presence_control_login:
                company.hr_config_id.hr_presence_control_attendance = True
            if not at_install and company.hr_config_id.hr_presence_control_attendance:
                company.hr_config_id.hr_presence_control_login = True

    def _action_view_kiosk_mode(self):
        return {
            "type": "ir.actions.act_url",
            "target": "self",
            "url": f"/hr_attendance/kiosk_mode_menu/{self.env.company.id}",
        }
