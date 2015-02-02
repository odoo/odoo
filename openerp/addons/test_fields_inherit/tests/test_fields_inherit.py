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
        self.context = self.env["res.users"].context_get()

    def test_field_inherit_property_to_function_many2one(self):
        default_account_id = self.env.ref('account.a_sale')
        test_model = self.env['fields.inherit.test']
        res = test_model.create({'name': 'Test'})
        # Here, we check that the value on property_to_function_many2one field
        # is equal to default_account_id.
        self.assertEqual(res.property_to_function_many2one,
                         default_account_id,
                         "Account isn't correct")

    def test_field_inherit_property_to_function_many2one_new_api(self):
        default_account_id = self.env.ref('account.a_sale')
        test_model = self.env['fields.inherit.test']
        res = test_model.create({'name': 'Test'})
        # Here, we check that the value on property_to_function_many2one
        # new_api field is equal to default_account_id.
        self.assertEqual(res.property_to_function_many2one_new_api,
                         default_account_id,
                         "Account isn't correct")

    def test_field_inherit_function_float(self):
        test_model = self.env['fields.inherit.test']
        res = test_model.create({'name': 'Test'})
        # Here, we check that the value on property_to_function_float_new_api
        # field is equal to 2.0.
        self.assertAlmostEqual(res.property_to_function_float_new_api, 2.0, 2,
                               "Float Value isn't correct")
