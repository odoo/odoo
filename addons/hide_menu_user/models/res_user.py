# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2021-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
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

from odoo import models, fields, api


class HideMenuUser(models.Model):
    _inherit = 'res.users'

    @api.model_create_multi
    def create(self, vals_list):
        """
        Else the menu will be still hidden even after removing from the list
        """
        self.clear_caches()
        return super(HideMenuUser, self).create(vals_list)

    def write(self, vals):
        """
        Else the menu will be still hidden even after removing from the list
        """
        res = super(HideMenuUser, self).write(vals)
        for record in self:
            for menu in record.hide_menu_ids:
                menu.write({
                    'restrict_user_ids': [(4, record.id)]
                })
        self.clear_caches()
        return res
    def _get_is_admin(self):
        """
        The Hide specific menu tab will be hidden for the Admin user form.
        Else once the menu is hidden, it will be difficult to re-enable it.
        """
        for rec in self:
            rec.is_admin = False
            if rec.id == self.env.ref('base.user_admin').id:
                rec.is_admin = True

    hide_menu_ids = fields.Many2many('ir.ui.menu', string="Menu", store=True,
                                     help='Select menu items that needs to be '
                                          'hidden to this user ')
    is_admin = fields.Boolean(compute=_get_is_admin, string="Admin")


class RestrictMenu(models.Model):
    _inherit = 'ir.ui.menu'

    restrict_user_ids = fields.Many2many('res.users')
