# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.exceptions import AccessError


class Partner(models.Model):

    _inherit = ['res.partner']

    @api.model
    def get_static_mention_suggestions(self):
        """ Extend the mail's static mention suggestions by adding the employees. """
        suggestions = super(Partner, self).get_static_mention_suggestions()

        try:
            employee_group = self.env.ref('base.group_user')
            hr_suggestions = [{'id': user.partner_id.id, 'name': user.name, 'email': user.email} for user in employee_group.users]
            suggestions.append(hr_suggestions)
            return suggestions
        except AccessError:
            return suggestions

    def name_get(self):
        """ Override to allow an employee to see its private address in his profile.
            This avoids to relax access rules on `res.parter` and to add an `ir.rule`.
            (advantage in both security and performance).
            Use a try/except instead of systematically checking to minimize the impact on performance.
            """
        try:
            return super(Partner, self).name_get()
        except AccessError as e:
            if len(self) == 1 and self in self.env.user.employee_ids.mapped('address_home_id'):
                return super(Partner, self.sudo()).name_get()
            raise e
