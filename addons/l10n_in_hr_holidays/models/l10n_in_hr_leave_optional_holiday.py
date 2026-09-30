# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain


class L10nInHrLeaveOptionalHoliday(models.Model):
    _name = 'l10n.in.hr.leave.optional.holiday'
    _description = 'Optional Holidays'
    _order = 'date desc'

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "IN":
            raise UserError(_('You must be logged in an Indian company to use this feature'))
        return super().default_get(field_list)

    name = fields.Char(required=True)
    date = fields.Date(required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)

    @api.depends('name', 'date')
    def _compute_display_name(self):
        for holiday in self:
            name = holiday.name
            if holiday.date:
                name = f'{name} ({holiday.date})'
            holiday.display_name = name

    @api.ondelete(at_uninstall=False)
    def _unlink_except_optional_holidays(self):
        domain = Domain([
            ("holiday_status_id.l10n_in_is_limited_to_optional_days", '=', True),
        ])
        dates_domain = Domain.OR([[
             '&',
            ("request_date_from", "<=", optional_holiday.date),
            ("request_date_to", ">=", optional_holiday.date),
        ] for optional_holiday in self])
        linked_leave_request = self.env["hr.leave"].search_count(domain & dates_domain, limit=1)
        if linked_leave_request:
            raise ValidationError(self.env._("You cannot delete an Optional Holiday that is linked to a leave request."))
