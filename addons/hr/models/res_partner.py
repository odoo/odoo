# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from openerp.exceptions import AccessError


class Partner(models.Model):

    _inherit = ['res.partner']

    @api.model
    def get_static_mention_suggestions(self):
        """ Extend the mail's static mention suggestions by adding the employees. """
        suggestions = super(Partner, self).get_static_mention_suggestions()

        try:
            employee_group = self.env.ref('base.group_user')
            hr_suggestions = [{'id': user.partner_id.id, 'name': user.name, 'email': user.email}
                              for user in employee_group.users]
            suggestions.append(hr_suggestions)
            return suggestions
        except AccessError:
            return suggestions
