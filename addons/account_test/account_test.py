# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: product_expiry.py 4304 2006-10-25 09:54:51Z ged $
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
##############################################################################

from openerp.osv import fields,osv
import pooler
import netsvc
import time
from xml import dom


CODE_EXEC_DEFAULT = '''\
res = []
cr.execute("select id, code from account_journal")
for record in cr.dictfetchall():
    res.append(record['code'])
result = res
'''

class accounting_assert_test(osv.osv):
    _name = "accounting.assert.test"
    _order = "sequence"

    _columns = {
        'name': fields.char('Test Name', size=256, required=True, select=True, translate=True),
        'desc': fields.text('Test Description', select=True, translate=True),
        'code_exec': fields.text('Python code', required=True),
        'active': fields.boolean('Active'),
        'sequence': fields.integer('Sequence'),
    }

    _defaults = {
        'code_exec': CODE_EXEC_DEFAULT,
        'active': True,
        'sequence': 10,
    }

accounting_assert_test()

