# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Arshad Ali Pottengal (<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
from odoo import models


class WebsiteMenu(models.Model):
    """Inheriting the website menu"""
    _inherit = "website.menu"

    def _compute_visible(self):
        """Compute function for to  visible the menu based on the boolean
        field visibility"""
        super()._compute_visible()
        show_menu_header = self.env['ir.config_parameter'].sudo().get_param(
            'odoo_website_helpdesk.helpdesk_menu_show')
        for menu in self:
            if menu.name == 'Helpdesk' and not show_menu_header:
                menu.is_visible = False
            if menu.name == 'Helpdesk' and show_menu_header:
                menu.is_visible = True
