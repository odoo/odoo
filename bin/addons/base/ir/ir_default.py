##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
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
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from osv import fields,osv

class ir_default(osv.osv):
    _name = 'ir.default'
    _columns = {
        'field_tbl': fields.char('Model',size=64),
        'field_name': fields.char('Model field',size=64),
        'value': fields.char('Default Value',size=64),
        'uid': fields.many2one('res.users', 'Users'),
        'page': fields.char('View',size=64),
        'ref_table': fields.char('Table Ref.',size=64),
        'ref_id': fields.integer('ID Ref.',size=64),
        'company_id': fields.many2one('res.company','Company')
    }

    def _get_company_id(self, cr, uid, context={}):
        res = self.pool.get('res.users').read(cr, uid, [uid], ['company_id'], context=context)
        if res and res[0]['company_id']:
            return res[0]['company_id'][0]
        return False

    _defaults = {
        'company_id': _get_company_id,
    }
ir_default()

