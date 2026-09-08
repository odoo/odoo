# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class CalendarFilters(models.Model):
    _name = 'calendar.filters'
    _description = 'Calendar Filter'

    active = fields.Boolean('Active', default=True)  # Whether or not the partner filter is activated for user_id
    user_id = fields.Many2one('res.users', 'Me', required=True, default=lambda self: self.env.user, index=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', 'Employee', required=True, index=True)

    _user_id_partner_id_unique = models.Constraint(
        'UNIQUE(user_id, partner_id)',
        'A user cannot have the same contact twice.',
    )

    @api.autovacuum
    def _gc_calendar_filters(self):
        """ Making sure to unlink the inactive filters which haven't been updated for more than a month. """
        threshold = fields.Datetime.now() - relativedelta(months=1)
        self.search([
            ('active', '=', False),
            ('write_date', '<', threshold),
        ]).unlink()

    @api.model
    def init_partner_filters(self):
        """ Default the partners filters on the ones listed in the context 'default_partner_ids' key if any.
        If there's none, reset every partner filters.
        """
        self.update_partner_filters(self.env.context.get('default_partner_ids', []))

    @api.model
    def update_partner_filters(self, partner_ids):
        """ Update current user partner filters.
        Deactivating a partner filter by writing "active" to false instead of unlinking.
        This keeps things fast and safe, as the filter can be reactivated/deactivated instantly and
        the calendar view can reload right away (no need to debounce to prevent record not found crashes).

        :param partner_ids: Ids of the partners for which the filters should be activated.
                             Not considering the current user partner as the current user events filtering
                             is handled separatly from the partner filters.
        """
        requested_partner_ids = set(partner_ids) - {self.env.user.partner_id.id}
        existing_filters = self.with_context(active_test=False).search([('user_id', '=', self.env.user.id)])
        new_partner_ids = requested_partner_ids - set(existing_filters.partner_id.ids)
        filters_to_activate = existing_filters.filtered(
            lambda f: f.partner_id.id in requested_partner_ids and not f.active
        )
        filters_to_deactivate = existing_filters.filtered(
            lambda f: f.partner_id.id not in requested_partner_ids and f.active
        )
        if new_partner_ids:
            self.create([
                {'active': True, 'partner_id': partner_id, 'user_id': self.env.user.id}
                for partner_id in new_partner_ids
            ])
        if filters_to_activate:
            filters_to_activate.active = True
        if filters_to_deactivate:
            filters_to_deactivate.active = False
