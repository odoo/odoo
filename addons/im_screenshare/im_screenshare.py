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
import openerp.addons.im.im

from openerp.osv import osv, fields
from openerp.http import request

_logger = logging.getLogger(__name__)


#----------------------------------------------------------
# Controllers
#----------------------------------------------------------

class Controller(openerp.addons.im.im.Controller):

    @openerp.http.route('/im_screenshare/start', type="json", auth="none")
    def start(self, **kwargs):
        return '%s' % uuid.uuid4()

    @openerp.http.route('/im_screenshare/share', type="json", auth="none")
    def share(self, uuid, message):
        registry, cr, context, uid = request.registry, request.cr, request.context, request.session.uid
        return registry.get('im.bus').sendone(cr, uid, uuid, message)

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
    _columns = {
        'name' : fields.char('Title'),
        'starttime' : fields.datetime('Start Time', readonly=True),     # Obtained from webclient's messsages
        'endtime' : fields.datetime('End Time', readonly=True),
        'duration' : fields.datetime('Total Time', readonly=True),
        'user_id' : fields.many2one('res.users', 'User', readonly=True),
        'event_ids' : fields.one2many('im_screenshare.record.event', 'screen_record_id', 'Events', readonly=True),
        'description' : fields.text('Description'),
    }
    _defaults = {
        'user_id': lambda self,cr,uid,context: uid
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
        'timestamp' : fields.float('Timestamp', readonly=True),
        'timestamp_date' : fields.datetime('Timestamp', readonly=True),
        'notes': fields.text('Internal Notes'),
        'msglist' : fields.text('Messages', readonly=True),
    }