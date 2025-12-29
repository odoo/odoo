# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class CalendarFilters(models.Model):
    _name = 'calendar.filters'
    _description = 'Calendar Filter'

    user_id = fields.Many2one('res.users', 'Me', required=True, default=lambda self: self.env.user, index=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', 'Employee', required=True, index=True)
    active = fields.Boolean('Active', default=True)
    partner_checked = fields.Boolean('Checked', default=True)  # used to know if the partner is checked in the filter of the calendar view for the user_id.

    _user_id_partner_id_unique = models.Constraint(
        'UNIQUE(user_id, partner_id)',
        'A user cannot have the same contact twice.',
    )

    @api.model
    def unlink_from_partner_id(self, partner_id):
        return self.search([('partner_id', '=', partner_id)]).unlink()

    @api.model
    def create_partner_calendar_filters(self, partner_ids):
        """Create missing filters for the given partners."""
        user_id = self.env.user.id
        existing_filters = self.with_context(active_test=False).search([
            ('user_id', '=', user_id),
            ('partner_id', 'in', partner_ids),
        ])
        existing_filters.write({
            'partner_checked': True,
        })
        if missing_partner_ids := list(set(partner_ids) - set(existing_filters.partner_id.ids)):
            self.create([
                {'user_id': user_id, 'partner_id': pid, 'active': False}
                for pid in missing_partner_ids
            ])
