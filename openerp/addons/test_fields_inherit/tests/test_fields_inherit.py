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

import openerp.tests.common as common


class test_field_inherit(common.TransactionCase):

    def setUp(self):
        super(test_field_inherit, self).setUp()
        self.context = self.registry("res.users").context_get(self.cr,
                                                              self.uid)

    def test_field_inherit_property_to_function_many2one(self):
        default_account_id = self.ref('account.a_sale')
        test_model = self.registry('fields.inherit.test')
        res_id = test_model.create(self.cr, self.uid, {'name': 'Test'})
        res = test_model.browse(self.cr, self.uid, [res_id])[0]
        # Here, property_to_function_many2one field should be calculated
        # and it should only have a single value
        self.assertEqual(len(res.property_to_function_many2one.ids), 1,
                         "No account defined")
        # Here, we check that the value on property_to_function_many2one field
        # is equal to default_account_id.
        self.assertEqual(len(res.property_to_function_many2one.ids[0]),
                         default_account_id,
                         "Account isn't correct")
