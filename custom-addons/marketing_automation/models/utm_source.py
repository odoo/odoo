# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models

from odoo.exceptions import UserError


class UtmSource(models.Model):
    _inherit = 'utm.source'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_activities(self):
        """ Already handled by ondelete='restrict', but let's show a nice error message """
        linked_activities = self.env['marketing.activity'].sudo().search([
            ('source_id', 'in', self.ids)
        ])

        if linked_activities:
            raise UserError(_(
                "You cannot delete these UTM Sources as they are linked to the following marketing activities in "
                "Marketing Automation:\n%(activities_names)s",
                activities_names=', '.join(['"%s"' % name for name in linked_activities.mapped('name')])))
