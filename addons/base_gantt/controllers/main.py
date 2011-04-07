import glob, os
from xml.etree import ElementTree
import math
import simplejson
import openerpweb
import time
import datetime
from base.controllers.main import Xml2Json
   

COLOR_PALETTE = ['#f57900', '#cc0000', '#d400a8', '#75507b', '#3465a4', '#73d216', '#c17d11', '#edd400',
                 '#fcaf3e', '#ef2929', '#ff00c9', '#ad7fa8', '#729fcf', '#8ae234', '#e9b96e', '#fce94f',
                 '#ff8e00', '#ff0000', '#b0008c', '#9000ff', '#0078ff', '#00ff00', '#e6ff00', '#ffff00',
                 '#905000', '#9b0000', '#840067', '#510090', '#0000c9', '#009b00', '#9abe00', '#ffc900', ]

_colorline = ['#%02x%02x%02x' % (25 + ((r + 10) % 11) * 23, 5 + ((g + 1) % 11) * 20, 25 + ((b + 4) % 11) * 23) for r in range(11) for g in range(11) for b in range(11) ]

def choice_colors(n):
        if n > len(COLOR_PALETTE):
            return _colorline[0:-1:len(_colorline) / (n + 1)]
        elif n:
            return COLOR_PALETTE[:n]
        return []
 
class GanttView(openerpweb.Controller):
    _cp_path = "/base_gantt/ganttview"
   
    date_start = None
    date_delay = None
    date_stop = None
    color_field = None
    
    day_length = 8
    fields = {}
    events = []
    calendar_fields = {}
    ids = []
    model = ''
    domain = []
    context = {}
    event_res = []
    colors = {}
    color_values = []
 
    @openerpweb.jsonrequest
    def load(self, req, model, view_id):
        m = req.session.model(model)
        r = m.fields_view_get(view_id, 'gantt')
        r["arch"] = Xml2Json.convert_to_structure(r["arch"])
        return {'fields_view':r}
    
    @openerpweb.jsonrequest
    def get_events(self, req, **kw):

        self.model = kw['model']
        self.fields = kw['fields']
        self.day_length = kw['day_length']
        self.calendar_fields = kw['calendar_fields']
        self.color_field = kw.get('color_field') or self.color_field or None
        self.fields[self.color_field] = ""
        self.colors = kw.get('colors') or {}
        self.text = self.calendar_fields['text']['name']
        
        self.date_start = self.calendar_fields['date_start']['name']
        self.fields[self.date_start] = ""
        
        if self.calendar_fields.get('date_stop'):
            self.date_stop = self.calendar_fields['date_stop']['name']
            self.fields[self.date_stop] = ""
        if self.calendar_fields.get('date_delay'):
            self.date_delay = self.calendar_fields['date_delay']['name']
            self.fields[self.date_delay] = ""
        if self.calendar_fields.get('parent'):
            self.parent = self.calendar_fields['parent']['name']
            self.fields[self.parent] = ""
            
        model = req.session.model(self.model)
        event_ids = model.search([])
        
        return self.create_event(event_ids, model)
        
    def create_event(self, event_ids, model):
    
        self.events = model.read(event_ids, self.fields.keys())
        result = []
        for evt in self.events:
            
            event_res = {}
            key = evt[self.color_field]
            name = key
            value = key
            if isinstance(key, list): # M2O, XMLRPC returns List instead of Tuple
                name = key[0]
                value = key[-1]
                evt[self.color_field] = key = key[-1]
            if isinstance(key, tuple): # M2O
                value, name = key
                
            self.colors[key] = (name, value, None)
            
            st_date = evt.get(self.date_start)
            if st_date:
                self.set_format(st_date)
                if self.date_delay:
                    duration = evt.get(self.date_delay)
                else:
                    en_date = evt.get(self.date_stop)
                    
                    duration = (time.mktime(time.strptime(en_date, self.format))-\
                                time.mktime(time.strptime(st_date, self.format)))/ (60 * 60)

                    if duration > self.day_length :
                        d = math.floor(duration / 24)
                        h = duration % 24
                        duration = d * self.day_length + h
                
                event_res = {}
                event_res['start_date'] = st_date
                event_res['duration'] = duration
                event_res['text'] = evt.get(self.text)
                event_res['id'] = evt['id']
                event_res['parent'] = evt.get(self.parent)
                result.append(event_res)
                
        colors = choice_colors(len(self.colors))
        for i, (key, value) in enumerate(self.colors.items()):
            self.colors[key] = [value[0], value[1], colors[i]]
            
        return {'result': result,'sidebar': self.colors}

    def set_format(self, st_date):
        if len(st_date) == 10 :
            self.format = "%Y-%m-%d"
        else :
            self.format = "%Y-%m-%d %H:%M:%S"
        return
            
    def check_format(self, date):
        if self.format == "%Y-%m-%d %H:%M:%S":
            date = date + " 00:00:00"
        return date    

    @openerpweb.jsonrequest
    def on_event_resize(self, req, **kw):
        if self.date_delay:
            key = self.date_delay
            value = kw['duration']
        else:
            key = self.date_stop
            value = self.check_format(kw['end_date'])
        try:
            model = req.session.model(self.model)
            res = model.write(kw['id'], {key : value})
        except Exception, e:
            print "eeeeeeeeeeeeeeeeeeeeeeeeeee",e
        return True
    
    @openerpweb.jsonrequest
    def on_event_drag(self, req, **kw):
        start_date = self.check_format(kw['start_date']) 
        if self.date_delay:
            key = self.date_delay
            value = kw['duration']
        else:
            key = self.date_stop
            value = self.check_format(kw['end_date'])
        try:
            model = req.session.model(self.model)
            res = model.write(kw['id'], {self.date_start : start_date, key : value})
        except Exception, e:
            print "eeeeeeeeeeeeeeeeeeeeeeeeeee",e
        return True
    
    @openerpweb.jsonrequest
    def reload_gantt(self, req, **kw):
        
        model = req.session.model(kw['model'])
        if (kw['domain']):
            domain = (kw['color_field'],'in', kw['domain']) 
            event_ids = model.search([domain])
        else:
            event_ids = model.search([])
        return self.create_event(event_ids, model)
    