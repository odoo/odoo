# -*- coding: utf-8 -*-

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
            for user in employee_group.users:
                suggestions.append((user.partner_id.id, user.name, user.email)) 
            return suggestions
        except AccessError:
            return suggestions
