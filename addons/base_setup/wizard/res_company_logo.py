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

from osv import fields, osv
import os
import tools
from tools.translate import _


class res_company_logo(osv.osv_memory):
    _name = 'res.company.logo'
    _inherit = 'res.config'
    _columns = {
        'logo' : fields.binary('Logo'),
    }
    _defaults={
               'logo':lambda self,cr,uid,c: self.pool.get('res.company').browse(cr, uid, uid,c).logo,
     }

    def execute(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        user_comp = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
        get_val = self.browse(cr, uid, ids)[0]
        user_comp.write({'logo': get_val.logo}, context=context)
        return {'type': 'ir.actions.act_window_close'}
    
res_company_logo()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

