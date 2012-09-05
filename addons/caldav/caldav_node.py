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

from document_webdav import nodes
from document.nodes import _str2time, nodefd_static
import logging
from orm_utils import get_last_modified
_logger = logging.getLogger(__name__)

try:
    from tools.dict_tools import  dict_merge2
except ImportError:
    from document.dict_tools import  dict_merge2

# TODO: implement DAV-aware errors, inherit from IOError

# Assuming that we have set global properties right, we mark *all* 
# directories as having calendar-access.
nodes.node_dir.http_options = dict_merge2(nodes.node_dir.http_options,
            { 'DAV': ['calendar-access',] })

class node_calendar_collection(nodes.node_dir):
    DAV_PROPS = dict_merge2(nodes.node_dir.DAV_PROPS,
            { "http://calendarserver.org/ns/" : ('getctag',), } )
    DAV_M_NS = dict_merge2(nodes.node_dir.DAV_M_NS,
            { "http://calendarserver.org/ns/" : '_get_dav', } )

    def _file_get(self,cr, nodename=False):
        return []

    def _child_get(self, cr, name=False, parent_id=False, domain=None):
        dirobj = self.context._dirobj
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        where = [('collection_id','=',self.dir_id)]
        ext = False
        if name and name.endswith('.ics'):
            name = name[:-4]
            ext = True
        if name:
            where.append(('name','=',name))
        if not domain:
            domain = []
        where = where + domain
        fil_obj = dirobj.pool.get('basic.calendar')
        ids = fil_obj.search(cr,uid,where,context=ctx)
        res = []
        for cal in fil_obj.browse(cr, uid, ids, context=ctx):
            if (not name) or not ext:
                res.append(node_calendar(cal.name, self, self.context, cal))
            if self.context.get('DAV-client', '') in ('iPhone', 'iCalendar'):
                # these ones must not see the webcal entry.
                continue
            if cal.has_webcal and (not name) or ext:
                res.append(res_node_calendar(cal.name+'.ics', self, self.context, cal))
            # May be both of them!
        return res

    def _get_ttag(self, cr):
        return 'calen-dir-%d' % self.dir_id

    def _get_dav_getctag(self, cr):
        dirobj = self.context._dirobj
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        where = [('collection_id','=',self.dir_id)]
        bc_obj = dirobj.pool.get('basic.calendar')
        
        res = get_last_modified(bc_obj, cr, uid, where, context=ctx)
        return _str2time(res)

class node_calendar_res_col(nodes.node_res_obj):
    """ Calendar collection, as a dynamically created node
    
    This class shall be used instead of node_calendar_collection, when the
    node is under dynamic ones.
    """
    DAV_PROPS = dict_merge2(nodes.node_res_obj.DAV_PROPS,
            { "http://calendarserver.org/ns/" : ('getctag',), } )
    DAV_M_NS = dict_merge2(nodes.node_res_obj.DAV_M_NS,
            { "http://calendarserver.org/ns/" : '_get_dav', } )

    def _file_get(self,cr, nodename=False):
        return []

    def _child_get(self, cr, name=False, parent_id=False, domain=None):
        dirobj = self.context._dirobj
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        where = [('collection_id','=',self.dir_id)]
        ext = False
        if name and name.endswith('.ics'):
            name = name[:-4]
            ext = True
        if name:
            where.append(('name','=',name))
        if not domain:
            domain = []
        where = where + domain
        fil_obj = dirobj.pool.get('basic.calendar')
        ids = fil_obj.search(cr,uid,where,context=ctx)
        res = []
        # TODO: shall we use any of our dynamic information??
        for cal in fil_obj.browse(cr, uid, ids, context=ctx):
            if (not name) or not ext:
                res.append(node_calendar(cal.name, self, self.context, cal))
            if self.context.get('DAV-client', '') in ('iPhone', 'iCalendar'):
                # these ones must not see the webcal entry.
                continue
            if cal.has_webcal and (not name) or ext:
                res.append(res_node_calendar(cal.name+'.ics', self, self.context, cal))
            # May be both of them!
        return res

    def _get_ttag(self, cr):
        return 'calen-dir-%d' % self.dir_id

    def _get_dav_getctag(self, cr):
        dirobj = self.context._dirobj
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        where = [('collection_id','=',self.dir_id)]
        bc_obj = dirobj.pool.get('basic.calendar')
        
        res = get_last_modified(bc_obj, cr, uid, where, context=ctx)
        return _str2time(res)

class node_calendar(nodes.node_class):
    our_type = 'collection'
    DAV_PROPS = {
            "DAV:": ('supported-report-set',),
            # "http://cal.me.com/_namespace/" : ('user-state',),
            "http://calendarserver.org/ns/" : ( 'getctag',),
            'http://groupdav.org/': ('resourcetype',),
            "urn:ietf:params:xml:ns:caldav" : (
                    'calendar-description', 
                    'supported-calendar-component-set',
                    ),
            "http://apple.com/ns/ical/": ("calendar-color", "calendar-order"),
            }
    DAV_PROPS_HIDDEN = {
            "urn:ietf:params:xml:ns:caldav" : (
                    'calendar-data',
                    'calendar-timezone',
                    'supported-calendar-data',
                    'max-resource-size',
                    'min-date-time',
                    'max-date-time',
                    )}

    DAV_M_NS = {
           "DAV:" : '_get_dav',
           # "http://cal.me.com/_namespace/": '_get_dav', 
           'http://groupdav.org/': '_get_gdav',
           "http://calendarserver.org/ns/" : '_get_dav',
           "urn:ietf:params:xml:ns:caldav" : '_get_caldav',
           "http://apple.com/ns/ical/": '_get_apple_cal',
           }

    http_options = { 'DAV': ['calendar-access'] }

    def __init__(self,path, parent, context, calendar):
        super(node_calendar,self).__init__(path, parent,context)
        self.calendar_id = calendar.id
        self.mimetype = 'application/x-directory'
        self.create_date = calendar.create_date
        self.write_date = calendar.write_date or calendar.create_date
        self.content_length = 0
        self.displayname = calendar.name
        self.cal_type = calendar.type
        self.cal_color = calendar.calendar_color or None
        self.cal_order = calendar.calendar_order or None
        try:
            self.uuser = (calendar.user_id and calendar.user_id.login) or 'nobody'
        except Exception:
            self.uuser = 'nobody'

    def _get_dav_getctag(self, cr):
        dirobj = self.context._dirobj
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)

        bc_obj = dirobj.pool.get('basic.calendar')
        res = bc_obj.get_cal_max_modified(cr, uid, [self.calendar_id], self, domain=[], context=ctx)
        return _str2time(res)

    def _get_dav_user_state(self, cr):
        #TODO
        return 'online'

    def get_dav_resourcetype(self, cr):
        res = [ ('collection', 'DAV:'),
                ('calendar', 'urn:ietf:params:xml:ns:caldav'),
                ]
        if self.context.get('DAV-client', '') == 'GroupDAV':
            res.append((str(self.cal_type + '-collection'), 'http://groupdav.org/'))
        return res

    def get_domain(self, cr, filters):
        # TODO: doc.
        res = []
        if not filters:
            return res
        if filters.localName == 'calendar-query':
            res = []
            for filter_child in filters.childNodes:
                if filter_child.nodeType == filter_child.TEXT_NODE:
                    continue
                if filter_child.localName == 'filter':
                    for vcalendar_filter in filter_child.childNodes:
                        if vcalendar_filter.nodeType == vcalendar_filter.TEXT_NODE:
                            continue
                        if vcalendar_filter.localName == 'comp-filter':
                            if vcalendar_filter.getAttribute('name') == 'VCALENDAR':
                                for vevent_filter in vcalendar_filter.childNodes:
                                    if vevent_filter.nodeType == vevent_filter.TEXT_NODE:
                                        continue
                                    if vevent_filter.localName == 'comp-filter':
                                        if vevent_filter.getAttribute('name'):
                                            res = [('type','=',vevent_filter.getAttribute('name').lower() )]
                                            
                                        for cfe in vevent_filter.childNodes:
                                            if cfe.localName == 'time-range':
                                                if cfe.getAttribute('start'):
                                                    _log.warning("Ignore start.. ")
                                                    # No, it won't work in this API
                                                    #val = cfe.getAttribute('start')
                                                    #res += [('dtstart','=', cfe)]
                                                elif cfe.getAttribute('end'):
                                                    _log.warning("Ignore end.. ")
                                            else:
                                                _log.debug("Unknown comp-filter: %s.", cfe.localName)
                                    else:
                                        _log.debug("Unknown comp-filter: %s.", vevent_filter.localName)
                        else:
                            _log.debug("Unknown filter element: %s.", vcalendar_filter.localName)
                else:
                    _log.debug("Unknown calendar-query element: %s.", filter_child.localName)
            return res
        elif filters.localName == 'calendar-multiget':
            # this is not the place to process, as it wouldn't support multi-level
            # hrefs. So, the code is moved to document_webdav/dav_fs.py
            pass
        else:
            _log.debug("Unknown element in REPORT: %s.", filters.localName)
        return res

    def children(self, cr, domain=None):
        return self._child_get(cr, domain=domain)

    def child(self,cr, name, domain=None):
        res = self._child_get(cr, name, domain=domain)
        if res:
            return res[0]
        return None


    def _child_get(self, cr, name=False, parent_id=False, domain=None):
        dirobj = self.context._dirobj
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        where = []
        bc_obj = dirobj.pool.get('basic.calendar')

        if name:
            if name.endswith('.ics'):
                name = name[:-4]
            try:
                if name.isdigit():
                    where.append(('id','=',int(name)))
                else:
                    bca_obj = dirobj.pool.get('basic.calendar.alias')
                    bc_alias = bca_obj.search(cr, uid, 
                        [('cal_line_id.calendar_id', '=', self.calendar_id),
                         ('name', '=', name)] )
                    if not bc_alias:
                        return []
                    bc_val = bca_obj.read(cr, uid, bc_alias, ['res_id',])
                    where.append(('id', '=', bc_val[0]['res_id']))
            except ValueError:
                # if somebody requests any other name than the ones we
                # generate (non-numeric), it just won't exist
                return []

        if not domain:
            domain = []

        # we /could/ be supplying an invalid calendar id to bc_obj, it has to check
        res = bc_obj.get_calendar_objects(cr, uid, [self.calendar_id], self, domain=where, context=ctx)
        return res

    def create_child(self, cr, path, data):
        """ API function to create a child file object and node
            Return the node_* created
        """
        # we ignore the path, it will be re-generated automatically
        fil_obj = self.context._dirobj.pool.get('basic.calendar')
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        uid = self.context.uid

        res = self.set_data(cr, data)
        if res and len(res):
            # We arbitrarily construct only the first node of the data
            # that have been imported. ICS may have had more elements,
            # but only one node can be returned here.
            assert isinstance(res[0], (int, long))
            fnodes = fil_obj.get_calendar_objects(cr, uid, [self.calendar_id], self,
                    domain=[('id','=',res[0])], context=ctx)
            
            if self.context.get('DAV-client','') in ('iPhone', 'iCalendar',):
                # For those buggy clients, register the alias
                bca_obj = fil_obj.pool.get('basic.calendar.alias')
                ourcal = fil_obj.browse(cr, uid, self.calendar_id)
                line_id = None
                for line in ourcal.line_ids:
                    if line.name == ourcal.type:
                        line_id = line.id
                        break
                assert line_id, "Calendar #%d must have at least one %s line." % \
                                    (ourcal.id, ourcal.type)
                if path.endswith('.ics'):
                    path = path[:-4]
                bca_obj.create(cr, uid, { 'cal_line_id': line_id, 
                                    'res_id': res[0], 'name': path}, context=ctx)
            return fnodes[0]
        # If we reach this line, it means that we couldn't import any useful
        # (and matching type vs. our node kind) data from the iCal content.
        return None


    def set_data(self, cr, data, fil_obj = None):
        uid = self.context.uid
        calendar_obj = self.context._dirobj.pool.get('basic.calendar')
        res = calendar_obj.import_cal(cr, uid, data, self.calendar_id)
        return res

    def get_data_len(self, cr, fil_obj = None):
        return self.content_length

    def _get_ttag(self,cr):
        return 'calendar-%d' % (self.calendar_id,)

    def rmcol(self, cr):
        return False

    def _get_caldav_calendar_data(self, cr):
        if self.context.get('DAV-client', '') in ('iPhone', 'iCalendar'):
            # Never return collective data to iClients, they get confused
            # because they do propfind on the calendar node with Depth=1
            # and only expect the childrens' data
            return None
        res = []
        for child in self.children(cr):
            res.append(child._get_caldav_calendar_data(cr))
        return res

    def open_data(self, cr, mode):
        return nodefd_static(self, cr, mode)

    def _get_caldav_calendar_description(self, cr):
        uid = self.context.uid
        calendar_obj = self.context._dirobj.pool.get('basic.calendar')
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        try:
            calendar = calendar_obj.browse(cr, uid, self.calendar_id, context=ctx)
            return calendar.description or calendar.name
        except Exception:
            return None

    def _get_dav_supported_report_set(self, cr):
        
        return ('supported-report', 'DAV:', 
                    ('report','DAV:',
                            ('principal-match','DAV:')
                    )
                )

    def _get_caldav_supported_calendar_component_set(self, cr):
        return ('comp', 'urn:ietf:params:xml:ns:caldav', None,
                    {'name': self.cal_type.upper()} )
        
    def _get_caldav_calendar_timezone(self, cr):
        return None #TODO
        
    def _get_caldav_supported_calendar_data(self, cr):
        return ('calendar-data', 'urn:ietf:params:xml:ns:caldav', None,
                    {'content-type': "text/calendar", 'version': "2.0" } )
        
    def _get_caldav_max_resource_size(self, cr):
        return 65535

    def _get_caldav_min_date_time(self, cr):
        return "19700101T000000Z"

    def _get_caldav_max_date_time(self, cr):
        return "21001231T235959Z" # I will be dead by then
    
    def _get_apple_cal_calendar_color(self, cr):
        return self.cal_color

    def _get_apple_cal_calendar_order(self, cr):
        return self.cal_order

class res_node_calendar(nodes.node_class):
    our_type = 'file'
    DAV_PROPS = {
            "http://calendarserver.org/ns/" : ('getctag',),
            "urn:ietf:params:xml:ns:caldav" : (
                    'calendar-description',
                    'calendar-data',
                    )}
    DAV_M_NS = {
           "http://calendarserver.org/ns/" : '_get_dav',
           "urn:ietf:params:xml:ns:caldav" : '_get_caldav'}

    http_options = { 'DAV': ['calendar-access'] }

    def __init__(self,path, parent, context, res_obj, res_model=None, res_id=None):
        super(res_node_calendar,self).__init__(path, parent, context)
        self.mimetype = 'text/calendar'
        self.create_date = parent.create_date
        self.write_date = parent.write_date or parent.create_date
        self.calendar_id = hasattr(parent, 'calendar_id') and parent.calendar_id or False
        if res_obj:
            if not self.calendar_id: self.calendar_id = res_obj.id
            pr = res_obj.perm_read(context=context, details=False)[0]
            self.create_date = pr.get('create_date')
            self.write_date = pr.get('write_date') or pr.get('create_date')
            self.displayname = res_obj.name

        self.content_length = 0

        self.model = res_model
        self.res_id = res_id

    def open_data(self, cr, mode):
        return nodefd_static(self, cr, mode)

    def get_data(self, cr, fil_obj=None):
        uid = self.context.uid
        calendar_obj = self.context._dirobj.pool.get('basic.calendar')
        context = self.context.context.copy()
        context.update(self.dctx)
        context.update({'model': self.model, 'res_id':self.res_id})
        res = calendar_obj.export_cal(cr, uid, [self.calendar_id], context=context)
        return res
  
    def _get_caldav_calendar_data(self, cr):
        return self.get_data(cr)

    def get_data_len(self, cr, fil_obj = None):
        return self.content_length

    def set_data(self, cr, data, fil_obj = None):
        uid = self.context.uid
        context = self.context.context.copy()
        context.update(self.dctx)
        context.update({'model': self.model, 'res_id':self.res_id})
        calendar_obj = self.context._dirobj.pool.get('basic.calendar')
        res =  calendar_obj.import_cal(cr, uid, data, self.calendar_id, context=context)
        return res

    def _get_ttag(self,cr):
        res = False
        if self.model and self.res_id:
            res = '%s_%d' % (self.model, self.res_id)
        elif self.calendar_id:
            res = '%d' % (self.calendar_id)
        return res

    def _get_wtag(self, cr):
        uid = self.context.uid
        context = self.context.context
        if self.model and self.res_id:
            mod_obj = self.context._dirobj.pool.get(self.model)
            pr = mod_obj.perm_read(cr, uid, [self.res_id], context=context, details=False)[0]
            self.write_date = pr.get('write_date') or pr.get('create_date')
        
        # Super will use self.write_date, so we should be fine.
        return super(res_node_calendar, self)._get_wtag(cr)

    def rm(self, cr):
        uid = self.context.uid
        res = False
        if self.type in ('collection','database'):
            return False
        if self.model and self.res_id:
            document_obj = self.context._dirobj.pool.get(self.model)
            if document_obj:
                res =  document_obj.unlink(cr, uid, [self.res_id])

        return res

   

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4
