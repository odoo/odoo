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
from openerp.addons.website.models.website import slug
import datetime
import pytz
from pytz import timezone
from collections import OrderedDict
from openerp import tools

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
    _description = 'Event Tracks'
    _order = 'priority, date'
    _inherit = ['mail.thread', 'ir.needaction_mixin', 'website.seo.metadata']

    def _website_url(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, '')
        for track in self.browse(cr, uid, ids, context=context):
            res[track.id] = "/event/%s/track/%s" % (slug(track.event_id), slug(track))
        return res

    _columns = {
        'name': fields.char('Track Title', required=True, translate=True),
        'user_id': fields.many2one('res.users', 'Responsible'),
        'speaker_ids': fields.many2many('res.partner', string='Speakers'),
        'tag_ids': fields.many2many('event.track.tag', string='Tags'),
        'stage_id': fields.many2one('event.track.stage', 'Stage'),
        'description': fields.html('Track Description', translate=True),
        'date': fields.datetime('Track Date'),
        'duration': fields.integer('Duration'),
        'location_id': fields.many2one('event.track.location', 'Location'),
        'event_id': fields.many2one('event.event', 'Event', required=True),
        'color': fields.integer('Color Index'),
        'priority': fields.selection([('3','Low'),('2','Medium (*)'),('1','High (**)'),('0','Highest (***)')], 'Priority', required=True),
        'website_published': fields.boolean('Available in the website'),
        'website_url': fields.function(_website_url, string="Website url", type="char"),
        'image': fields.related('speaker_ids', 'image', type='binary', readonly=True)
    }
    def set_priority(self, cr, uid, ids, priority, context={}):
        return self.write(cr, uid, ids, {'priority' : priority})

    def _default_stage_id(self, cr, uid, context={}):
        stage_obj = self.pool.get('event.track.stage')
        ids = stage_obj.search(cr, uid, [], context=context)
        return ids and ids[0] or False

    _defaults = {
        'user_id': lambda self, cr, uid, ctx: uid,
        'website_published': lambda self, cr, uid, ctx: False,
        'duration': lambda *args: 60,
        'stage_id': _default_stage_id,
        'priority': '2'
    }
    def default_get(self, cr, uid, fields, context=None):
        if context is None:context = {}
        res = super(event_track, self).default_get(cr, uid, fields, context=context)
        if res.get('event_id'):
            res['date'] = self.pool.get('event.event').browse(cr, uid, res.get('event_id'), context=context).date_begin
        return res

    def _check_if_track_overlap(self, cr, uid, ids, context=None):
        for track in self.browse(cr, uid, ids, context=context):
            #if duration and start date enter check overlapping.
            if track.date and track.duration:
                if track.location_id:
                    cr.execute("SELECT (date, (duration || 'minutes')::INTERVAL) OVERLAPS (%s, (%s || 'minutes')::INTERVAL) from event_track where id!= %s and event_id=%s and (location_id=%s or location_id IS Null)", (track.date, track.duration, track.id, track.event_id.id, track.location_id.id or None))
                else:
                    cr.execute("SELECT (date, (duration || 'minutes')::INTERVAL) OVERLAPS (%s, (%s || 'minutes')::INTERVAL) from event_track where id!= %s and event_id=%s", (track.date, track.duration, track.id, track.event_id.id))
                result = cr.fetchall()
                for res in result:
                    if(res[0]):
                        return False
        return True

    _constraints = [
        (_check_if_track_overlap, 'This track is overlapping', ['This track is overlapping']),
    ]
    def _read_group_stage_ids(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
        stage_obj = self.pool.get('event.track.stage')
        result = stage_obj.name_search(cr, uid, '', context=context)
        return result, {}

    _group_by_full = {
        'stage_id': _read_group_stage_ids,
    }
    @staticmethod
    def calculate_slots(new_start_date, new_end_date, new_schedule):
        if not new_schedule:
            new_schedule.append([new_start_date, new_end_date])
            return new_schedule
        
        first_start_date = new_schedule[0][0]
        last_end_date = new_schedule[-1][1]

        def insert_time(time, new_schedule):
            for new_date in time:
                for index2, date in enumerate(new_schedule):
                    start_date, end_date = date
                    if start_date == new_date or end_date == new_date:break
                    if start_date < new_date and end_date > new_date:
                        new_schedule.pop(index2)
                        new_schedule.insert(index2, [new_date, end_date])
                        new_schedule.insert(index2, [start_date, new_date])
                        break
            return new_schedule
    
        #totally outter
        if first_start_date >= new_start_date and new_end_date >= last_end_date:
            if not new_start_date == first_start_date: new_schedule.insert(0, [new_start_date, first_start_date])
            if not last_end_date ==  new_end_date: new_schedule.append([last_end_date, new_end_date])
            return new_schedule
        
        #lower outer
        if first_start_date >= new_end_date:
            new_schedule.insert(0, [new_start_date, new_end_date])
            if not new_end_date == first_start_date: new_schedule.insert(1, [new_end_date, first_start_date])
            return new_schedule
        
        # upper outer
        if new_start_date >= last_end_date:
            if not last_end_date == new_start_date: new_schedule.append([last_end_date, new_start_date])
            new_schedule.append([new_start_date, new_end_date])
            return new_schedule
        
        #When inner time
        if first_start_date <= new_start_date and last_end_date >= new_end_date:
            return insert_time([new_start_date, new_end_date], new_schedule)
        
        #when start date is more and end date in range
        if first_start_date > new_start_date and last_end_date >= new_end_date:
            new_schedule.insert(0, [new_start_date, first_start_date])
            return insert_time([new_end_date], new_schedule)
        
        #when end date is more and start date in range
        if new_end_date > last_end_date and new_start_date >= first_start_date:
             new_schedule = insert_time([new_start_date], new_schedule)
             new_schedule.append([last_end_date, new_end_date])
             return new_schedule
             
    @staticmethod
    def convert_time(time, duration, local_tz):
        local_dt = (datetime.datetime.strptime(time, tools.DEFAULT_SERVER_DATETIME_FORMAT)).replace(tzinfo=pytz.utc).astimezone(local_tz)
        local_tz.normalize(local_dt)
        return local_dt, local_dt + datetime.timedelta(minutes = duration), local_dt.strftime('%m-%d-%y') 

    @staticmethod
    def generate_slots(date_and_durations, timezone):
        local_tz = pytz.timezone(timezone or 'UTC')
        got_slots = {}
        sort_track = {}
        for record in date_and_durations:
            start_time, end_time, key = event_track.convert_time(record[0], record[1], local_tz)
            if not got_slots.has_key(key):got_slots[key] = []
            got_slots[key] = event_track.calculate_slots(start_time, end_time, got_slots[key])

        for day in got_slots:
            sort_track[day] = OrderedDict()
            for slot in got_slots[day]:
                time = slot[0].strftime('%H:%M')+" - "+slot[1].strftime('%H:%M')
                sort_track[day][time] = []
        return got_slots, sort_track
    
    def make_tracks(self,cr, uid, only_slots={}, sort_tracks={}, event_tracks=[], timezone='UTC', context=None):
        def get_speaker_name(ids):
            speaker_names = res_partner.name_get(cr, uid, ids, context=context)
            string = "By "
            for name in speaker_names:
                string = string + name[1]
                if(speaker_names[-1:][0][0] != name[0]):string = string + ", "
            return string

        res_partner = self.pool.get('res.partner')
        local_tz = pytz.timezone(timezone)
        
        for track in event_tracks:
            start_time, end_time, key = event_track.convert_time(track['date'], track['duration'], local_tz)
            secret_key = None
            row_span = 0
            for index, value in enumerate(only_slots[key]):
                if value[0] <= start_time and value[1] > start_time:
                    keys = sort_tracks[key].keys()
                    secret_key = keys[index]
                    row_span = index
                if value[1] == end_time and secret_key:
                    if not index == row_span:
                        row_span = row_span - 1
                    track['row_span'] = index - row_span
                    track['speaker_ids'] = get_speaker_name(track['speaker_ids']) if len(track['speaker_ids'])else ""
                    sort_tracks[key][secret_key].append(track)
        return sort_tracks
    
    @staticmethod
    def calculate_and_sort(sort_tracks):
        row_skip_td = {}
        talks = {}
        for track_day in sort_tracks.keys():
            talks[track_day] = 0
            row_skip_td[track_day] = {}
            time_slots = sort_tracks[track_day].keys()
            for time_slot in time_slots:
                #sort location id
                sort_tracks[track_day][time_slot] = sorted(sort_tracks[track_day][time_slot], key=lambda x: x['location_id'])
                
                #calculate_talks
                talks[track_day] = talks[track_day] + len(sort_tracks[track_day][time_slot])
                
                #Getting td which will skip in future.
                for track in sort_tracks[track_day][time_slot]:
                    if track['row_span']:
                        skip_time = time_slots[time_slots.index(time_slot)+1: time_slots.index(time_slot)+track['row_span']]
                        location_key = track['location_id'][0] if track['location_id'] else 0
                        if not row_skip_td[track_day].has_key(location_key):
                            row_skip_td[track_day] [location_key] = []
                        row_skip_td[track_day][location_key] = row_skip_td[track_day] [location_key] + skip_time
        return row_skip_td, sort_tracks, talks
        
    def get_location(self, cr, uid, location_list):
        location_object = self.pool.get('event.track.location')
        locations = []
        for location_id in location_list:
            locations.append([location_id, location_object.browse(cr, uid, location_id).name])
        return locations

    def get_sorted_tracks(self, cr, uid, event, context=None):
        #Fetch all tracks
        domain = [('event_id','=',event.id),('date','!=',False),('duration','!=',False),('duration','!=',0)]
        fields = ['id', 'duration', 'location_id', 'name', 'date', 'color', 'speaker_ids', 'website_published']
        event_tracks = self.search_read(cr, uid, domain, fields, context=context)
        only_slots, sort_tracks = event_track.generate_slots([(track['date'], track['duration']) for track in event_tracks], event.timezone_of_event)
        sort_tracks = self.make_tracks(cr, uid, only_slots, sort_tracks, event_tracks, event.timezone_of_event, context=context)
        row_skip_td, sort_tracks, talks = event_track.calculate_and_sort(sort_tracks)
        return  {
            'event': event,
            'room_list': self.get_location(cr, uid, set([track['location_id'][0] for track in event_tracks if track['location_id']])),
            'days': sort_tracks,
            'row_skip_td': row_skip_td,
            'talks': talks,
            'format_date': [(datetime.datetime.strptime(day, '%m-%d-%y')).strftime("%d %B, %Y") for day in sort_tracks.keys()],
        }

#
# Events
#
class event_event(osv.osv):
    _inherit = "event.event"
    def _tz_get(self,cr,uid, context=None):
        # put POSIX 'Etc/*' entries at the end to avoid confusing users - see bug 1086728
        return [(tz,tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]

    def _get_tracks_tag_ids(self, cr, uid, ids, field_names, arg=None, context=None):
        res = dict.fromkeys(ids, [])
        for event in self.browse(cr, uid, ids, context=context):
            for track in event.track_ids:
                res[event.id] += [tag.id for tag in track.tag_ids]
            res[event.id] = list(set(res[event.id]))
        return res
    _columns = {
        'tag_ids': fields.many2many('event.tag', string='Tags'),
        'track_ids': fields.one2many('event.track', 'event_id', 'Tracks'),
        'sponsor_ids': fields.one2many('event.sponsor', 'event_id', 'Sponsorships'),
        'blog_id': fields.many2one('blog.blog', 'Event Blog'),
        'show_track_proposal': fields.boolean('Talks Proposals'),
        'show_tracks': fields.boolean('Multiple Tracks'),
        'show_blog': fields.boolean('News'),
        'tracks_tag_ids': fields.function(_get_tracks_tag_ids, type='one2many', relation='event.track.tag', string='Tags of Tracks'),
        'allowed_track_tag_ids': fields.many2many('event.track.tag', string='Accepted Tags', help="List of available tags for track proposals."),
        'timezone_of_event': fields.selection(_tz_get, 'Timezone of Event', size=64),
    }
    _defaults = {
        'show_track_proposal': False,
        'show_tracks': False,
        'show_blog': False,
        'timezone_of_event':lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).tz,
    }
    def _get_new_menu_pages(self, cr, uid, event, context=None):
        context = context or {}
        result = super(event_event, self)._get_new_menu_pages(cr, uid, event, context=context)
        if event.show_tracks:
            result.append( (_('Talks'), '/event/%s/track' % slug(event)))
            result.append( (_('Agenda'), '/event/%s/agenda' % slug(event)))
        if event.blog_id:
            result.append( (_('News'), '/blogpost'+slug(event.blog_ig)))
        if event.show_track_proposal:
            result.append( (_('Talk Proposals'), '/event/%s/track_proposal' % slug(event)))
        return result

#
# Sponsors
#

class event_sponsors_type(osv.osv):
    _name = "event.sponsor.type"
    _order = "sequence"
    _columns = {
        "name": fields.char('Sponsor Type', required=True),
        "sequence": fields.integer('Sequence')
    }

class event_sponsors(osv.osv):
    _name = "event.sponsor"
    _order = "sequence"
    _columns = {
        'event_id': fields.many2one('event.event', 'Event', required=True),
        'sponsor_type_id': fields.many2one('event.sponsor.type', 'Sponsoring Type', required=True),
        'partner_id': fields.many2one('res.partner', 'Sponsor/Customer', required=True),
        'url': fields.text('Sponsor Website'),
        'sequence': fields.related('sponsor_type_id', 'sequence', string='Sequence', store=True),
        'image_medium': fields.related('partner_id', 'image_medium', string='Logo')
    }

    def has_access_to_partner(self, cr, uid, ids, context=None):
        partner_ids = [sponsor.partner_id.id for sponsor in self.browse(cr, uid, ids, context=context)]
        return len(partner_ids) == self.pool.get("res.partner").search(cr, uid, [("id", "in", partner_ids)], count=True, context=context)