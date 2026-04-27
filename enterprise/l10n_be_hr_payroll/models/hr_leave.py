from odoo import api, fields, models, _

from dateutil.relativedelta import relativedelta


class HolidaysRequest(models.Model):
    _name = "hr.leave"
    _inherit = 'hr.leave'

    l10n_be_sickness_relapse = fields.Boolean(default=True, string="Sickness Relapse")
    l10n_be_sickness_can_relapse = fields.Boolean(compute="_compute_can_relapse")

    @api.depends("date_from", "validation_type", "employee_id", "holiday_status_id.work_entry_type_id.code")
    def _compute_can_relapse(self):
        l10n_be_leaves = self.filtered(
            lambda leave:
            leave.company_id.country_code == "BE"
            and leave.validation_type == "hr"
            and leave.employee_id
            and leave.date_from
        )

        sick_work_entry_type = self.env.ref("hr_work_entry_contract.work_entry_type_sick_leave")
        partial_sick_work_entry_type = self.env.ref("l10n_be_hr_payroll.work_entry_type_part_sick")
        long_sick_work_entry_type = self.env.ref("l10n_be_hr_payroll.work_entry_type_long_sick")
        sick_work_entry_types = (
            sick_work_entry_type
            + partial_sick_work_entry_type
            + long_sick_work_entry_type
        )

        if l10n_be_leaves:
            recent_leaves = dict(
                    self
                    .env["hr.leave"]
                    ._read_group(
                        domain=[
                            ("employee_id.id", "in", l10n_be_leaves.employee_id.ids),
                            ("date_to", "<=", max(l10n_be_leaves.mapped("date_from"))),
                            ("date_to", ">=", min(l10n_be_leaves.mapped(
                                lambda l: l.date_from + relativedelta(days=-56)
                                if l.date_from.year >= 2026
                                else l.date_from + relativedelta(days=-14)
                            ))),
                            ("holiday_status_id.work_entry_type_id", "in", sick_work_entry_types.ids),
                            ("state", "=", "validate"),
                        ],
                        groupby=["employee_id"],
                        aggregates=["request_date_to:max"],
                    )
            )
            for employee, leaves in l10n_be_leaves.grouped('employee_id').items():
                for leave in leaves:
                    leave.l10n_be_sickness_can_relapse = bool(recent_leaves.get(employee))

        for leave in (self - l10n_be_leaves):
            leave.l10n_be_sickness_can_relapse = False

    def action_validate(self, check_state=True):
        res = super().action_validate(check_state=check_state)
        activity_type_id = self.env.ref('mail.mail_activity_data_todo').id
        res_model_id = self.env.ref('hr_holidays.model_hr_leave').id
        for leave in self:
            if leave.employee_id.company_id.country_id.code == "BE" and \
                    leave.sudo().holiday_status_id.work_entry_type_id.code in self._get_drs_work_entry_type_codes():
                drs_link = "https://www.socialsecurity.be/site_fr/employer/applics/drs/index.htm"
                drs_link = '<a href="%s" target="_blank">%s</a>' % (drs_link, drs_link)
                user_ids = leave.holiday_status_id.responsible_ids.ids or self.env.user.ids
                note = _('%(employee)s is in %(holiday_status)s. Fill in the appropriate eDRS here: %(link)s',
                   employee=leave.employee_id.name,
                   holiday_status=leave.holiday_status_id.name,
                   link=drs_link)
                activity_vals = []
                for user_id in user_ids:
                    activity_vals.append({
                        'activity_type_id': activity_type_id,
                        'automated': True,
                        'note': note,
                        'user_id': user_id,
                        'res_id': leave.id,
                        'res_model_id': res_model_id,
                    })
                self.env['mail.activity'].create(activity_vals)
        return res

    def _get_drs_work_entry_type_codes(self):
        drs_work_entry_types = [
            'LEAVE290', # Breast Feeding
            'LEAVE280', # Long Term Sick
            'LEAVE210', # Maternity
            'LEAVE230', # Paternity Time Off (Legal)
            'YOUNG01',  # Youth Time Off
            'LEAVE115', # Work Accident
        ]
        return drs_work_entry_types
