# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models

from odoo.exceptions import UserError


class UtmSource(models.Model):
    _inherit = 'utm.source'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_users(self):
        """ Already handled by ondelete='restrict', but let's show a nice error message """
        linked_users = self.env['res.users'].sudo().search([
            ('utm_source_id', 'in', self.ids)
        ])

        if linked_users:
            raise UserError(_(
                "You cannot delete these UTM Sources as they are linked to the following users in "
                "Referral:\n%(employee_names)s",
                employee_names=', '.join(['"%s"' % name for name in linked_users.mapped('name')])))
