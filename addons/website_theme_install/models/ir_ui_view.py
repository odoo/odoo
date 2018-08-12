# coding: utf-8
from odoo import api, fields, models

class View(models.Model):
    _inherit = 'ir.ui.view'

    @api.model
    def _get_inheriting_views_arch_website(self, view_id):
        res = self.env['website'].get_current_website()

        # In certain cases view validation as done by
        # _validate_module_views will fail. When attempting to load
        # inherited view CHILD:
        #
        # PARENT (theme_common)
        #   ^
        #   |
        # CHILD  (other_theme)
        #
        # During the view validation no website_id will be in context
        # so the view will fail to apply, since PARENT won't be
        # selected by the inheriting view arch domain.
        #
        # This is not a problem however, CHILD will never be loaded on
        # a website where CHILD is not installed. To simulate this,
        # return a website which has the theme containing CHILD
        # installed.
        if res:
            return res
        else:
            view_theme = self.browse(view_id).theme_id
            if view_theme:
                return self.env['website'].search([('theme_ids', 'in', view_theme.id)], limit=1)
            else:
                return self.env['website']
