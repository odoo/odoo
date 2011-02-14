# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from osv import fields,osv,orm
from tools.translate import _


class synchronize_base(osv.osv_memory):
    _description ='Synchronize Contact'
    _name = "synchronize.base"
    _columns = {
        'tools':  fields.selection([('none','Nothing')], 'App to synchronize with'),
     }
    def action_synchronize(self, cr, uid, ids, context=None):
         return {}
synchronize_base()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
