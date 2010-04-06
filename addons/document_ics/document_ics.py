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

from tools.translate import _
from document.nodes import node_content

from tools.safe_eval import safe_eval

ICS_TAGS = {
    'summary': 'normal',
    'uid': 'normal' ,
    'dtstart': 'date' ,
    'dtend': 'date' ,
    'created': 'date' ,
    'dtstamp': 'date' ,
    'last-modified': 'normal' ,
    'url': 'normal',
    'attendee': 'multiple',
    'location': 'normal',
    'categories': 'normal',
    'description': 'normal',

    # TODO: handle the 'duration' property
}

ICS_FUNCTIONS = [
    ('field', 'Use the field'),
    ('const', 'Expression as constant'),
    ('hours', 'Interval in hours'),
    ]

class document_directory_ics_fields(osv.osv):
    """ Document Directory ICS Fields """
    _name = 'document.directory.ics.fields'
    _description = 'Document Directory ICS Fields'
    _columns = {
        'field_id': fields.many2one('ir.model.fields', 'Open ERP Field'),
        'name': fields.selection(map(lambda x: (x, x), ICS_TAGS.keys()), 'ICS Value', required=True),
        'content_id': fields.many2one('document.directory.content', 'Content',\
                             required=True, ondelete='cascade'),
        'expr': fields.char("Expression", size=64),
        'fn': fields.selection(ICS_FUNCTIONS, 'Function', help="Alternate method \
                of calculating the value", required=True)
    }
    _defaults = {
        'fn': lambda *a: 'field',
    }

document_directory_ics_fields()

class document_directory_content(osv.osv):
    """ Document Directory Content """
    _inherit = 'document.directory.content'
    _description = 'Document Directory Content'
    __rege = re.compile(r'OpenERP-([\w|\.]+)_([0-9]+)@(\w+)$')

    _columns = {
        'object_id': fields.many2one('ir.model', 'Object', oldname= 'ics_object_id'),
        'obj_iterate': fields.boolean('Iterate object',help="If set, a separate \
                        instance will be created for each record of Object"),
        'fname_field': fields.char("Filename field",size=16,help="The field of the \
                        object used in the filename. Has to be a unique identifier."),
        'ics_domain': fields.char('Domain', size=64),
        'ics_field_ids': fields.one2many('document.directory.ics.fields', 'content_id', 'Fields Mapping')
    }
    _defaults = {
        'ics_domain': lambda *args: '[]'
    }

    def _file_get(self, cr, node, nodename, content, context=None):
        """  Get the file
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param node: pass the node
            @param nodename: pass the nodename
            @param context: A standard dictionary for contextual values
        """

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
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param node: pass the node
            @param data: pass the data
            @param context: A standard dictionary for contextual values
        """

        if node.extension != '.ics':
                return super(document_directory_content, self).process_write(cr, uid, node, data, context)
        import vobject
        parsedCal = vobject.readOne(data)
        fields = {}
        funcs = {}
        fexprs = {}
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
        for n in content.ics_field_ids:
            fields[n.name] = n.field_id.name and str(n.field_id.name)
            funcs[n.name] = n.fn
            fexprs[n.name] = n.expr

        if 'uid' not in fields:
            print "uid not in ", fields
            # FIXME: should pass
            return True
        for child in parsedCal.getChildren():
            result = {}
            uuid = None

            for event in child.getChildren():
                enl = event.name.lower()
                if enl =='uid':
                    uuid = event.value
                if not enl in fields:
                        # print "skip", enl
                        continue
                if fields[enl] and funcs[enl] == 'field':
                    if ICS_TAGS[enl]=='normal':
                        result[fields[enl]] = event.value.encode('utf8')
                    elif ICS_TAGS[enl]=='date':
                        result[fields[enl]] = event.value.strftime('%Y-%m-%d %H:%M:%S')

                    # print "Field ",enl,  result[fields[enl]]
                elif fields[enl] and funcs[enl] == 'hours':
                    ntag = fexprs[enl] or 'dtstart'
                    ts_start = child.getChildValue(ntag, default=False)
                    if not ts_start:
                        raise Exception("Cannot parse hours (for %s) without %s" % (enl, ntag))
                    ts_end = event.value
                    assert isinstance(ts_start, datetime.datetime)
                    assert isinstance(ts_end, datetime.datetime)
                    td = ts_end - ts_start
                    result[fields[enl]] = td.days * 24.0 + ( td.seconds / 3600.0)

                # put other functions here..
                else:
                    # print "Unhandled tag in ICS:", enl
                    pass
            # end for

            if not uuid:
                print "Skipping cal", child
                # FIXME: should pass
                continue

            cmodel = content.object_id.model
            wexpr = False
            if fields['uid']:
                wexpr = [(fields['uid'], '=', uuid.encode('utf8'))]
            else:
                # Parse back the uid from 'OpenERP-%s_%s@%s'
                wematch = self.__rege.match(uuid.encode('utf8'))
                # TODO: perhaps also add the domain to wexpr, restrict.
                if not wematch:
                    raise Exception("Cannot locate UID in %s" % uuid)
                if wematch.group(3) != cr.dbname:
                    raise Exception("Object is not for our db!")
                if content.object_id:
                    if wematch.group(1) != cmodel:
                        raise Exception("ICS must be at the wrong folder, this one is for %s" % cmodel)
                else:
                    # TODO: perhaps guess the model from the iCal, is it safe?
                    pass

                wexpr = [ ( 'id', '=', wematch.group(2) ) ]

            # print "Looking at ", cmodel, " for ", wexpr
            # print "domain=", idomain

            fobj = self.pool.get(content.object_id.model)

            if not wexpr:
                id = False
            else:
                id = fobj.search(cr, uid, wexpr, context=context)

            if isinstance(id, list):
                if len(id) > 1:
                    raise Exception("Multiple matches found for ICS")
            if id:
                fobj.write(cr, uid, id, result, context=context)
            else:
                r = idomain.copy()
                r.update(result)
                fobj.create(cr, uid, r, context=context)

        return True

    def process_read(self, cr, uid, node, context=None):
        """
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param node: pass the node
            @param context: A standard dictionary for contextual values
        """

        def ics_datetime(idate, short=False):
            if short:
                return datetime.date.fromtimestamp(time.mktime(time.strptime(idate, '%Y-%m-%d')))
            else:
                return datetime.datetime.strptime(idate, '%Y-%m-%d %H:%M:%S')

        if node.extension != '.ics':
            return super(document_directory_content, self).process_read(cr, uid, node, context)

        import vobject
        ctx = (context or {})
        ctx.update(node.context.context.copy())
        ctx.update(node.dctx)
        content = self.browse(cr, uid, node.cnt_id, ctx)
        if not content.object_id:
            return super(document_directory_content, self).process_read(cr, uid, node, context)
        obj_class = self.pool.get(content.object_id.model)

        if content.ics_domain:
            domain = safe_eval(content.ics_domain,ctx)
        else:
            domain = []
        if node.act_id:
            domain.append(('id','=',node.act_id))
        # print "process read clause:",domain
        ids = obj_class.search(cr, uid, domain, context=ctx)
        cal = vobject.iCalendar()
        for obj in obj_class.browse(cr, uid, ids):
            event = cal.add('vevent')
            # Fix dtstamp et last-modified with create and write date on the object line
            perm = obj_class.perm_read(cr, uid, [obj.id], context)
            event.add('created').value = ics_datetime(time.strftime('%Y-%m-%d %H:%M:%S'))
            event.add('dtstamp').value = ics_datetime(perm[0]['create_date'][:19])
            if perm[0]['write_date']:
                event.add('last-modified').value = ics_datetime(perm[0]['write_date'][:19])
            for field in content.ics_field_ids:
                if field.field_id.name:
                    value = getattr(obj, field.field_id.name)
                else: value = None
                if (not value) and field.name=='uid':
                    value = 'OpenERP-%s_%s@%s' % (content.object_id.model, str(obj.id), cr.dbname,)
                    # Why? obj_class.write(cr, uid, [obj.id], {field.field_id.name: value})
                if ICS_TAGS[field.name]=='normal':
                    if type(value)==type(obj):
                        value=value.name
                    event.add(field.name).value = tools.ustr(value) or ''
                elif ICS_TAGS[field.name]=='date' and value:
                    if field.name == 'dtstart':
                        date_start = start_date = datetime.datetime.fromtimestamp(time.mktime(time.strptime(value , "%Y-%m-%d %H:%M:%S")))
                    if field.name == 'dtend' and ( isinstance(value, float) or field.fn == 'hours'):
                        value = (start_date + datetime.timedelta(hours=value)).strftime('%Y-%m-%d %H:%M:%S')
                    if len(value)==10:
                        value = ics_datetime(value, True)
                    else:
                        value = ics_datetime(value)
                    event.add(field.name).value = value
        s = cal.serialize()
        return s
document_directory_content()

class crm_case(osv.osv):
    _inherit = 'crm.case'
    _columns = {
        'code': fields.char('Calendar Code', size=64),
        'date_deadline': fields.datetime('Deadline', help="Deadline Date is automatically\
                         computed from Start Date + Duration"),
    }

    _defaults = {
        'code': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'crm.case'),
    }

    def copy(self, cr, uid, id, default=None, context=None):
        """
            code field must be unique in ICS file
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param id: crm case's ID
            @param context: A standard dictionary for contextual values
        """

        if not default: default = {}
        if not context: context = {}
        default.update({'code': self.pool.get('ir.sequence').get(cr, uid, 'crm.case'), 'id': False})
        return super(crm_case, self).copy(cr, uid, id, default, context)

    def on_change_duration(self, cr, uid, id, date, duration):
        """ Change Duration
            @param self: The object pointer
            @param cr: the current row, from the database cursor,
            @param uid: the current user’s ID for security checks,
            @param id: crm case's ID,
            @param date: Pass the Date,
            @param duration: Pass the duration,
        """

        if not date:
            return {}
        start_date = datetime.datetime.fromtimestamp(time.mktime(time.strptime(date, "%Y-%m-%d %H:%M:%S")))
        if duration >= 0 :
            end = start_date + datetime.timedelta(hours=duration)
        if duration < 0:
            raise osv.except_osv(_('Warning !'),
                    _('You can not set negative Duration.'))

        res = {'value': {'date_deadline' : end.strftime('%Y-%m-%d %H:%M:%S')}}
        return res

crm_case()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

