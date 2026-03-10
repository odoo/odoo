# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
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
#############################################################################
from odoo import api, fields, models


class Settings(models.TransientModel):
    """Inheriting config settings to add menu order management"""
    _inherit = 'res.config.settings'

    order_menu = fields.Boolean(default=False, string='Order Menu Alphabets',
                                help="Order the menus in alphabetic order")

    @api.model
    def get_values(self):
        """ Get values for fields in the settings
         and assign the value to the fields"""
        res = super(Settings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        order_menu = params.get_param('order_menu', default=False)
        res.update(
            order_menu=order_menu,
        )
        return res

    def set_values(self):
        """ save values in  the settings fields"""
        super(Settings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            "order_menu", self.order_menu)

    @api.onchange('order_menu')
    def onchange_order_menu(self):
        """Change order of menus"""
        asc_order_menu = self.env['ir.config_parameter'].sudo().get_param(
            'order_menu') or False
        sqno = 1
        if asc_order_menu:
            menus = self.env['ir.ui.menu'].sudo().search(
                ['&', ('parent_id', '=', False), (
                    'name', 'not in', ('Apps', 'Settings', 'Dashboard'))])
            for menu in menus:
                if not menu.order_changed:
                    menu.recent_menu_sequence = menu.sequence
                    menu.sequence = sqno
                    menu.order_changed = True
                    sqno += 1
        else:
            menus = self.env['ir.ui.menu'].search(
                [('parent_id', '=', False), ('name', 'not in', (
                    'Apps', 'Settings', 'Dashboard'))])
            for menu in menus:
                if menu.order_changed:
                    menu.sequence = menu.recent_menu_sequence
                    menu.recent_menu_sequence = 0
                    menu.order_changed = False
        return False
