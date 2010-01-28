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

from osv import fields,osv

class document_change_report(osv.osv):
    _name = "document.change.report"
    _description = "Process Changes Report"
    _auto = False
    def _amount_all(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for id in ids:
            dir, type = id.split(' ')
            att = self.pool.get('ir.attachment')
            fids = att.search(cr, uid, [('parent_id','child_of',[int(dir)]),('change_type_id','=',int(type))], context=context)
            res[id] = {
                'amount_required': 0,
                'amount_exist': 0,
                'amount_percent': 0.0
            }
            for f in att.browse(cr, uid, fids, context=context):
                res[id] = {
                    'amount_required': res[id]['amount_required'] + 1,
                    'amount_exist': res[id]['amount_exist'] + (f.state<>'draft') and 1 or 0,
                }
            if res[id]['amount_required']:
                res[id]['amount_percent'] = float(res[id]['amount_exist']*100) / res[id]['amount_required']
        return res

    _columns = {
        'directory_id': fields.many2one('document.directory', 'Directory', readonly=True),
        'change_type_id': fields.many2one('document.change.type', 'Document Type', readonly=True),
        'level': fields.integer('Level', readonly=True),
        'amount_required': fields.function(_amount_all, method=True,
            string='Required', multi='sums', type='integer'),
        'date': fields.date('Date', readonly=True),
        'amount_exist': fields.function(_amount_all, method=True,
            string='Existing', multi='sums', type='integer'),
        'amount_percent': fields.function(_amount_all, method=True,
            string='% Coverage', multi='sums', type='float', digits=(16,2)),
    }
    def init(self, cr):
        cr.execute("""
            create or replace view document_change_report as (
                select
                    d.id || ' ' || t.id as id,
                    d.id as directory_id,
                    d.level as level,
                    t.id as change_type_id
                from
                    document_directory d,
                    document_change_type t
            )""")
document_change_report()

