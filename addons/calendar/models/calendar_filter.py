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
    def get_partner_filters(self, filter_ids, *kwargs):
        is_user = False
        if filter_ids and filter_ids[0] is None:
            is_user = filter_ids.pop() or True
        return self.search([('id', '=', filter_ids)]).partner_id | (is_user and self.env.user.partner_id)

    @api.model
    def update_user_filters(self, active_filters):
        all_user_filters = self.with_context(active_test=False).search([('user_id', '=', self.env.user.id)])
        all_active_user_filters = all_user_filters.filtered(lambda f: f.active and f.partner_checked)
        filter_partners_to_update = self.env['res.partner']
        filters_to_create = []
        for filter in active_filters:
            partner = self.env['res.partner'].browse(int(filter.get('id')))
            if partner == self.env.user.partner_id:
                continue
            if existing_filter := all_active_user_filters.filtered(lambda f: f.partner_id == partner):
                all_active_user_filters -= existing_filter
                continue
            if partner in all_user_filters.partner_id:
                filter_partners_to_update += partner
            else:
                filters_to_create.append({
                    'user_id': self.env.user.id,
                    'partner_id': partner.id,
                    'active': True,
                    'partner_checked': True,
                })
        if filters_to_create:
            self.create(filters_to_create)
        if filter_partners_to_update:
            all_user_filters.filtered(lambda f: f.partner_id in filter_partners_to_update).write({
                'active': True,
                'partner_checked': True,
            })
        if all_active_user_filters:
            all_active_user_filters.write({
                'active': False,
                'partner_checked': False,
            })

    @api.model
    def reset_user_filters(self):
        self.with_context(active_test=False).search(
            [('user_id', '=', self.env.user.id), ('partner_checked', '=', True)]
        ).write({'partner_checked': False})
