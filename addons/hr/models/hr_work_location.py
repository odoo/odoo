# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError

from .hr_employee_location import DAYS


class HrWorkLocation(models.Model):
    _name = 'hr.work.location'
    _description = "Work Location"
    _order = 'name'

    active = fields.Boolean(default=True)
    name = fields.Char(string="Work Location", required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    location_type = fields.Selection([
        ('home', 'Home'),
        ('office', 'Office'),
        ('other', 'Other')], string='Location Type', default='office', required=True)
    address_id = fields.Many2one('res.partner', string="Work Address", check_company=True)
    location_number = fields.Char()

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used_by_employee(self):
        domains = [(day, 'in', self.ids) for day in DAYS]
        employee_uses_location = self.env['hr.employee'].search_count(domains, limit=1)
        if employee_uses_location:
            raise UserError(self.env._("You cannot delete locations that are being used by your employees"))
        exceptions_using_location = self.env['hr.employee.location'].search([('work_location_id', 'in', self.ids)])
        exceptions_using_location.unlink()

    # Computed field
    # Following the refactor of the badges_selection component, all badge field types
    # (many2one, selection, etc.) were unified. To simplify the many2one
    # implementation, the component now only supports a related_icon_field to
    # retrieve each record's icon. Icons can no longer be defined directly in the views (XML),
    # so this computed field provides the required value.
    icon = fields.Char(compute='_compute_icon')

    @api.depends('location_type')
    def _compute_icon(self):
        for record in self:
            if record.location_type == 'office':
                record.icon = 'fa-building-o'
            elif record.location_type == 'home':
                record.icon = 'fa-home'
            else:
                record.icon = None
