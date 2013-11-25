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

class event_track_tag(osv.osv):
    _name = "event.track.tag"
    _columns = {
        'name': fields.char('Event Track Tag')
    }

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
    _order = 'sequence'
    _columns = {
        'name': fields.char('Track Stage'),
        'sequence': fields.integer('Sequence')
    }
    _defaults = {
        'sequence': 0
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
        'speaker_ids': fields.many2many('res.partner', string='Speakers'),
        'tag_ids': fields.many2many('event.track.tag', string='Tags'),
        'stage_id': fields.many2one('event.track.stage'),
        'description': fields.html('Track Description'),
        'date': fields.datetime('Track Date'),
        'duration': fields.float('Duration (Hours)'),
        'location_id': fields.many2one('event.track.location', 'Location'),
        'show_attachments': fields.boolean('Show Documents'),
        'event_id': fields.many2one('event.event', 'Event', required=True),
        'color': fields.integer('Color Index'),
        'priority': fields.selection([('3','Low'),('2','Medium (*)'),('1','High (**)'),('0','Highest (***)')], 'Priority', required=True),
    }
    def set_priority(self, cr, uid, ids, priority, context={}):
        return self.write(cr, uid, ids, {'priority' : priority})

    def _default_stage_id(self, cr, uid, context={}):
        stage_obj = self.pool.get('event.track.stage')
        ids = stage_obj.search(cr, uid, [], context=context)
        return ids and ids[0] or False

    _defaults = {
        'user_id': lambda self, cr, uid, ctx: uid,
        'show_attachments': lambda self, cr, uid, ctx: True,
        'duration': lambda *args: 0,
        'stage_id': _default_stage_id,
        'priority': '2'
    }
    def _read_group_stage_ids(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
        stage_obj = self.pool.get('event.track.stage')
        result = stage_obj.name_search(cr, uid, '', context=context)
        return result, {}

    _group_by_full = {
        'stage_id': _read_group_stage_ids,
    }

#
# Events
#

class event_event(osv.osv):
    _inherit = "event.event"
    _columns = {
        'tag_ids': fields.many2many('event.tag', string='Tags'),
        'track_ids': fields.one2many('event.track', 'event_id', 'Tracks'),
        'blog_id': fields.many2one('blog.category', 'Event Blog'),
        'show_track_proposal': fields.boolean('Talks Proposals'),
        'show_tracks': fields.boolean('Multiple Tracks'),
        'show_blog': fields.boolean('News'),
        'track_tag_ids': fields.many2many('event.track.tag', string='Accepted Tracks'),
    }
    _defaults = {
        'show_track_proposal': False,
        'show_tracks': False,
        'show_blog': False,
    }
    def _get_new_menu_pages(self, cr, uid, event, context=None):
        context = context or {}
        result = super(event_event, self)._get_new_menu_pages(cr, uid, event, context=context)
        if event.show_tracks:
            result.append( (_('Agenda'), '/event/%s/tracks/' % event.id))
        if event.blog_id:
            result.append( (_('News'), '/blog/cat/'+str(event.blog_ig.id)))
        if event.show_track_proposal:
            result.append( (_('Talk Proposals'), '/event/%s/track_proposal/' % event.id))
        return result
