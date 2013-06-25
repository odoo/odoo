# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2013-TODAY OpenERP S.A. <http://openerp.com>
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

from openerp.tests import common


class TestIdeaBase(common.TransactionCase):

    def setUp(self):
        super(TestIdeaBase, self).setUp()
        cr, uid = self.cr, self.uid

        # Usefull models
        self.idea_category = self.registry('idea.category')
        self.idea_idea = self.registry('idea.idea')

    def tearDown(self):
        super(TestIdeaBase, self).tearDown()

    def test_OO(self):
        pass
