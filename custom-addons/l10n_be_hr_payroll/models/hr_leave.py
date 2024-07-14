from odoo import models, _


class HolidaysRequest(models.Model):
    _name = "hr.leave"
    _inherit = 'hr.leave'

    def action_validate(self):
        res = super(HolidaysRequest, self).action_validate()
        activity_type_id = self.env.ref('mail.mail_activity_data_todo').id
        res_model_id = self.env.ref('hr_holidays.model_hr_leave').id
        for leave in self:
            if leave.employee_id.company_id.country_id.code == "BE" and \
                    leave.sudo().holiday_status_id.work_entry_type_id.code in self._get_drs_work_entry_type_codes():
                drs_link = "https://www.socialsecurity.be/site_fr/employer/applics/drs/index.htm"
                drs_link = '<a href="%s" target="_blank">%s</a>' % (drs_link, drs_link)
                user_ids = leave.holiday_status_id.responsible_ids.ids or self.env.user.ids
                note = _('%s is in %s. Fill in the appropriate eDRS here: %s',
                   leave.employee_id.name,
                   leave.holiday_status_id.name,
                   drs_link)
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
