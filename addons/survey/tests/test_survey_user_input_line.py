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

from openerp.tests import common as common


class TestSurveyUserInputLine(common.TransactionCase):

    _module_ns = 'survey'

    def setUp(self):
        super(TestSurveyUserInputLine, self).setUp()

    def test_copy_data_user_input_line(self):
        cr, uid, context = self.cr, self.uid, {}
        user_input_line_id = self.ref('%s.uil_13' % self._module_ns)
        user_input_line_obj = self.registry['survey.user_input_line']
        default = {}
        with self.assertRaises(Warning):
            user_input_line_obj.copy(
                cr, uid, user_input_line_id, default=default, context=context)
