# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Dhanya Babu (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
from odoo import api, models
from odoo.osv import expression



class ResPartner(models.Model):
    """The ResPartner model is an inherited model of res.partner.
        This model extends the functionality of the res.partner model
        by adding a custom name search method _name_search(),
        which searches for partners by their name, phone number,
        or mobile number."""
    _inherit = 'res.partner'

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100,
                     name_get_uid=None):
        """search the phone number,mobile  and return to name_get ()
                Args:
                name (str) : The name to search for
                args (list) : Additional search arguments
                operator (str): The operator to use for the search (default is 'ilike')
                limit (int): The maximum number of records to return (default is 100)
                name_get_uid (int) : The UID of the user performing the search
                Returns:
                 list:The search results"""
        args = args or []
        domain = ['|', '|', '|', ('name', operator, name),
                      ('phone', operator, name), ('email', operator, name),
                      ('mobile', operator, name)]
        return self._search(expression.AND([domain + args]), limit=limit,
                            access_rights_uid=name_get_uid)
