# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class WebsiteMenu(models.Model):
    _inherit = "website.menu"

    def _compute_visible(self):
        """ Display helpdesk team menus even if they are unpublished """
        helpdesk_menus = self.filtered(lambda menu: menu.url and menu.url[:9] == "/helpdesk")
        if helpdesk_menus.user_has_groups('base.group_user'): # avoid extra query if not needed
            helpdesk_menus.is_visible = True
            return super(WebsiteMenu, self - helpdesk_menus)._compute_visible()
        published_menus, = self.env['helpdesk.team']._read_group(
            [('is_published', '=', True), ('website_menu_id', '!=', False)],
            [], ['website_menu_id:recordset']
        )[0]
        for menu in helpdesk_menus:
            menu.is_visible = menu in published_menus
        return super(WebsiteMenu, self - helpdesk_menus)._compute_visible()
