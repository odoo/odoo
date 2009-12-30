# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

from osv import osv, fields
from osv.orm import except_orm
import os
import StringIO
import base64
import datetime
import time
import random
import tools
import re

from document.nodes import node_content

from tools.safe_eval import safe_eval

ICS_TAGS = {
    'summary':'normal',
    'uid':'normal' ,
    'dtstart':'date' ,
    'dtend':'date' ,
    'created':'date' ,
    'dtstamp':'date' ,
    'last-modified':'normal' ,
    'url':'normal' ,
    'attendee':'multiple',
    'location':'normal',
    'categories': 'normal',
    'description':'normal',

    # TODO: handle the 'duration' property
}

ICS_FUNCTIONS = [
    ('field', 'Use the field'),
    ('const', 'Expression as constant'),
    ('hours', 'Interval in hours'),
    ]

class document_directory_ics_fields(osv.osv):
    _name = 'document.directory.ics.fields'
    _columns = {
        'field_id': fields.many2one('ir.model.fields', 'Open ERP Field'),
        'name': fields.selection(map(lambda x: (x, x), ICS_TAGS.keys()), 'ICS Value', required=True),
        'content_id': fields.many2one('document.directory.content', 'Content', required=True, ondelete='cascade'),
        'expr': fields.char("Expression", size=64),
        'fn': fields.selection(ICS_FUNCTIONS,'Function',help="Alternate method of calculating the value", required=True)
    }
    _defaults = {
        'fn': lambda *a: 'field',
    }
   
document_directory_ics_fields()

class document_directory_content(osv.osv):
    _inherit = 'document.directory.content'
    __rege = re.compile(r'OpenERP-([\w|\.]+)_([0-9]+)@(\w+)$')
    _columns = {
        'object_id': fields.many2one('ir.model', 'Object', oldname= 'ics_object_id'),
        'obj_iterate': fields.boolean('Iterate object',help="If set, a separate instance will be created for each record of Object"),
        'fname_field': fields.char("Filename field",size=16,help="The field of the object used in the filename. Has to be a unique identifier."),
        'ics_domain': fields.char('Domain', size=64),
        #'ics_field_ids': fields.one2many('document.directory.ics.fields', 'content_id', 'Fields Mapping')
    }
    _defaults = {
        'ics_domain': lambda *args: '[]'
    }
    def _file_get(self, cr, node, nodename, content, context=None):
        if not content.obj_iterate:
            return super(document_directory_content, self)._file_get(cr, node, nodename, content)
        else:
            if not content.object_id:
                return False
            mod = self.pool.get(content.object_id.model)
            uid = node.context.uid
            fname_fld = content.fname_field or 'id'
            where = []            
            if node.domain:
                where += eval(node.domain)
            if nodename:
                # Reverse-parse the nodename to deduce the clause:
                prefix = (content.prefix or '')
                suffix = (content.suffix or '') + (content.extension or '')
                if not nodename.startswith(prefix):
                    return False
                if not nodename.endswith(suffix):
                    return False
                tval = nodename[len(prefix):0 - len(suffix)]
                where.append((fname_fld,'=',tval))
            # print "ics iterate clause:", where
            resids = mod.search(cr, uid, where, context=context)
            if not resids:
                return False
        
            res2 = []
            for ro in mod.read(cr,uid,resids,['id', fname_fld]):
                tname = (content.prefix or '') + str(ro[fname_fld])
                tname += (content.suffix or '') + (content.extension or '')
                dctx2 = { 'active_id': ro['id'] }
                if fname_fld:
                    dctx2['active_'+fname_fld] = ro[fname_fld]
                n = node_content(tname, node, node.context,content,dctx=dctx2, act_id = ro['id'])
                n.fill_fields(cr, dctx2)
                res2.append(n)
            return res2

    def process_write(self, cr, uid, node, data, context=None):
        if node.extension != '.ics':
                return super(document_directory_content, self).process_write(cr, uid, node, data, context)
        content = self.browse(cr, uid, node.cnt_id, context)

        idomain = {}
        ctx = (context or {})
        ctx.update(node.context.context.copy())
        ctx.update(node.dctx)
        # print "ICS domain: ", type(content.ics_domain), content.ics_domain
        if content.ics_domain:
            for d in safe_eval(content.ics_domain,ctx):
                # TODO: operator?
                idomain[d[0]]=d[2]

        fobj = self.pool.get(content.object_id.model)
        fobj.import_cal(cr, uid, base64.encodestring(data), context=context)        
        return True

    def process_read(self, cr, uid, node, context=None):
        ctx = (context or {})
        ctx.update(node.context.context.copy())
        ctx.update(node.dctx)
        content = self.browse(cr, uid, node.cnt_id, ctx)
        obj_class = self.pool.get(content.object_id.model)
#
        if content.ics_domain:
            domain = safe_eval(content.ics_domain,ctx)
        else:
            domain = []
        if node.act_id:
            domain.append(('id','=',node.act_id))
        # print "process read clause:",domain
        ids = obj_class.search(cr, uid, domain, context=ctx)
        context.update({'model': content.object_id.model})
        s = obj_class.export_cal(cr, uid, ids, context=context)
        return s
document_directory_content()

class crm_case(osv.osv):
    _inherit = 'crm.case'
    _columns = {
        'code': fields.char('Calendar Code', size=64),
        'date_deadline': fields.datetime('Deadline', help="Deadline Date is automatically computed from Start Date + Duration"),
    }

    _defaults = {
        'code': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'crm.case'),
    }

    def copy(self, cr, uid, id, default=None, context=None):
        """
        code field must be unique in ICS file
        """
        if not default: default = {}
        if not context: context = {}
        default.update({'code': self.pool.get('ir.sequence').get(cr, uid, 'crm.case'), 'id': False})
        return super(crm_case, self).copy(cr, uid, id, default, context)

    def on_change_duration(self, cr, uid, id, date, duration):
        if not date:
            return {}
        start_date = datetime.datetime.fromtimestamp(time.mktime(time.strptime(date, "%Y-%m-%d %H:%M:%S")))
        if duration >= 0 :
            end = start_date + datetime.timedelta(hours=duration)
        if duration < 0:
            raise osv.except_osv(_('Warning !'),
                    _('You can not set negative Duration.'))

        res = {'value' : {'date_deadline' : end.strftime('%Y-%m-%d %H:%M:%S')}}
        return res

crm_case()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

