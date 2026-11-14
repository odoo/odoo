
from odoo import fields, models
from odoo.fields import Domain
from odoo.exceptions import ValidationError


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

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

    def write(self, vals):
        versions = self.env['hr.version'].sudo().with_context(active_test=False).search([('resource_calendar_id', 'in', self.ids)])
        if versions.company_id - self.env.companies:
            raise ValidationError(self.env._("You can't change this working schedule, it's used by employees from other companies you don't have access to. Contact your admin or create a new working schedule."))
        return super().write(vals)
