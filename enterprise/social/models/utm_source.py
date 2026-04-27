# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models

from odoo.exceptions import UserError


class UtmSource(models.Model):
    _inherit = 'utm.source'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_linked_social_posts(self):
        """ Already handled by ondelete='restrict', but let's show a nice error message """
        linked_social_posts = self.env['social.post'].sudo().search([
            ('source_id', 'in', self.ids)
        ])

        if linked_social_posts:
            raise UserError(_(
                "You cannot delete these UTM Sources as they are linked to social posts in "
                "Social:\n%(utm_sources)s",
                utm_sources=', '.join(['"%s"' % name for name in self.mapped('name')])))
