# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
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
from ast import literal_eval
from odoo import fields, models, _
from odoo.tools.misc import ustr
from odoo.addons.auth_signup.models.res_partner import SignupError, now


class ResUsers(models.Model):
    """ Added shop information and user creation from website"""
    _inherit = 'res.users'

    profile_url = fields.Integer(string='Shop Url', help='Shop url')

    def _create_user_from_template(self, values):
        """ Creating user through the website"""
        if values['profile_url'] != 0:
            template_user_id = self.env.ref(
                'multi_vendor_marketplace.template_seller_user').id
        else:
            template_user_id = literal_eval(
                self.env['ir.config_parameter'].sudo().get_param(
                    'base.template_portal_user_id', 'False'))
        template_user = self.browse(template_user_id)
        if not template_user.exists():
            raise ValueError(_('Signup: invalid template user'))
        if not values.get('login'):
            raise ValueError(_('Signup: no login given for new user'))
        if not values.get('partner_id') and not values.get('name'):
            raise ValueError(
                _('Signup: no name or partner given for new user'))
        values['active'] = True
        try:
            with self.env.cr.savepoint():
                return template_user.with_context(no_reset_password=True).copy(
                    values)
        except Exception as e:
            raise SignupError(ustr(e))
