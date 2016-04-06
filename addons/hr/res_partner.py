# -*- coding: utf-8 -*-

from openerp import api, models

class Partner(models.Model):
    _name = "res.partner"
    _inherit = ['res.partner']

    @api.model
    def get_static_mention_suggestions(self):
        """ Extend the mail's static mention suggestions by adding the employees. """
        suggestions = super(Partner, self).get_static_mention_suggestions()

        employee_group_id = self.env['ir.model.data'].xmlid_to_res_id('base.group_user')
        self._cr.execute("""
            SELECT P.id, P.name, P.email
            FROM res_users U
                INNER JOIN res_groups_users_rel R ON U.id = R.uid
                INNER JOIN res_partner P ON P.id = U.partner_id
            WHERE R.gid = %s AND U.active = 't'""", (employee_group_id,))
        suggestions.append(self._cr.dictfetchall())
        return suggestions
