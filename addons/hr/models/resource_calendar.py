
from odoo import api, fields, models
from odoo.fields import Domain
from odoo.exceptions import ValidationError


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    version_ids = fields.One2many('hr.version', 'resource_calendar_id', readonly=True, copy=False)

    @api.constrains('company_id')
    def _check_company_id(self):
        for res_calendar in self:
            if res_calendar.company_id:
                if any(res_calendar.company_id not in version.company_id.parent_ids for version in res_calendar.version_ids):
                    raise ValidationError(self.env._("The working schedule '%s' is linked to version(s) not compatible with its new company.") % res_calendar.name)

    def write(self, vals):
        if self.version_ids.company_id - self.env.companies:
            raise ValidationError(self.env._("You can't change this working schedule, it's used by employees from other companies you don't have access to. Contact your admin or create a new working schedule."))
        return super().write(vals)

    def get_number_of_linked_employees(self):
        self.ensure_one()
        return len(set(self.version_ids.mapped('employee_id')))

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
