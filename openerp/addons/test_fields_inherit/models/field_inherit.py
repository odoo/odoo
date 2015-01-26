# -*- coding: utf-8 -*-
#
##############################################################################
#
#     Authors: Adrien Peiffer
#    Copyright (c) 2015 Acsone SA/NV (http://www.acsone.eu)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import orm, fields


class fields_inherit_test(orm.Model):
    """ This model use a many2one property field """

    _name = 'fields.inherit.test'

    _columns = {'name': fields.char(string='Name', required=True),
                'property_to_function_many2one': fields.property(
                type='many2one',
                relation='account.account',
                string='property_to_function_many2one')
                }


class fields_inherit_test(orm.Model):
    """Here, there is an inheritance from fields.inherit.test model.
    The goal of this inheritance is to overload the many2one property fields
    previously defined to make a many2one function field"""

    _inherit = 'fields.inherit.test'

    def _get_value(self, cr, uid, ids, name, arg, context=None):
        """This method aims to return a default account value at the
        computation of the inherited field(new type function) with an xml id.
        if this id doesn't exist an exception is raised"""

        res = {}
        default_account_id = self.pool['ir.model.data']\
            .xmlid_to_res_id(cr, uid, 'account.a_sale',
                             raise_if_not_found=True)
        for product in self.browse(cr, uid, ids, context=context):
            res[product.id] = default_account_id
        return res

    _columns = {'property_to_function_many2one': fields
                .function(_get_value, type='many2one',
                          string='property_to_function_many2one'),
                }
