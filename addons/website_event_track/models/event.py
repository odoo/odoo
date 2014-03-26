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


def get_schedule(new_start_date, new_end_date, new_schedule):
    '''
        Function get_schedule  creates time slots according to given track.
        
        new_start_date, new_end_date : Date for creating new slots.
        new_schedule : Dictionary contain all value to compare
        rtype: new_schedule(new Dictionary with new time slot added)
    '''
    def insert_time(time, new_schedule):
        for index,ct in enumerate(time):
            for index2,dt in enumerate(new_schedule):
                st, et = dt
                if st == ct or et == ct:break
                if st < ct and et > ct:
                    new_schedule.pop(index2)
                    new_schedule.insert(index2, [ct, et])
                    new_schedule.insert(index2, [st, ct])
                    break
        return new_schedule
    if not new_schedule:
        new_schedule.append([new_start_date, new_end_date])
        return new_schedule
    first_start_date = new_schedule[0][0]
    last_end_date = new_schedule[-1][1]

    #totally outter
    if first_start_date >= new_start_date and new_end_date >= last_end_date:
        if not new_start_date == first_start_date:
            new_schedule.insert(0, [new_start_date, first_start_date])
        if not last_end_date ==  new_end_date:
            new_schedule.append([last_end_date, new_end_date])
        return new_schedule
    
    #lower outer
    if first_start_date >= new_end_date:
        new_schedule.insert(0, [new_start_date, new_end_date])
        if not new_end_date == first_start_date:
            new_schedule.insert(1, [new_end_date, first_start_date])
        return new_schedule
    
    # upper outer
    if new_start_date >= last_end_date:
        if not last_end_date == new_start_date:
            new_schedule.append([last_end_date, new_start_date])
        new_schedule.append([new_start_date, new_end_date])
        return new_schedule
    
    #When inner time
    if first_start_date <= new_start_date and last_end_date >= new_end_date:
        new_schedule = insert_time([new_start_date, new_end_date], new_schedule)
        return new_schedule
    
    #when start date is more and end date in range
    if first_start_date > new_start_date and last_end_date >= new_end_date:
        new_schedule.insert(0, [new_start_date, first_start_date])
        new_schedule = insert_time([new_end_date], new_schedule)
        return new_schedule
    
    #when end date is more and start date in range
    if new_end_date > last_end_date and new_start_date >= first_start_date:
         new_schedule = insert_time([new_start_date], new_schedule)
         new_schedule.append([last_end_date, new_end_date])
         return new_schedule
 
def convert_time(time, duration, local_tz):
    '''
        Function convert_time update value according to given timezone.
        time: Value in string
        duration: integer
        rtype: start time, end time and date in string.
    '''
    local_dt = (datetime.datetime.strptime(time, tools.DEFAULT_SERVER_DATETIME_FORMAT)).replace(tzinfo=pytz.utc).astimezone(local_tz)
    local_tz.normalize(local_dt)
    return local_dt, local_dt + datetime.timedelta(minutes = duration), local_dt.strftime('%m-%d-%y') 

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
    def get_tracks_schedulre_details(self, cr, uid, event, context=None):
        '''
            Method get_tracks_schedulre_details create object in well format to show tabular form.
            event: Browse Object of evenet.event
            rtype:
                rooms: room list contain id and name of location.
                sort_tracks: Well form object of track data.
                row_skip_td: To skip td for rowspan
                talks: talks on everyday
                format_date: format title
        '''
        keys_for_table = {}
        format_date = []
        sort_tracks = {}
        room_list = []
        rooms = []
        talks = {}
        row_skip_td = {}
        domain = [('event_id','=',event.id),('date','!=',False),('duration','!=',False),('duration','!=',0)]
        fields = ['id', 'duration', 'location_id', 'name', 'date', 'color', 'speaker_ids', 'website_published']
        location_object = self.pool.get('event.track.location')
        res_partner = self.pool.get('res.partner')
        local_tz = pytz.timezone(event.timezone_of_event or 'UTC')
        event_tracks = self.search_read(cr, uid, domain, fields, context=context)
        
        def get_speaker_name(ids):
            speaker_names = res_partner.name_get(cr, uid, ids, context=context)
            string = "By "
            for name in speaker_names:
                string = string + name[1]
                if(speaker_names[-1:][0][0] != name[0]):string = string + ", "
            return string
        def set_value(key, val):
            sort_tracks[key][val]=[]
        
        for track in event_tracks:
            start_time, end_time, key = convert_time(track['date'], track['duration'], local_tz)
            if not keys_for_table.has_key(key):
                keys_for_table[key] = []
                sort_tracks[key] = OrderedDict()
                talks[key] = 0
            talks[key] = talks[key] + 1 
            keys_for_table[key] = get_schedule(start_time, end_time, keys_for_table[key])
            
        [set_value(key, value[0].strftime('%H:%M')+" - "+value[1].strftime('%H:%M')) for key in keys_for_table.keys() for value in keys_for_table[key]]

        for track in event_tracks:
            if(track['location_id']):room_list.append(track['location_id'][0])
            start_time, end_time, key = convert_time(track['date'], track['duration'], local_tz)
            secret_key = None
            row_span = 0
            for index, value in enumerate(keys_for_table[key]):
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
        
        for room in list(set(room_list)):
            if room:rooms.append([room, location_object.browse(cr, uid, room).name])

        for track_day in sort_tracks.keys():
            #format date eg. 4 june,2014.
            format_date.append((datetime.datetime.strptime(track_day, '%m-%d-%y')).strftime("%d %B, %Y"))
            
            row_skip_td[track_day] = {}
            time_slots = sort_tracks[track_day].keys()
            for time_slot in time_slots:
                #sort location id
                sort_tracks[track_day][time_slot] = sorted(sort_tracks[track_day][time_slot], key=lambda x: x['location_id'])
                #Getting td which will skip in future.
                for track in sort_tracks[track_day][time_slot]:
                    if track['row_span']:
                        skip_time = time_slots[time_slots.index(time_slot)+1: time_slots.index(time_slot)+track['row_span']]
                        location_key = track['location_id'][0] if track['location_id'] else 0
                        if not row_skip_td[track_day].has_key(location_key):
                            row_skip_td[track_day] [location_key] = []
                        row_skip_td[track_day][location_key] = row_skip_td[track_day] [location_key] + skip_time
        return  {
            'event': event,
            'room_list': rooms,
            'days': sort_tracks,
            'row_skip_td': row_skip_td,
            'talks': talks,
            'format_date': format_date,
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
            result.append( (_('Talks'), '/event/%s/track/' % slug(event)))
            result.append( (_('Agenda'), '/event/%s/agenda/' % slug(event)))
        if event.blog_id:
            result.append( (_('News'), '/blogpost/'+slug(event.blog_ig)))
        if event.show_track_proposal:
            result.append( (_('Talk Proposals'), '/event/%s/track_proposal/' % slug(event)))
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
    }

    def has_access_to_partner(self, cr, uid, ids, context=None):
        partner_ids = [sponsor.partner_id.id for sponsor in self.browse(cr, uid, ids, context=context)]
        return len(partner_ids) == self.pool.get("res.partner").search(cr, uid, [("id", "in", partner_ids)], count=True, context=context)