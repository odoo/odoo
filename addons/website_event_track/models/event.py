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

from openerp.osv import fields, osv
from openerp.tools.translate import _

class event_tag(osv.osv):
    _name = "event.tag"
    _columns = {
        'name': fields.char('Event Tag')
    }

#
# Tracks: conferences
# 

class event_track_stage(osv.osv):
    _name = "event.track.stage"
    _columns = {
        'name': fields.char('Track Stage')
    }


class event_track_location(osv.osv):
    _name = "event.track.location"
    _columns = {
        'name': fields.char('Track Rooms')
    }

class event_track(osv.osv):
    _name = "event.track"
    _order = 'date'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _columns = {
        'name': fields.char('Track Title', required=True),
        'user_id': fields.many2one('res.users', 'Responsible'),
        'speaker_ids': fields.many2many('res.partner'),
        'tag_ids': fields.many2many('event.track.tag'),
        'stage_id': fields.many2one('event.track.stage'),
        'description': fields.html('Track Description'),
        'date': fields.datetime('Track Date'),
        'duration': fields.float('Duration (Hours)'),
        'location_id': fields.many2one('event.track.location'),
        'attachment_show': fields.boolean('Show Documents'),
        'event_id': fields.many2one('event.event', 'Event', required=True),
        'color': fields.integer('Color Index'),
    }
    _defaults = {
        'user_id': lambda self, cr, uid, ctx: uid,
        'attachment_show': lambda self, cr, uid, ctx: True,
    }


#
# Events
#

class event_event(osv.osv):
    _inherit = "event.event"
    _columns = {
        'tag_ids': fields.many2many('Tags'),
        'track_ids': fields.one2many('event.track', 'event_id', 'Tracks'),
        'blog_id': fields.many2one('blog.blog', 'Event Blog'),
   }

