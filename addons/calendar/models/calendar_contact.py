# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from odoo import api, fields, models


class Contacts(models.Model):
    _name = 'calendar.contacts'
    _description = 'Calendar Contacts'

    user_id = fields.Many2one('res.users', 'Me', required=True, default=lambda self: self.env.user)
    partner_id = fields.Many2one('res.partner', 'Employee', required=True)

    # The active field is used to keep track if check or uncheck in the DB
    # So we give the _active_name another field
    active = fields.Boolean('Checked', default=True)
    x_active = fields.Boolean('Active', default=True)
    _active_name = 'x_active'

    _sql_constraints = [
        ('user_id_partner_id_unique', 'UNIQUE(user_id, partner_id)', 'A user cannot have twice the same contact.')
    ]

    @api.model
    def unlink_from_partner_id(self, partner_id):
        return self.search([('partner_id', '=', partner_id)]).unlink()

    @api.model
    def update_check_filter(self, data):
        """
        Update the checked / unchecked  active field in the DB for the defined partner.

        :param data: javascript object
        """
        partner_id = data['data']['value']
        is_checked = bool(data['data']['active'])
        current_user_id = self.env.user.id

        # If the "show all" checkbox has been clicked, we do not make DB updates
        # todo IMP save the "show all" state as well (in new task ?)
        if partner_id == 'all':
            return

        partner_id = int(partner_id)
        domain = ['&', ('partner_id', '=', partner_id), ('user_id', '=', current_user_id)]
        partner_to_update = self.env['calendar.contacts'].search(domain)
        partner_to_update.active = is_checked

    # todo probably have to remove all this
    # This should be called by the JS to retrieve the data
    # But where and when ?
    # It seems that this model is already read by the frontend "magically" but I can't find where
    @api.model
    def get_check_filters(self):
        current_user_id = self.env.user.id

        domain = [('user_id', '=', current_user_id)]
        partners_in_filters = self.env['calendar.contacts'].search(domain)

        active_data = []
        for p in partners_in_filters:
            active_data.append((p.partner_id.id, p.active))

        return json.dumps(active_data)
