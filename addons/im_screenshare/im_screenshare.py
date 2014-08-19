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
import openerp
import logging
import simplejson
import uuid
import openerp.addons.bus.bus
import datetime

from openerp.osv import osv, fields
from openerp.http import request
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

_logger = logging.getLogger(__name__)


#----------------------------------------------------------
# Controllers
#----------------------------------------------------------

class Controller(openerp.addons.bus.bus.Controller):

    @openerp.http.route('/im_screenshare/start', type="json", auth="none")
    def start(self, mode='record', **kwargs):
        # mode must be in ['record', 'share']
        if( mode == 'record'):
            registry, cr, context, uid = request.registry, request.cr, request.context, request.session.uid
            data = {
                'name' : "Screen Record",
                'user_id' : uid,
            }
            return registry['im_screenshare.record'].create(cr, uid, data, context=context)
        else:
            return '%s' % uuid.uuid4()

    @openerp.http.route('/im_screenshare/share', type="json", auth="none")
    def share(self, mutations, uuid=None, record_id=None):
        registry, cr, context, uid = request.registry, request.cr, request.context, request.session.uid
        if uuid:
            registry.get('bus.bus').sendone(cr, uid, uuid, mutations)
        if record_id:
            data = {
                "screen_record_id" : record_id,
                "timestamp" : 0,
                "mutations" : simplejson.dumps(mutations),
            }
            registry['im_screenshare.record.event'].create(cr, uid, data, context=context)

    @openerp.http.route(['/im_screenshare/player/<string:uuid>','/im_screenshare/player/<int:id>/<string:dbname>'], type='http', auth='none')
    def player(self, uuid=None, id=None, dbname=None):
        params = {
            "uuid" : uuid,
            "id" : id,
            "dbname" : dbname
        }
        return request.render('im_screenshare.player_page', dict(params = simplejson.dumps(params)))


#----------------------------------------------------------
# Models
#----------------------------------------------------------

class im_screenshare_record(osv.Model):

    _name = 'im_screenshare.record'

    def _get_duration(self, cr, uid, ids, fields, arg, context=None):
        """ get the duration between the first and the last events of a record """
        result = {}
        for record in self.browse(cr, uid, ids, context=context):
            events = self.pool['im_screenshare.record.event'].search_read(cr, uid, [('screen_record_id', '=', record.id)], order="create_date asc", context=context)
            if events:
                start_date = datetime.datetime.strptime(events[0]["create_date"], DEFAULT_SERVER_DATETIME_FORMAT)
                end_date = datetime.datetime.strptime(events[-1]["create_date"], DEFAULT_SERVER_DATETIME_FORMAT)
                result[record.id] = (end_date - start_date).seconds / 60 # minutes
            else:
                result[record.id] = 0
        return result

    _columns = {
        'name' : fields.char('Title'),
        'starttime' : fields.datetime('Start Time', readonly=True),     # Obtained from webclient's messsages
        'duration' : fields.function(_get_duration, string='Duration', help="Difference between first and last events of the record."),
        'user_id' : fields.many2one('res.users', 'User', readonly=True),
        'event_ids' : fields.one2many('im_screenshare.record.event', 'screen_record_id', 'Events', readonly=True),
        'description' : fields.text('Description'),
    }
    _defaults = {
        'user_id': lambda self,cr,uid,context: uid,
        'starttime' : fields.datetime.now,
    }

    def play_screen_record(self, cr, uid, id, context=None):
        url="/im_screenshare/player/" + str(id[0]) + "/" + cr.dbname
        _logger.debug(url)
        return {
            'type': 'ir.actions.act_url',
            'url':url,
            'target': '_blank'
        }

class im_screenshare_record_event(osv.Model):
    _name = "im_screenshare.record.event"
    _rec_name = "screen_record_id"
    _columns = {
        'screen_record_id' : fields.many2one('im_screenshare.record', 'Screen Record', readonly=True),
        'timestamp' : fields.float('Timestamp', readonly=True, help="The recording start at 'instant zero', then this timestamp is increased."),
        'mutations' : fields.text('DOM Mutations', readonly=True, help="This field contains the DOM Mutations (changes) generated by the Summary Mutations Javascript Library."),
    }