# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
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
from odoo import api, models


class IrModelAccess(models.Model):
    """Inherits the ir model access for restricting
     the user from accessing data."""
    _inherit = 'ir.model.access'

    @api.model
    def check(self, model, mode, raise_exception=True):
        """Overrides the default check method to allow
         only read access to the user."""
        res = super().check(model, mode, raise_exception=raise_exception)
        if self.env.user.has_group('odoo_readonly_user.group_users_readonly')\
                and mode in ('write', 'create', 'unlink'):
            return False
        return res
