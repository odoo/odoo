# -*- coding: utf-8 -*-
##############################################################################
#
#     This file is part of survey, an Odoo module.
#
#     Copyright (c) 2015 ACSONE SA/NV (<http://acsone.eu>)
#
#     survey is free software: you can redistribute it and/or
#     modify it under the terms of the GNU Affero General Public License
#     as published by the Free Software Foundation, either version 3 of
#     the License, or (at your option) any later version.
#
#     survey is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU Affero General Public License for more details.
#
#     You should have received a copy of the
#     GNU Affero General Public License
#     along with survey.
#     If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from uuid import uuid4

from openerp import fields
from openerp.tests import common as common
from openerp.osv import osv


class TestSurveyUserInput(common.TransactionCase):

    _module_ns = 'survey'

    def setUp(self):
        super(TestSurveyUserInput, self).setUp()

    def test_copy_data_user_input(self):
        cr, uid, context = self.cr, self.uid, {}
        user_input_id = self.ref('%s.ui3' % self._module_ns)
        user_input_obj = self.registry['survey.user_input']
        token = uuid4().__str__()
        default = {
            'date_create': fields.datetime.now(),
            'state': 'skip',
            'token': token,
            'deadline': False,
        }
        self.assertRaises(
            osv.except_osv, user_input_obj.copy_data, cr, uid, user_input_id,
            default=default, context=context)
        context['allow_copy'] = True
        user_input_copy_values = user_input_obj.copy_data(
            cr, uid, user_input_id, default=default,
            context=context)
        self.assertEquals(
            token, user_input_copy_values['token'],
            'Token should be the same')
