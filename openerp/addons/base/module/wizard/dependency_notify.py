# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2004-2012 OpenERP S.A. <http://openerp.com>
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

from openerp.osv import fields,osv

class dependency_notify(osv.osv_memory):
    _name = 'dependency.notify'
    _description = 'Notify dependency'
    _rec_name = 'message'

    _columns = {
        'message': fields.text('Message'),
    }

    def uninstall_all(self, cr, uid, ids, context=None):
        module_pool = self.pool.get('ir.module.module')
        print context
        return module_pool.button_immediate_uninstall_final(
            cr, uid, context['active_ids'], context=context)



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
