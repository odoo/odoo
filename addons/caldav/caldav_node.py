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
from tools.translate import _
import pooler
import tools
import time
import base64


class node_calendar(object):
    def __init__(self, path, context, calendar):
        self.path = path
        self.context = context
        self.calendar_id =  calendar.id
        self.mimetype = 'ics'
        self.create_date = calendar.create_date
        self.write_date = calendar.write_date or calendar.create_date
        self.content_length = 0
        self.displayname = calendar.name


    def get_data(self, cr, uid):
        calendar_obj = pooler.get_pool(cr.dbname).get('basic.calendar')
        return calendar_obj.export_cal(cr, uid, [self.calendar_id])

    def get_data_len(self, cr):
        return self.content_length

    def set_data(self, cr, uid, data):
        calendar_obj = pooler.get_pool(cr.dbname).get('basic.calendar')
        return calendar_obj.import_cal(cr, uid, base64.encodestring(data), self.calendar_id)

    def get_etag(self, cr):
        """ Get a tag, unique per object + modification.

            see. http://tools.ietf.org/html/rfc2616#section-13.3.3 """
        return self._get_ttag(cr) + ':' + self._get_wtag(cr)

    def _get_wtag(self, cr):
        """ Return the modification time as a unique, compact string """
        if self.write_date:
            wtime = time.mktime(time.strptime(self.write_date, '%Y-%m-%d %H:%M:%S'))
        else: wtime = time.time()
        return str(wtime)

    def _get_ttag(self, cr):
        return 'calendar-%d' % self.calendar_id


class Calendar(osv.osv):
    _inherit = 'basic.calendar'

    def get_calendar_object(self, cr, uid, uri, context=None):
        if not uri:
            return None
        if len(uri) > 1:
            return None
        name, file_type = tuple(uri[0].split('.'))
        res = self.name_search(cr, uid, name)
        if not res:
            return None
        calendar_id, calendar_name = res[0]
        calendar = self.browse(cr, uid, calendar_id)
        return node_calendar(uri, context, calendar)
Calendar()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4