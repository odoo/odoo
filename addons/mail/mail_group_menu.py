# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from osv import osv
from osv import fields
from tools.translate import _

class ir_ui_menu(osv.osv):
    _inherit = 'ir.ui.menu'
    _columns = {
        'mail_group_id': fields.many2one('mail.group', 'Mail Group')
    }
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        ids = super(ir_ui_menu, self).search(cr, uid, args, offset=0, limit=None, order=order, context=context, count=False)

        partner_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).partner_id.id
        subs = self.pool.get('mail.subscription')
        for menu in self.browse(cr, uid, ids, context=context):
            if menu.mail_group_id:
                sub_ids = subs.search(cr, uid, [
                    ('partner_id','=',partner_id),('res_model','=','mail.group'),
                    ('res_id','=',menu.mail_group_id.id)
                    ], context=context)
                if not sub_ids:
                    ids.remove(menu.id)
        return ids

