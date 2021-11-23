from odoo import fields, models
from odoo.addons.base.models.res_users import check_identity


class User(models.Model):
    _inherit = 'res.users'

    @check_identity
    def preference_calendar_subscribe(self):
        base_url = self.get_base_url()
        key = self.env['res.users.apikeys']._generate('calendar.ics', 'Calendar Subscription')
        return {
            'context': {
                'calendar_url': f"{base_url}/calendar.ics?key={key}",
            },
            'tag': 'calendar_subscribe',
            'target': 'new',
            'type': 'ir.actions.client',
        }

    def _get_ics_domain(self, lower_bound=False, upper_bound=False):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        if not lower_bound:
            days = int(get_param('calendar.ics.lower_bound', default=30))
            lower_bound = fields.Datetime.subtract(fields.Datetime.now(), days=days)
        if not upper_bound:
            days = int(get_param('calendar.ics.upper_bound', default=90))
            upper_bound = fields.Datetime.add(fields.Datetime.now(), days=days)
        # FIXME DRY google_calendar, microsoft_calendar
        return [
            ('partner_ids.user_ids', 'in', self.env.user.id),
            ('stop', '>', lower_bound),
            ('start', '<', upper_bound),
            # Do not sync events that follow the recurrence, they are already synced at recurrence creation
            '!', '&', '&', ('recurrency', '=', True), ('recurrence_id', '!=', False), ('follow_recurrence', '=', True)
        ]
