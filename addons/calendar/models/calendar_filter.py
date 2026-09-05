# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

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
    def _cron_clean_inactive_calendar_filters(self):
        """ Since calendar filters are managed solely through "update_partner_filters"
        and "init_partner_filters" (not the JS "unlinkFilter" method anymore) and
        deactivating a filter only writes "partner_checked"/"active" to false rather than unlinking it,
        inactive filter records can build up indefinitely.
        This cron unlinks the ones that have stayed inactive for at least 1 month.
        """
        threshold = fields.Datetime.now() - relativedelta(months=1)
        self.with_context(active_test=False).search([
            ('active', '=', False),
            ('write_date', '<', threshold),
        ]).unlink()

    @api.model
    def init_partner_filters(self):
        """ Uncheck all partner filters by default.
        This method can be overwritten by other module to add user filters if needed.
        """
        self.with_context(active_test=False).search(
            [('user_id', '=', self.env.user.id), ('partner_checked', '=', True)]
        ).write({'partner_checked': False})

    @api.model
    def unlink_from_partner_id(self, partner_id):
        return self.search([('partner_id', '=', partner_id)]).unlink()

    @api.model
    def update_partner_filters(self, partner_ids):
        """ Update current user partner filters.
        :partner_ids: Ids of the partners for which the filters should be activated.
        """
        requested_partner_ids = set(partner_ids)
        existing_filters = self.with_context(active_test=False).search([('user_id', '=', self.env.user.id)])
        new_partner_ids = requested_partner_ids - set(existing_filters.partner_id.ids)
        filters_to_activate = existing_filters.filtered(
            lambda f: f.partner_id.id in requested_partner_ids and not (f.active and f.partner_checked)
        )
        filters_to_deactivate = existing_filters.filtered(
            lambda f: f.partner_id.id not in requested_partner_ids and f.active and f.partner_checked
        )
        if new_partner_ids:
            self.create([
                {'active': True, 'partner_id': partner_id, 'partner_checked': True, 'user_id': self.env.user.id}
                for partner_id in new_partner_ids
            ])
        if filters_to_activate:
            filters_to_activate.write({'active': True, 'partner_checked': True})
        if filters_to_deactivate:
            # Always deactivate by writing "partner_checked"/"active" to false instead of unlinking, so the
            # JS side can reload immediately. No unlink means no crash risk from rapid clicks when reloading.
            filters_to_deactivate.write({'active': False, 'partner_checked': False})
