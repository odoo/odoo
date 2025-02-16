# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class L10nInHrLeaveOptionalHoliday(models.Model):
    _name = 'l10n.in.hr.leave.optional.holiday'
    _description = 'Optional Holidays'
    _order = 'date desc'

    name = fields.Char(required=True)
    date = fields.Date(required=True)

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "IN":
            raise UserError(_('You must be logged in an Indian company to use this feature'))
        return super().default_get(field_list)

    @api.depends('name', 'date')
    def _compute_display_name(self):
        for holiday in self:
            name = holiday.name
            if holiday.date:
                name = f'{name} ({holiday.date})'
            holiday.display_name = name
