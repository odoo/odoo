
from odoo import api, fields, models
from odoo.fields import Domain
from odoo.exceptions import ValidationError


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    @api.constrains('company_id')
    def _check_company_id(self):
        versions_per_calendar = {
            calnder_id.id: versions for
            calnder_id, versions in self.env['hr.version'].sudo()._read_group(
            domain=[('resource_calendar_id', 'in', self.ids)],
            groupby=['resource_calendar_id'],
            aggregates=['id:recordset'])
        }
        for res_calendar in self:
            if res_calendar.company_id:
                versions = versions_per_calendar.get(res_calendar.id, [])
                if not all(res_calendar.company_id in version.company_id.parent_ids for version in versions):
                    raise ValidationError(self.env._("The working schedule '%s' is linked to version(s) not compatible with its new company.") % res_calendar.name)

    def write(self, vals):
        versions_per_calendar = {
            calnder_id.id: versions for
            calnder_id, versions in self.env['hr.version'].sudo()._read_group(
            domain=[('resource_calendar_id', 'in', self.ids)],
            groupby=['resource_calendar_id'],
            aggregates=['id:recordset'])
        }
        for res_calendar in self:
            versions = versions_per_calendar.get(res_calendar.id, [])
            if any(version.company_id not in self.env.companies for version in versions):
                raise ValidationError(self.env._("You can't change this working schedule, it's used by employees from other companies you don't have access to. Contact your admin or create a new working schedule."))
        return super().write(vals)

    def get_number_of_linked_employees(self):
        self.ensure_one()
        versions = self.env['hr.version'].sudo().search([('resource_calendar_id', '=', self.id)])
        if any(version.company_id not in self.env.companies for version in versions):
            raise ValidationError(self.env._("You can't change this working schedule, it's used by employees from other companies you don't have access to. Contact your admin or create a new working schedule."))
        return len(versions.employee_id)

    def transfer_leaves_to(self, other_calendar, resources=None, from_date=None):
        """
            Transfer some resource.calendar.leaves from 'self' to another calendar 'other_calendar'.
            Transfered leaves linked to `resources` (or all if `resources` is None) and starting
            after 'from_date' (or today if None).
        """
        from_date = from_date or fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        domain = [
            ('calendar_id', 'in', self.ids),
            ('date_from', '>=', from_date),
        ]
        domain = Domain.AND([domain, [('resource_id', 'in', resources.ids)]]) if resources else domain

        self.env['resource.calendar.leaves'].search(domain).write({
            'calendar_id': other_calendar.id,
        })
