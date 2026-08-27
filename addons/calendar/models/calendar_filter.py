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
    def update_user_filters(self, active_filters):
        all_user_filters = self.with_context(active_test=False).search([('user_id', '=', self.env.user.id)])

        filters_by_partner_id = {filter.partner_id.id: filter for filter in all_user_filters}
        active_filters_by_partner = {
            partner_id: filter for partner_id, filter in filters_by_partner_id.items()
            if filter.active and filter.partner_checked
        }
        current_partner_id = self.env.user.partner_id.id
        requested_partner_ids = {
            int(filter['id']) for filter in active_filters if int(filter['id']) != current_partner_id
        }

        filters_to_activate = self.env['calendar.filters']
        filters_to_create = []

        for partner_id in requested_partner_ids:
            if existing_filter := filters_by_partner_id.get(partner_id):
                if partner_id not in active_filters_by_partner:
                    filters_to_activate += existing_filter
            else:
                filters_to_create.append({
                    'active': True,
                    'partner_id': partner_id,
                    'partner_checked': True,
                    'user_id': self.env.user.id,
                })

        filters_to_deactivate = self.env['calendar.filters'].browse([
            filter.id for partner_id, filter in active_filters_by_partner.items()
            if partner_id not in requested_partner_ids
        ])

        if filters_to_create:
            self.create(filters_to_create)
        if filters_to_activate:
            filters_to_activate.write({'active': True, 'partner_checked': True})
        if filters_to_deactivate:
            filters_to_deactivate.write({'active': False, 'partner_checked': False})

    @api.model
    def init_user_filters(self):
        """ Uncheck all user filter by default.
        This method can be overwritten by other module to add user filters if needed."""
        self.with_context(active_test=False).search(
            [('user_id', '=', self.env.user.id), ('partner_checked', '=', True)]
        ).write({'partner_checked': False})
