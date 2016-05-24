# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    @api.depends('sheet_id.employee_id', 'sheet_id.date_from', 'sheet_id.date_to', 'user_id', 'date', 'project_id')
    def _sheet(self):
        for ts_line in self:
            if not ts_line.project_id:
                continue
            sheet_ids = self.env['hr_timesheet_sheet.sheet'].search(
                [('date_to', '>=', ts_line.date), ('date_from', '<=', ts_line.date),
                 ('employee_id.user_id', '=', ts_line.user_id.id),
                 ('state', 'in', ['draft', 'new'])],)
            if sheet_ids:
                # [0] because only one sheet possible for an employee between 2 dates
                ts_line.sheet_id = sheet_ids.name_get()[0]

    sheet_id = fields.Many2one('hr_timesheet_sheet.sheet', compute='_sheet', string='Sheet', select="1", ondelete="cascade", store=True)

    @api.multi
    def write(self, values):
        self._check()
        return super(AccountAnalyticLine, self).write(values)

    @api.multi
    def unlink(self):
        self._check()
        return super(AccountAnalyticLine, self).unlink()

    def _check(self):
        for att in self:
            if att.sheet_id and att.sheet_id.state not in ('draft', 'new'):
                raise UserError(_('You cannot modify an entry in a confirmed timesheet.'))
        return True
