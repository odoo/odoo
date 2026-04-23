
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    @api.constrains('company_id')
    def _check_company_id_not_in_use(self):
        calendars = self.filtered(lambda c: not c.company_id)
        if not calendars:
            return
        in_use_ids = {
            cal.id for [cal] in self.env['hr.version']._read_group(
                Domain('resource_calendar_id', 'in', calendars.ids),
                groupby=['resource_calendar_id'],
            )
        }
        in_use = calendars.filtered(lambda c: c.id in in_use_ids)
        if in_use:
            raise ValidationError(self.env._(
                'The following working schedules cannot have their company removed while they are still in use: %(names)s',
                names=', '.join(in_use.mapped('name')),
            ))

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
