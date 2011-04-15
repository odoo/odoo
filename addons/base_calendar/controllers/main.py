from base.controllers.main import View
import openerpweb, time, math, re, datetime as DT, pytz

COLOR_PALETTE = ['#f57900', '#cc0000', '#d400a8', '#75507b', '#3465a4', '#73d216', '#c17d11', '#edd400',
                 '#fcaf3e', '#ef2929', '#ff00c9', '#ad7fa8', '#729fcf', '#8ae234', '#e9b96e', '#fce94f',
                 '#ff8e00', '#ff0000', '#b0008c', '#9000ff', '#0078ff', '#00ff00', '#e6ff00', '#ffff00',
                 '#905000', '#9b0000', '#840067', '#510090', '#0000c9', '#009b00', '#9abe00', '#ffc900', ]

_colorline = ['#%02x%02x%02x' % (25 + ((r + 10) % 11) * 23, 5 + ((g + 1) % 11) * 20, 25 + ((b + 4) % 11) * 23) for r in range(11) for g in range(11) for b in range(11) ]

DT_SERVER_FORMATS = {
  'datetime' : '%Y-%m-%d %H:%M:%S',
  'date' : '%Y-%m-%d',
  'time' : '%H:%M:%S'
}

DT_FORMAT_INFO = {'datetime' : ('%Y-%m-%d %H:%M:%S', DT.datetime, 0, 6),
                  'date': ('%Y-%m-%d', DT.date, 0, 3),
                  'time': ('%H:%M:%S', DT.time, 3, 6)}

def choice_colors(n):
        if n > len(COLOR_PALETTE):
            return _colorline[0:-1:len(_colorline) / (n + 1)]
        elif n:
            return COLOR_PALETTE[:n]
        return []

class CalendarView(View):
    _cp_path = "/base_calendar/calendarview"
    
    mode = 'month'
    date_start = None
    date_delay = None
    date_stop = None
    color_field = None
    day_length = 8
    use_search = False
    selected_day = None
    date_format = '%Y-%m-%d'
    info_fields = []
    fields = {}
    events = []

    colors = {}
    color_values = []

    remote_timezone = 'utc'
    client_timezone = False
    
    calendar_fields = {}
    concurrency_info = None

    ids = []
    model = ''
    domain = []
    context = {}
    
    @openerpweb.jsonrequest
    def load(self, req, model, view_id):
        fields_view = self.fields_view_get(req, model, view_id, 'calendar')
        return {'fields_view':fields_view}
    
    def convert(self, event):
        fields = [self.date_start]
        if self.date_stop:
            fields.append(self.date_stop)
            
        for fld in fields:
            fld_type = self.fields[fld]['type']
            fmt = DT_SERVER_FORMATS[fld_type]
            if event[fld] and fmt:
                event[fld] = time.strptime(event[fld], fmt)
            
            # default start/stop time is 9:00 AM / 5:00 PM
            if fld_type == 'date' and event[fld]:
                ds = list(event[fld])
                if fld == self.date_start:
                    ds[3] = 9
                elif fld == self.date_stop:
                    ds[3] = 17
                event[fld] = tuple(ds)
             
    
    @openerpweb.jsonrequest
    def schedule_events(self, req, **kw):
        self.model = kw['model']
        self.mode = kw.get('mode') or self.mode or 'month'
        self.fields = kw['fields']
        self.color_field = kw.get('color_field') or self.color_field or None
        self.colors = kw.get('colors') or {}
        self.calendar_fields = kw['calendar_fields']
        self.info_fields = kw['info_fields']
        self.date_start = self.calendar_fields['date_start']['name']
        self.domain = kw.get('domain') or []
        
        self.remote_timezone = req.session.remote_timezone
        self.client_timezone = req.session.client_timezone
        
        if self.calendar_fields.get('date_stop'):
            self.date_stop = self.calendar_fields['date_stop']['name']
        
        if self.calendar_fields.get('date_delay'):
            self.date_delay = self.calendar_fields['date_delay']['name']
            
        model = req.session.model(self.model)
        event_ids = model.search(self.domain)
        
        self.events = model.read(event_ids, self.fields.keys())
        result = []
        self.date_format = req.session._lang and req.session._lang['date_format']
        
        if self.color_field:
            for evt in self.events:
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
            
            colors = choice_colors(len(self.colors))
            for i, (key, value) in enumerate(self.colors.items()):
                self.colors[key] = [value[0], value[1], colors[i]]
        
        for evt in self.events:
            self.convert(evt)
            a = self.get_event_widget(evt)
            result.append(a)
            
        return {'result':result,'sidebar':self.colors}
    
    def parsedatetime(self, string):
        
        kind = 'datetime'

        if '-' in string and ':' in string:
            kind = 'datetime'
        elif '-' in string:
            kind = 'date'
        elif ':' in string:
            kind = 'time'
        
        fmt, obj, i, j = DT_FORMAT_INFO[kind]
        return obj(*time.strptime(string, fmt)[i:j])
    
    def parse_datetime(self, value, kind="datetime", as_timetuple=False):
        server_format = DT_SERVER_FORMATS[kind]
        local_format = self.date_format
        if not value:
            return False

        if isinstance(value, (time.struct_time, tuple)):
            value = time.strftime(local_format, value)

        try:
            value = time.strptime(value, local_format)
        except ValueError:
            try:
                # might be in server format already (e.g. filter domain)
                value = time.strptime(value, server_format)
            except ValueError:
                try:
                    dt = list(time.localtime())
                    dt[2] = int(value)
                    value = tuple(dt)
                except:
                    return False
    
        if kind == "datetime":
            try:
                value = self.tz_convert(value, 'parse')
            except Exception,e:
                print "*******************Error in timezone parsing *********",e
    
        if as_timetuple:
            return value
        
        return time.strftime(server_format, value)

    
    @openerpweb.jsonrequest
    def edit_events(self, req,**kw):
        data = {}
        ds = self.parsedatetime(kw['start_date'])
        de = self.parsedatetime(kw['end_date'])
        data[kw['calendar_fields']['date_start']['name']] = self.parse_datetime(ds.timetuple())
        
        if 'date_stop' in kw['calendar_fields']:
            data[kw['calendar_fields']['date_stop']['name']] = self.parse_datetime(de.timetuple())
        elif 'date_delay' in kw['calendar_fields']:
            day_length = kw['calendar_fields']['day_length']
            
            tds = time.mktime(ds.timetuple())
            tde = time.mktime(de.timetuple())
            
            n = (tde - tds) / (60 * 60)

            if n > day_length:
                d = math.floor(n / 24)
                h = n % 24

                n = d * day_length + h

            data[kw['calendar_fields']['date_delay']['name']] = n
        error = None
        try:
            req.session.model(kw['model']).write([int(kw['id'])], data)
        except Exception, e:
            error = e
        return error
    
    def tz_convert(self, struct_time, action):
        # if no client timezone is configured, consider the client is in the same
        # timezone as the server
        lzone = pytz.timezone(self.client_timezone or self.remote_timezone)
        szone = pytz.timezone(self.remote_timezone)
        dt = DT.datetime.fromtimestamp(time.mktime(struct_time))
    
        if action == 'parse':
            fromzone = lzone
            tozone = szone
        elif action == 'format':
            fromzone = szone
            tozone = lzone
        else:
            raise Exception("_tz_convert action should be 'parse' or 'format'. Not '%s'" % (action, ))
    
        localized_original_datetime = fromzone.localize(dt, is_dst=True)
        destination_datetime = localized_original_datetime.astimezone(tozone)
        return destination_datetime.timetuple()
    
    def format_datetime(self, value, kind="datetime", as_timetuple=False):
        """Convert date value to the local datetime considering timezone info.
    
        @param value: the date value
        @param kind: type of the date value (date, time or datetime)
        @param as_timetuple: return timetuple
    
        @type value: basestring or time.time_tuple)
    
        @return: string or timetuple
        """
    
        server_format = DT_SERVER_FORMATS[kind]
        local_format = self.date_format
    
        if not value:
            return ''
    
        if isinstance(value, (time.struct_time, tuple)):
            value = time.strftime(server_format, value)
    
        if isinstance(value, DT.datetime):
            value = value
            try:
                value = DT.datetime.strptime(value[:10], server_format)
                return value.strftime(local_format)
            except:
                return ''
    
        value = value.strip()
    
        # remove trailing miliseconds
        value = re.sub("(.*?)(\s+\d{2}:\d{2}:\d{2})(\.\d+)?$", "\g<1>\g<2>", value)
    
        # add time part in value if missing
        if kind == 'datetime' and not re.search('\s+\d{2}:\d{2}:\d{2}?$', value):
            value += ' 00:00:00'
    
        # remove time part from value
        elif kind == 'date':
            value = re.sub('\s+\d{2}:\d{2}:\d{2}(\.\d+)?$', '', value)
    
        value = time.strptime(value, server_format)
    
        if kind == "datetime":
            try:
                value = self.tz_convert(value, 'format')
            except Exception, e:
                print "\n\n\n************ Error in timezone formatting", e
    
        if as_timetuple:
            return value
    
        return time.strftime(local_format, value)
    
    def get_event_widget(self, event):
        title = ''       # the title
        description = [] # the description
        
        if self.info_fields:

            f = self.info_fields[0]
            s = event[f]
            
            if isinstance(s, (tuple, list)): s = s[-1]
            
            title = s
            for f in self.info_fields[1:]:
                s = event[f]
                if isinstance(s, (tuple, list)):
                    s = s[-1]
                if s:
                    description.append(str(s))
        
        starts = event.get(self.date_start)
        ends = event.get(self.date_delay) or 1.0
        span = 0
        
        if starts and ends:

            n = 0
            h = ends

            if ends == self.day_length:
                span = 1

            elif ends > self.day_length:
                n = ends / self.day_length
                h = ends % self.day_length

                n = int(math.floor(n))
                
                if h > 0:
                    span = n + 1
                else:
                    span = n
            ends = time.localtime(time.mktime(starts) + (h * 60 * 60) + (n * 24 * 60 * 60))
            
        if starts and self.date_stop:

            ends = event.get(self.date_stop)
            if not ends:
                ends = time.localtime(time.mktime(starts) + 60 * 60)

            tds = time.mktime(starts)
            tde = time.mktime(ends)

            if tds >= tde:
                tde = tds + 60 * 60
                ends = time.localtime(tde)

            n = (tde - tds) / (60 * 60)

            if n >= self.day_length:
                span = math.ceil(n / 24)
        
        starts = self.format_datetime(starts, "datetime", True)
        ends = self.format_datetime(ends, "datetime", True)
        title = title.strip()
        description = ', '.join(description).strip()
        return {'id': event['id'], 'start_date': str(DT.datetime(*starts[:6])), 'end_date': str(DT.datetime(*ends[:6])), 'text': title, 'title': description, 'color': self.colors[event[self.color_field]][-1]}
