/*globals: openerp, $, console */

/*---------------------------------------------------------
 * OpenERP web_calendar
 *---------------------------------------------------------*/

openerp.web_calendar = function(instance) {

    var _t = instance.web._t,
        _lt = instance.web._lt;
    var QWeb = instance.web.qweb;

    function get_class(name) {
        return new instance.web.Registry({'tmp' : name}).get_object("tmp");
    }

    var fc_defaultOptions = {
        monthNames: Date.CultureInfo.monthNames,
        monthNamesShort: Date.CultureInfo.abbreviatedMonthNames,
        dayNames: Date.CultureInfo.dayNames,
        dayNamesShort: Date.CultureInfo.abbreviatedDayNames,

        weekNumberTitle: _t("W"),
        allDayText: _t("all-day"),

        firstDay: Date.CultureInfo.firstDayOfWeek,
    };

    function is_virtual_id(id) {
        return typeof id == "string" && id.indexOf('-') >= 0;
    }

    instance.web.views.add('calendar', 'instance.web_calendar.FullCalendarView');

    instance.web_calendar.FullCalendarView = instance.web.View.extend({
        template: "FullCalendarView",
        display_name: _lt('Calendar'),
        quick_create_class: 'instance.web_calendar.QuickCreate',

        init: function (parent, dataset, view_id, options) {
            this._super(parent);
            this.ready = $.Deferred();
            this.set_default_options(options);
            this.dataset = dataset;
            this.model = dataset.model;
            this.fields_view = {};
            this.view_id = view_id;
            this.view_type = 'calendar';

            this.COLOR_PALETTE = ['#f57900', '#cc0000', '#d400a8', '#75507b', '#3465a4', '#73d216', '#c17d11', '#edd400',
                                  '#fcaf3e', '#ef2929', '#ff00c9', '#ad7fa8', '#729fcf', '#8ae234', '#e9b96e', '#fce94f',
                                  '#ff8e00', '#ff0000', '#b0008c', '#9000ff', '#0078ff', '#00ff00', '#e6ff00', '#ffff00',
                                  '#905000', '#9b0000', '#840067', '#510090', '#0000c9', '#009b00', '#9abe00', '#ffc900' ];

            this.color_map = {};
            this.last_search = [];
            this.range_start = null;
            this.range_stop = null;
            this.selected_filters = [];
                        
        },

        set_default_options: function(options) {
            this._super(options);
            _.defaults(this.options, {
                // All possible views options should be defaulted here
                confirm_on_delete: true,
            });
        },

        destroy: function() {
            this.$calendar.fullCalendar('destroy');
            this.$small_calendar.datepicker('destroy');
            this._super.apply(this, arguments);
        },

        view_loading: function (fv) {
            var self = this;
            this.fields_view = fv;
            this.$calendar = this.$el.find(".oe_fullcalendar_widget");

            this.info_fields = [];

            /* buttons */
            this.$buttons = $(QWeb.render("CalendarView.buttons", {'widget': this}));
            if (this.options.$buttons) {
                this.$buttons.appendTo(this.options.$buttons);
            } else {
                this.$el.find('.oe_calendar_buttons').replaceWith(this.$buttons);
            }

            this.$buttons.on('click', 'button.oe_calendar_button_new', function () {
                self.dataset.index = null;
                self.do_switch_view('form');
            });

            /* xml view calendar options */
            var attrs = fv.arch.attrs;

            if (!attrs.date_start) {
                throw new Error(_t("Calendar view has not defined 'date_start' attribute."));
            }

            this.$el.addClass(attrs['class']);

            this.name = fv.name || attrs.string;
            this.view_id = fv.view_id;

            this.mode = attrs.mode;                 // one of month, week or day
            this.date_start = attrs.date_start;     // Field name of starting date field
            this.date_delay = attrs.date_delay;     // duration
            this.date_stop = attrs.date_stop;
            this.all_day = attrs.all_day; 
            this.attendee_people = attrs.attendee;  
            this.how_display_event = '';

            if (typeof attrs.quick_create_instance !== "undefined") 
                self.quick_create_class = attrs.quick_create_instance;                
                
            if (typeof attrs.quick_add !== "undefined" && attrs.quick_add == "True")
                this.quick_add_pop = true; 
            else
                this.quick_add_pop = false;

            
            // The display format which will be used to display the event where fields are between "[" and "]"
            if (typeof attrs.display !== "undefined")
                this.how_display_event = attrs.display; // String with [FIELD]
            
            // If this field is set ot true, we don't open the event in form view, but in a popup with the view_id passed by this parameter
            if (attrs.event_open_popup == null || attrs.event_open_popup == "False")
                this.open_popup_action = false; 
            else {
                this.open_popup_action = attrs.event_open_popup;
            }
            
            // If this field is set to true, we will use de calendar_friends model as filter and not the color field.
            if (typeof attrs.use_contacts !== "undefined" && attrs.use_contacts == "True")
                this.useContacts = true; 
            else
                this.useContacts = false;

            // If this field is set ot true, we don't add itself as an attendee when we use attendee_people to add each attendee icon on an event
            // The color is the color of the attendee, so don't need to show again that it will be present
            if (typeof attrs.color_is_attendee == null || attrs.color_is_attendee == "False")
                this.colorIsAttendee = false; 
            else
                this.colorIsAttendee = true;

                    
            this.color_field = attrs.color;
        
            if (this.color_field && this.selected_filters.length === 0) {
                var default_filter;
                if ((default_filter = this.dataset.context['calendar_default_' + this.color_field])) {
                    this.selected_filters.push(default_filter + '');
                }
            }
            this.fields = fv.fields;

            for (var fld = 0; fld < fv.arch.children.length; fld++) {
                this.info_fields.push(fv.arch.children[fld].attrs.name);
            }
            
            return (new instance.web.Model(this.dataset.model))
                .call("check_access_rights", ["create", false])
                .then(function (create_right) {
                    self.create_right = create_right;
                    self.init_fullcalendar().then(function() {    
                        self.trigger('calendar_view_loaded', fv);
                        self.ready.resolve();
                    });
                });
        },

        get_fc_init_options: function () {
            var self = this;
            return $.extend({}, fc_defaultOptions, {
                
                defaultView: (this.mode == "month")?"month":
                    (this.mode == "week"?"agendaWeek":
                     (this.mode == "day"?"agendaDay":"month")),
                header: {
                    left: 'prev,next today',
                    center: 'title',
                    right: 'month,agendaWeek,agendaDay'
                },
                selectable: !this.options.read_only_mode && this.create_right,
                selectHelper: true,
                editable: !this.options.read_only_mode,
                droppable: true,

                // callbacks

                eventDrop: function (event, _day_delta, _minute_delta, _all_day, _revertFunc) {
                debugger;
                    var data = self.get_event_data(event);
                    self.proxy('update_record')(event._id, data); // we don't revert the event, but update it.
                },
                eventResize: function (event, _day_delta, _minute_delta, _revertFunc) {
                    var data = self.get_event_data(event);
                    self.proxy('update_record')(event._id, data);
                },
                eventRender: function (event, element, view) {
                    element.find('.fc-event-title').html(event.title);                    
                },
                eventAfterRender: function (event, element, view) {                    
                    if ((view.name !== 'month') && (((event.end-event.start)/60000)<=30)) {
                        //if duration is too small, we see the html code of img
                        var current_title = $(element.find('.fc-event-time')).text();
                        var new_title = current_title.substr(0,current_title.indexOf("<img")>0?current_title.indexOf("<img"):current_title.length)
                        element.find('.fc-event-time').html(new_title);
                    }                    
                },
                eventClick: function (event) { console.log(event); self.open_event(event._id,event.title); },
                select: function (start_date, end_date, all_day, _js_event, _view) {
                    var data_template = self.get_event_data({
                        start: start_date,
                        end: end_date,
                        allDay: all_day,
                    });

                    self.open_quick_create(data_template);

                },
                drop: function(start_date, all_day) {
                    if (this.classList.contains("ui-dialog")) {
                        return; //don't look click event on calendar if popup hover !
                    }
                    var data_template = self.get_event_data({
                        start: start_date,
                        allDay: all_day,
                    });
                    var stored_data = $(this).data('eventDefaults');

                    data_template = $.extend({}, stored_data, data_template);

                    // Opening quick create widget
                    self.open_quick_create(data_template);
                },
                unselectAuto: false,

                // Options

                weekNumbers: true,
                snapMinutes: 15,
                timeFormat : {
                           // for agendaWeek and agendaDay
                            agenda: 'h:mm{ - h:mm}', // 5:00 - 6:30

                            // for all other views
                            '': 'h(:mm)tt'            // 7pm
                        },
                firstHour: 8,
                weekMode : 'liquid',
                aspectRatio: 1.8,
                

            });
        },

        calendarMiniChanged: function (context) {
            return function(datum,obj) {
                var curView = context.$calendar.fullCalendar( 'getView');
                var curDate = new Date(obj.currentYear , obj.currentMonth, obj.currentDay);
                
                if (curView.name == "agendaWeek") {
                    if (curDate <= curView.end && curDate >= curView.start) {
                        context.$calendar.fullCalendar('changeView','agendaDay');
                    }
                }
                else if (curView.name != "agendaDay" || (curView.name == "agendaDay" && curDate.compareTo(curView.start)==0)) { 
                        context.$calendar.fullCalendar('changeView','agendaWeek');
                }                
                context.$calendar.fullCalendar('gotoDate', obj.currentYear , obj.currentMonth, obj.currentDay);
            }
        },              
        
        init_fullcalendar: function() {
            var self = this;
             
            if (!this.sidebar && this.options.$sidebar) {
                this.sidebar = new instance.web_calendar.Sidebar(this);
                this.sidebar.appendTo(this.$el.find('.oe_calendar_sidebar_container'));
                
                //Initialize small calendar
                this.$small_calendar = self.$el.find(".oe_calendar_mini");
                this.$small_calendar.datepicker({ onSelect: self.calendarMiniChanged(self) });
            
                if (this.useContacts) {
                    new instance.web.Model("res.users").query(["partner_id"]).filter([["id", "=",this.dataset.context.uid]]).first()
                            .done(
                                function(result) { 
                                    var sidebar_items = {};
                                    var filter_value = result.partner_id[0];
                                    var filter_item = {
                                            value: filter_value,
                                            label: result.partner_id[1] + " [Me]",
                                            color: self.get_color(filter_value)
                                        };
                                    sidebar_items[filter_value] = filter_item ;
                                    filter_item = {
                                            value: -1,
                                            label: "All partners [All]",
                                            color: self.get_color(-1)
                                        };
                                    sidebar_items[-1] = filter_item ;

                                    new instance.web.Model("web_calendar.contacts").query(["partner_id"]).filter([["user_id", "=",self.dataset.context.uid]]).all().then(function(result) {
                                        _.each(result, function(item) {
                                            filter_value = item.partner_id[0];
                                            filter_item = {
                                                value: filter_value,
                                                label: item.partner_id[1],
                                                color: self.get_color(filter_value)
                                            };
                                            sidebar_items[filter_value] = filter_item ;
                                        });
                                        
                                        self.allFilters = sidebar_items;
                                        self.sidebar.filter.events_loaded(sidebar_items);
                                        self.sidebar.filter.addUpdateButton();
                                    }).done(function () { 
                                        self.$calendar.fullCalendar('refetchEvents');            
                                    });
                                }
                             );
                                          
                }                            
            }
            self.$calendar.fullCalendar(self.get_fc_init_options());
                            
            
            return $.when();
        },

        open_quick_create: function(data_template) {
            if (this.quick) {
                return this.quick.trigger('close');
            }
            var QuickCreate = get_class(this.quick_create_class);
            
            this.options.disable_quick_create =  this.options.disable_quick_create || !this.quick_add_pop;
            this.quick = new QuickCreate(this, this.dataset, true, this.options, data_template);
            this.quick.on('added', this, this.proxy('quick_created'))
                    .on('slowadded', this, this.proxy('slow_created'))
                    .on('close', this, function() {
                        this.quick.destroy();
                        delete this.quick;
                        this.$calendar.fullCalendar('unselect');
                    });
            this.quick.replace($(".oe_calendar_qc_placeholder"));
            this.quick.focus();
        },

        /**
         * Refresh one fullcalendar event identified by it's 'id' by reading OpenERP record state.
         * If event was not existent in fullcalendar, it'll be created.
         */
        refresh_event: function(id) {
            var self = this;
            if (is_virtual_id(id))
                // Should avoid "refreshing" a virtual ID because it can't
                // really be modified so it should never be refreshed. As upon
                // edition, a NEW event with a non-virtual id will be created.
                console.warn("Unwise use of refresh_event on a virtual ID.");
            this.dataset.read_ids([id], _.keys(this.fields)).done(function (incomplete_records) {
                self.perform_necessary_name_gets(incomplete_records).then(function(records) {
                    // Event boundaries were already changed by fullcalendar, but we need to reload them:
                    var new_event = self.event_data_transform(records[0]);
                    // fetch event_obj
                    var event_objs = self.$calendar.fullCalendar('clientEvents', id);
                    if (event_objs.length == 1) { // Already existing obj to update
                        var event_obj = event_objs[0];
                        // update event_obj
                        _(new_event).each(function (value, key) {
                            event_obj[key] = value;
                        });
                        self.$calendar.fullCalendar('updateEvent', event_obj);
                    } else { // New event object to create
                        self.$calendar.fullCalendar('renderEvent', new_event);
                        // By forcing attribution of this event to this source, we
                        // make sure that the event will be removed when the source
                        // will be removed (which occurs at each do_search)
                        self.$calendar.fullCalendar('clientEvents', id)[0].source = self.event_source;
                    }
                });
            });
        },

        get_color: function(key) {
            if (this.color_map[key]) {
                return this.color_map[key];
            }
            var index = _.keys(this.color_map).length % this.COLOR_PALETTE.length;
            var color = this.COLOR_PALETTE[index];
            this.color_map[key] = color;
            return color;
        },

        /**
         * In o2m case, records from dataset won't have names attached to their *2o values.
         * We should make sure this is the case.
         */
        perform_necessary_name_gets: function(evts) {
            var def = $.Deferred();
            var self = this;
            var to_get = {};
            _(this.info_fields).each(function (fieldname) {
                if (!_(["many2one", "one2one"]).contains(
                    self.fields[fieldname].type))
                    return;
                to_get[fieldname] = [];
                _(evts).each(function (evt) {
                    var value = evt[fieldname];
                    if (value === false || (value instanceof Array))
                        return;
                    to_get[fieldname].push(value);
                });
                if (to_get[fieldname].length === 0)
                    delete to_get[fieldname];
            });
            var defs = _(to_get).map(function (ids, fieldname) {
                return (new instance.web.Model(self.fields[fieldname].relation))
                    .call('name_get', ids).then(function (vals) {
                        return [fieldname, vals];
                    });
            });

            $.when.apply(this, defs).then(function() {
                var values = arguments;
                _(values).each(function(value) {
                    var fieldname = value[0];
                    var name_gets = value[1];
                    _(name_gets).each(function(name_get) {
                        _(evts).chain()
                            .filter(function (e) {return e[fieldname] == name_get[0];})
                            .each(function(evt) {
                                evt[fieldname] = name_get;
                            });
                    });
                });
                def.resolve(evts);
            });
            return def;
        },
       
        isInArray: function(array_is, array_in) {
            for(var z=0; z<array_is.length; z++){
              if( array_in.indexOf(array_is[z]) !== -1) 
                  return true;
            }
            return false;
        },            
            
        
        /**
         * Transform OpenERP event object to fullcalendar event object
         */
        event_data_transform: function(evt) {
            var self = this;

            var date_start = instance.web.auto_str_to_date(evt[this.date_start]),
                date_stop = this.date_stop ? instance.web.auto_str_to_date(evt[this.date_stop]) : null,
                date_delay = evt[this.date_delay] || 1.0,
                all_day = this.all_day ? evt[this.all_day] : false,
                res_computed_text = '',
                the_title = '',
                attendees = [];                

            if (this.date_stop && this.fields[this.date_stop].type == 'date') {
                date_stop.addDay(1);
            }

            if (this.info_fields) {
                var temp_ret = {};
                res_computed_text = this.how_display_event;
                
                _.each(this.info_fields, function (fieldname) {
                    var value = evt[fieldname];
                    if (_.contains(["many2one", "one2one"], self.fields[fieldname].type)) {
                        if (value === false)
                            temp_ret[fieldname] = null;
                        else if (value instanceof Array) 
                            temp_ret[fieldname] = value[1]; // Yipee, no name_get to make
                        else
                            throw new Error("Incomplete data received from dataset for record " + evt.id);
                    }
                    else if (_.contains(["one2many","many2many"], self.fields[fieldname].type)) {
                        if (value === false) 
                            temp_ret[fieldname] = null;
                        else if (value instanceof Array) 
                            temp_ret[fieldname] = value; // if x2many, keep all id !
                        else
                            throw new Error("Incomplete data received from dataset for record " + evt.id);
                    }
                    else {
                        temp_ret[fieldname] = value;
                    }
                    res_computed_text = res_computed_text.replace("["+fieldname+"]",temp_ret[fieldname]);
                });                

                
                if (res_computed_text.length) {
                    the_title = res_computed_text;
                }
                else {
                    var res_text= [];
                    _.each(temp_ret, function(val,key) { res_text.push(val)} );
                    the_title = res_text.join(', ');                    
                }
                the_title = the_title.replace(/&/g,'&amp;').replace(/</g,'&lt;'); //.replace(/>/g,'&gt;');
                
                if (typeof this.attendee_people !== "undefined") {
                    var MAX_ATTENDEES = 3;
                    var attendee_showed = 0;
                    var attendee_other = '';

                    _.each(temp_ret[this.attendee_people], 
                        function (the_attendee_people) { 
                            attendees.push(the_attendee_people);
                            attendee_showed += 1;
                            //style = 'style="border:2px solid '+self.get_color((the_attendee_people in self.allFilters) ? the_attendee_people : '-1')+'"';
                            if (attendee_showed<= MAX_ATTENDEES) {
                            // if (the_attendee_people in self.allFilters && (!self.colorIsAttendee || temp_ret[self.color_field]!=the_attendee_people)) { //&& the_attendee_people != this.colorIsAttendee
                                the_title += '<img title="' + self.all_attendees[the_attendee_people] + '" class="attendee_head" width="20px" height="20px" src="/web/binary/image?model=res.partner&field=image_small&id=' + the_attendee_people + '"></img>';                                
                            }
                            else {
                                attendee_other += self.all_attendees[the_attendee_people] +", ";
                            }                                    
                        }
                    );
                    if (attendee_other.length) {
                        the_title += '<span class="attendee_head" title="' + attendee_other.substring(0, attendee_other.length - 2) + '">+</span>';                    
                    }
                }                
            }
            
            if (!date_stop && date_delay) {
                date_stop = date_start.clone().addHours(date_delay);
            }
            if (this.fields[this.date_start].type != "date" && all_day) {
                date_stop.addDays(-1);
            }
            var r = {
                'start': date_start.toString('yyyy-MM-dd HH:mm:ss'),
                'end': date_stop.toString('yyyy-MM-dd HH:mm:ss'),
                'title': the_title, //res_text.join(', '),
                'allDay': (this.fields[this.date_start].type == 'date' || (this.all_day && evt[this.all_day]) || false),
                'id': evt.id,
                'attendees':attendees
            };
            
            if (!self.useContacts || self.all_filters[evt[this.color_field]] != undefined) {
                if (this.color_field && evt[this.color_field]) {
                    var color_key = evt[this.color_field];
                    if (typeof color_key === "object") {
                        color_key = color_key[0];
                    }
                    r.color = this.get_color(color_key);                
                }
            }
            else  { // if form all, get color -1
                r.color = self.all_filters[-1].color;
            }
            
            return r;
        },
        
        /**
         * Transform fullcalendar event object to OpenERP Data object
         */
        get_event_data: function(event) {

            // Normalize event_end without changing fullcalendars event.
            var event_end = event.end;
            if (event.allDay) {
                // Sometimes fullcalendar doesn't give any event.end.
                if (event_end === null || typeof event_end === "undefined")
                    event_end = event.start;
                // Avoid inplace changes
                event_end = (new Date(event_end.getTime())).addDays(1);
            }

            var data = {
                name: event.title
            };
            data[this.date_start] = instance.web.parse_value(event.start, this.fields[this.date_start]);
    
            //Bug whenmove a all_day event from week or day, we don't have a dateend or duration...            
            if (event_end == null) {
                event_end = event.start.addHours(2);
            }

            if (this.date_stop) {
                data[this.date_stop] = instance.web.parse_value(event_end, this.fields[this.date_stop]);
            }
            if (this.all_day) {
                data[this.all_day] = event.allDay;
            }
            if (this.date_delay) {
                var diff_seconds = Math.round((event_end.getTime() - event.start.getTime()) / 1000);
                data[this.date_delay] = diff_seconds / 3600;
            }
            return data;
        },
        do_search: function(domain, context, _group_by) {
            var self = this;
            if (typeof this.event_source !== "undefined")
                this.$calendar.fullCalendar('removeEventSource', this.event_source);
            this.event_source = {
                events: function(start, end, callback) {
                    var current_event_source = self.event_source;
                    self.dataset.read_slice(_.keys(self.fields), {
                        offset: 0,
                        domain: self.get_range_domain(domain, start, end),
                        context: context,
                    }).done(function(events) {
                        if (self.event_source !== current_event_source) {
                            // Event source changed while waiting for AJAX response
                            console.log("Consecutive ``do_search`` called. Cancelling.");
                            return;
                        }
                        // We should make sure that *2many used in title of event have their extended form [ID, NAME]...
                        
                        events = $.map(events, function (e) {
                            
                            if (self.attendee_people != undefined) { //If we filter on contacts...
                                if (self.isInArray(self.selected_filters,e[self.attendee_people]) || (self.selected_filters.indexOf(-1) > -1)) {
                                    return e;
                                }
                                else {
                                    return null;
                                }   
                            }
                            else { //We adds all events # TO TEST ?       if (self.isInArray(self.selected_filters,e[self.color_field])){
                                
                                return e;
                            }                            
                            return null;                            
                        });
                        
                        
                        
                        if (!self.useContacts) {  // If we use all peoples as filter in sidebars
                            var now_filters = {};
                            var filter_value;
                            var filter_item;
                            
                            _.each(events, function (e) {
                                filter_value = e[self.color_field][0];
                                filter_item = {
                                    value: filter_value,
                                    label: e[self.color_field][1],
                                    color: self.get_color(filter_value)
                                };
                                if (!now_filters[e[self.color_field][0]]) 
                                    now_filters[e[self.color_field][0]] = filter_item;
                            });
                            
                            self.allFilters = now_filters;
                            self.sidebar.filter.events_loaded(now_filters);                            
                            
                            return self.perform_necessary_name_gets(events).then(callback);
                        }
                        else {
                            var all_attendees = [];
                            
                            _.each(events, function (e) {
                                all_attendees.push(e[self.attendee_people]);                                
                            });
                            
                            self.all_attendees = {}
                            
                            all_attendees = _.chain(all_attendees).flatten().uniq().value();
                            new instance.web.Model("res.partner").query(["name"]).filter([["id", "in",all_attendees]]).all().then(function(result) {
                                _.each(result, function(item) {
                                    self.all_attendees[item.id] = item.name;
                                });
                            }).done(function() { 
                                return self.perform_necessary_name_gets(events).then(callback);
                            });                                                        
                        }
                        

                    });
                },
                eventDataTransform: function (event) {
                    return self.event_data_transform(event);
                },
            };
            this.$calendar.fullCalendar('addEventSource', this.event_source);
        },
        /**
         * Build OpenERP Domain to filter object by this.date_start field
         * between given start, end dates.
         */
        get_range_domain: function(domain, start, end) {
            var format = instance.web.date_to_str;
            return new instance.web.CompoundDomain(
                domain,
                [[this.date_start, '>=', format(start.clone())],
                 [this.date_start, '<=', format(end.clone())]]);
        },

        // do_show: function () {
        //     this.$el.show();
        // },

        /**
         * Updates record identified by ``id`` with values in object ``data``
         */
        update_record: function(id, data) {
            var self = this;
            delete(data.name); // Cannot modify actual name yet
            var index = this.dataset.get_id_index(id);
            if (index !== null) {
                event_id = this.dataset.ids[index];
                this.dataset.write(event_id, data, {}).done(function() {
                    if (is_virtual_id(event_id)) {
                        // this is a virtual ID and so this will create a new event
                        // with an unknown id for us.
                        self.$calendar.fullCalendar('refetchEvents');
                    } else {
                        // classical event that we can refresh
                        self.refresh_event(event_id);
                    }
                });
            }
            return false;
        },
        open_event: function(id,title) {
            if (! this.open_popup_action) { 
                var index = this.dataset.get_id_index(id);
                this.dataset.index = index;
                this.do_switch_view('form');
            }            
            else {

                var self = this;

                var pop = new instance.web.form.FormOpenPopup(this);
                pop.show_element(this.dataset.model, id, this.dataset.get_context(), {
                    title: _.str.sprintf(_t("View: %s"),title),
                    view_id: this.open_popup_action,
                    res_id: id,
                    target: 'new',
                    readonly:true
                });              

               var form_controller = pop.view_form;
               form_controller.on("load_record", self, function(){
                    button_delete = _.str.sprintf("<button class='oe_button oe_bold delme'><span> %s </span></button>",_t("Delete"));
                    button_edit = _.str.sprintf("<button class='oe_button oe_bold editme oe_highlight'><span> %s </span></button>",_t("Edit event &gt;&gt;"));
                    
                    
                    pop.$el.closest(".ui-dialog").find(".ui-dialog-buttonpane").prepend(button_delete)
                    pop.$el.closest(".ui-dialog").find(".ui-dialog-buttonpane").prepend(button_edit)
                    
                    $('.delme').click(
                        function() { 
                            $('.oe_form_button_cancel').trigger('click'); 
                            self.remove_event(id); 
                        }
                    );
                    $('.editme').click(
                        function() { 
                             var action = {
                                type: 'ir.actions.act_window',
                                res_model: 'crm.meeting',
                                view_mode: 'form',
                                view_type: 'form',
                                views: [[false, 'form']],
                                res_id: id,
                                context: {},
                            };
                            $('.oe_form_button_cancel').trigger('click'); 
                            self.do_action(action);
                        }
                    );
                    
                    
               });
                 
            }   
            
            return false;         
            
        },

        do_show: function() {
            if (this.$buttons) {
                this.$buttons.show();
            }
            this.do_push_state({});
            return this._super();
        },
        do_hide: function () {
            if (this.$buttons) {
                this.$buttons.hide();
            }
            return this._super();
        },
        is_action_enabled: function(action) {
            if (action === 'create' && !this.options.creatable)
                return false;
            return this._super(action);
        },

        /**
         * Handles a newly created record
         *
         * @param {id} id of the newly created record
         */
        quick_created: function (id) {

            /** Note:
             * it's of the most utter importance NOT to use inplace
             * modification on this.dataset.ids as reference to this
             * data is spread out everywhere in the various widget.
             * Some of these reference includes values that should
             * trigger action upon modification.
             */
            this.dataset.ids = this.dataset.ids.concat([id]);
            // Inform every body that dataset changed
            this.dataset.trigger("dataset_changed", id);
            this.refresh_event(id);
        },
        slow_created: function () {
            // refresh all view, because maybe some recurrents item
            var self = this;
            self.$calendar.fullCalendar('refetchEvents');
        },

        remove_event: function(id) {
            var self = this;
            function do_it() {
                return $.when(self.dataset.unlink([id])).then(function() {
                    self.$calendar.fullCalendar('removeEvents', id);
                });
            }
            if (this.options.confirm_on_delete) {
                if (confirm(_t("Are you sure you want to delete this record ?"))) {
                    return do_it();
                }
            } else
                return do_it();
        },
    });


    /**
     * Quick creation view.
     *
     * Triggers a single event "added" with a single parameter "name", which is the
     * name entered by the user
     *
     * @class
     * @type {*}
     */
    instance.web_calendar.QuickCreate = instance.web.Widget.extend({
        template: 'CalendarView.quick_create',
        
        init: function(parent, dataset, buttons, options, data_template) {
            this._super(parent);            
            this.dataset = dataset;
            this._buttons = buttons || false;
            this.options = options;

            // Can hold data pre-set from where you clicked on agenda
            this.data_template = data_template || {};
        },
        get_title: function () {
            var parent = this.getParent();
            var title =
                (typeof parent.field_widget === "undefined") ?
                    (parent.string || parent.name) :
                parent.field_widget.string || parent.field_widget.name || '';
            return _t("Create: ") + title;
        },
        start: function () {
            var self = this;

            if (this.options.disable_quick_create) {
                this.$el.hide();
                this.slow_create();
                return;
            }

            self.$input = this.$el.find('input');
            self.$input.keyup(function(event) {
                if(event.keyCode == 13){
                    self.quick_add();
                }
            });
            this.$el.find(".oe_calendar_quick_create_add").click(function () {
                self.quick_add();
                self.focus();
            });
            this.$el.find(".oe_calendar_quick_create_edit").click(function () {
                self.slow_add();
                self.focus();
            });            
            this.$el.find(".oe_calendar_quick_create_close").click(function (ev) {
                ev.preventDefault();
                self.trigger('close');
            });
            self.$input.keyup(function(e) {
                if (e.keyCode == 27 && self._buttons) {
                    self.trigger('close');
                }
            });
            self.$el.dialog({ title: this.get_title()});
            self.on('added', self, function() {
                self.trigger('close');
            });
            
            self.$el.on('dialogclose', self, function() {
                console.log("dialogclose");
                self.trigger('close');
            });

        },
        focus: function() {
            this.$el.find('input').focus();
        },

        /**
         * Gathers data from the quick create dialog a launch quick_create(data) method
         */
        quick_add: function() {
            var val = this.$input.val();
            if (/^\s*$/.test(val)) { return; }
            this.quick_create({'name': val});
        },
        
        slow_add: function() {
            var val = this.$input.val();
            this.slow_create({'name': val});
        },

        /**
         * Handles saving data coming from quick create box
         */
        quick_create: function(data, options) {
            var self = this;
            this.dataset.create($.extend({}, this.data_template, data), options)
                .then(function(id) {
                    self.trigger('added', id);
                    self.$input.val("");
                }).fail(function(r, event) {
                    event.preventDefault();
                    // This will occurs if there are some more fields required
                    self.slow_create(data);
                });
        },

        /**
         * Show full form popup
         */
        slow_create: function(data) {
            var self = this;
            var def = $.Deferred();
            var defaults = {};
            _.each($.extend({}, this.data_template, data), function(val, field_name) {
                defaults['default_' + field_name] = val;
            });
            
            if (defaults['default_allday'] && (defaults['default_date_deadline'] || defaults['default_duration'])) {
                delete defaults['default_date_deadline'];
                delete defaults['default_duration'];
            }

            var pop = new instance.web.form.FormOpenPopup(this);
            var context = new instance.web.CompoundContext(this.dataset.context, defaults)
            pop.show_element(this.dataset.model, null, context, {
                title: this.get_title(),
                disable_multiple_selection: true,
                // Ensuring we use ``self.dataset`` and DO NOT create a new one.
                create_function: function(data, options) {
                    return self.dataset.create(data, options).done(function(r) {
                        // Although ``self.dataset.create`` DOES not call ``dataset_changed`` in O2M
                        // it gets called thanks to ``create_completed`` -> ``added``
                        // XXXvlab: why ``create`` does not call dataset_changed AND adds id in dataset.ids
                        // is a mystery for me ATM.
                    }).fail(function (r, event) {
                       if (!r.data.message) //else manage by openerp
                            throw new Error(r);
                    });
                },

                // ATM this method should not be attainable as the current pop up is
                // spawned only for newly created objects.

                // write_function: function(id, data, options) {
                //     return self.dataset.write(id, data, options).done(function() {
                //     }).fail(function (r, event) {
                //         throw new Error(r);
                //     });
                // },
                read_function: function(id, fields, options) {
                    return self.dataset.read_ids.apply(self.dataset, arguments).done(function() {
                    }).fail(function (r, event) {
                        if (!r.data.message)  //else manage by openerp
                            throw new Error(r);
                    });
                },
            });
            pop.on('closed', self, function() {
                // Hum, this is bad trick happening: we must avoid
                // calling ``self.trigger('close')`` directly because
                // it would itself destroy all child element including
                // the slow create popup, which would then re-trigger
                // recursively the 'closed' signal.  
                // 
                // Thus, here, we use a deferred and its state to cut
                // the endless recurrence.
                if (def.state() === "pending")
                    def.resolve();
            });
            pop.on('create_completed', self, function(id) {
                 self.trigger('slowadded');
            });
            def.then(function() {
                self.trigger('close');
            });
            return def;
        },
    });


    /**
     * Form widgets
     */

    function widget_calendar_lazy_init() {
        if (instance.web.form.Many2ManyCalendarView)
            return;

        instance.web_fullcalendar.FieldFullCalendarView = instance.web_fullcalendar.FullCalendarView.extend({

            init: function (parent) {
                this._super.apply(this, arguments);
                // Warning: this means only a field_widget should instanciate this Class
                this.field_widget = parent;
            },

            view_loading: function (fv) {
                var self = this;
                return $.when(this._super.apply(this, arguments)).then(function() {
                    self.on('event_rendered', this, function (event, element, view) {

                    });
                });
            },

            // In forms, we could be hidden in a notebook. Thus we couldn't
            // render correctly fullcalendar so we try to detect when we are
            // not visible to wait for when we will be visible.
            init_fullcalendar: function() {
                if (this.$calendar.width() !== 0) { // visible
                    return this._super();
                }

                // find all parents tabs.
                var def = $.Deferred();
                var self = this;
                this.$calendar.parents(".ui-tabs").on('tabsactivate', this, function() {
                    if (self.$calendar.width() !== 0) { // visible
                        self.$calendar.fullCalendar(self.get_fc_init_options());
                        def.resolve();
                    }
                });
                return def;
            },


        });

    }

    instance.web_calendar.BufferedDataSet = instance.web.BufferedDataSet.extend({

        /**
         * Adds verification on possible missing fields for the sole purpose of
         * O2M dataset being compatible with the ``slow_create`` detection of
         * missing fields... which is as simple to try to write and upon failure
         * go to ``slow_create``. Current BufferedDataSet would'nt fail because
         * they do not send data to the server at create time.
         */
        create: function (data, options) {
            var def = $.Deferred();
            var self = this;
            var create = this._super;
            if (typeof this.required_fields === "undefined") {
                this.required_fields = (new instance.web.Model(this.model))
                    .call('fields_get').then(function (fields_def) {
                        return _(fields_def).chain()
                         // equiv to .pairs()
                            .map(function (value, key) { return [key, value]; })
                         // equiv to .omit(self.field_widget.field.relation_field)
                            .filter(function (pair) { return pair[0] !== self.field_widget.field.relation_field; })
                            .filter(function (pair) { return pair[1].required; })
                            .map(function (pair) { return pair[0]; })
                            .value();
                    });
            }
            $.when(this.required_fields).then(function (required_fields) {
                var missing_fields = _(required_fields).filter(function (v) {
                    return typeof data[v] === "undefined";
                });
                var default_get = (missing_fields.length !== 0) ?
                    self.default_get(missing_fields) : [];
                $.when(default_get).then(function (defaults) {

                    // Remove all fields that have a default from the missing fields.
                    missing_fields = _(missing_fields).filter(function (f) {
                        return typeof defaults[f] === "undefined";
                    });
                    if (missing_fields.length !== 0) {
                        def.reject(
                            _.str.sprintf(
                                _t("Missing required fields %s"), missing_fields.join(", ")),
                            $.Event());
                        return;
                    }
                    create.apply(self, [data, options]).then(function (result) {
                        def.resolve(result);
                    });
                });
            });
            return def;
        },
    });

    instance.web_calendar.fields_dataset = new instance.web.Registry({
        'many2many': 'instance.web.DataSetStatic',
        'one2many': 'instance.web_calendar.BufferedDataSet',
    });


    function get_field_dataset_class(type) {
        var obj = instance.web_calendar.fields_dataset.get_any([type]);
        if (!obj) {
            throw new Error(_.str.sprintf(_t("Dataset for type '%s' is not defined."), type));
        }

        // Override definition of legacy datasets to add field_widget context
        return obj.extend({
            init: function (parent) {
                this._super.apply(this, arguments);
                this.field_widget = parent;
            },
            get_context: function() {
                this.context = this.field_widget.build_context();
                return this.context;
            }
        });
    }

    /**
     * Common part to manage any field using calendar view
     */
    instance.web_calendar.FieldCalendar = instance.web.form.AbstractField.extend({

        disable_utility_classes: true,
        fullcalendar_view_class: 'instance.web_calendar.FieldFullCalendarView',

        init: function(field_manager, node) {
            this._super(field_manager, node);
            widget_calendar_lazy_init();
            this.is_loaded = $.Deferred();
            this.initial_is_loaded = this.is_loaded;

            var self = this;

            // This dataset will use current widget to '.build_context()'.
            var field_type = field_manager.fields_view.fields[node.attrs.name].type;
            this.dataset = new (get_field_dataset_class(field_type))(
                this, this.field.relation);

            this.dataset.on('unlink', this, function(_ids) {
                this.dataset.trigger('dataset_changed');
            });

            // quick_create widget instance will be attached when spawned
            this.quick_create = null;

            this.no_rerender = true;

        },

        start: function() {
            this._super.apply(this, arguments);

            var self = this;

            self.load_view();
            self.on("change:effective_readonly", self, function() {
                self.is_loaded = self.is_loaded.then(function() {
                    self.calendar_view.destroy();
                    return $.when(self.load_view()).done(function() {
                        self.render_value();
                    });
                });
            });
        },

        load_view: function() {
            var self = this;
            var calendar_view_class = get_class(this.fullcalendar_view_class);
            this.calendar_view = new calendar_view_class(this, this.dataset, false, $.extend({
                'create_text': _t("Add"),
                'creatable': self.get("effective_readonly") ? false : true,
                'quick_creatable': self.get("effective_readonly") ? false : true,
                'read_only_mode': self.get("effective_readonly") ? true : false,
                'confirm_on_delete': false,
            }, this.options));
            var embedded = (this.field.views || {}).calendar;
            if (embedded) {
                this.calendar_view.set_embedded_view(embedded);
            }
            var loaded = $.Deferred();
            this.calendar_view.on("calendar_view_loaded", self, function() {
                self.initial_is_loaded.resolve();
                loaded.resolve();
            });
            this.calendar_view.on('switch_mode', this, this.open_popup);
            $.async_when().done(function () {
                self.calendar_view.appendTo(self.$el);
            });
            
            
            return loaded;
        },

        render_value: function() {
            console.log("In render value");
            var self = this;
            this.dataset.set_ids(this.get("value"));
            this.is_loaded = this.is_loaded.then(function() {
                return self.calendar_view.do_search(self.build_domain(), self.dataset.get_context(), []);
            });
        },

        open_popup: function(type, unused) {
            if (type !== "form")
                return;
            if (this.dataset.index === null) {
                if (typeof this.open_popup_add === "function")
                    this.open_popup_add();
            } else {
                if (typeof this.open_popup_edit === "function")
                    this.open_popup_edit();
            }
        },
        open_popup_add: function() {
            throw new Error("Not Implemented");
        },
        open_popup_edit: function() {
            var id = this.dataset.ids[this.dataset.index];
            var self = this;
            var pop = (new instance.web.form.FormOpenPopup(this));
            pop.show_element(this.field.relation, id, this.build_context(), {
                title: _t("Open: ") + this.string,
                write_function: function(id, data, _options) {
                    return self.dataset.write(id, data, {}).done(function() {
                        // Note that dataset will trigger itself the
                        // ``dataset_changed`` signal
                        self.calendar_view.refresh_event(id);
                    });
                },
                read_function: function(id, fields, options) {
                    return self.dataset.read_ids.apply(self.dataset, arguments).done(function() {
                    }).fail(function (r, event) {
                        throw new Error(r);
                    });
                },

                alternative_form_view: this.field.views ? this.field.views.form : undefined,
                parent_view: this.view, //XXXvlab: to check ! this.view is likely undefined
                child_name: this.name,
                readonly: this.get("effective_readonly")
            });
        }
    });

    instance.web_calendar.FieldMany2ManyCalendar = instance.web_calendar.FieldCalendar.extend({

        init: function(field_manager, node) {
            this._super(field_manager, node);
            this.dataset.on('dataset_changed', this, function() {
                // Will set dirty state if necessary
                this.set({'value': this.dataset.ids});
            });
        },

        set_value: function(value_) {
            value_ = value_ || [];
            if (value_.length >= 1 && value_[0] instanceof Array) {
                value_ = value_[0][2];
            }
            this._super(value_);
        },

        get_value: function() {
            // see to use ``commands.replace_with`` provided in
            // ``instance.web.form`` but not yet shared.
            return [[6, false, this.get('value')]];
        },
        open_popup_add: function() {
            var pop = (new instance.web.form.SelectCreatePopup(this));
            var self = this;
            pop.select_element(
                this.field.relation,
                {
                    title: _t("Add: ") + this.string
                },
                new instance.web.CompoundDomain(
                    this.build_domain(),
                    ["!", ["id", "in", this.dataset.ids]]),
                this.build_context()
            );
            pop.on("elements_selected", this, function(element_ids) {
                _.each(element_ids, function(id) {
                    if (!_.detect(self.dataset.ids, function(x) {return x == id;})) {
                        self.dataset.set_ids([].concat(self.dataset.ids, [id]));
                        self.calendar_view.refresh_event(id);
                    }
                    self.dataset.trigger("dataset_changed");
                });
            });
        }

    });


    instance.web_calendar.FieldOne2ManyCalendar = instance.web_calendar.FieldCalendar.extend({

        init: function(field_manager, node) {
            this._super(field_manager, node);
            this.dataset.on('dataset_changed', this, function() {
                // Force dirty state, as if dataset changed, then 'get_value'
                // result will change because it uses directly the dataset to
                // compute its result.
                this.trigger('changed_value');
            });
        },

        set_value: instance.web.form.FieldOne2Many.prototype.set_value,
        get_value: instance.web.form.FieldOne2Many.prototype.get_value,
        // XXX needed by set_value for no reason at all, TO REMOVE when
        // FieldOne2Many.set_value will be cleaned.
        trigger_on_change: function() {},
        reload_current_view: function() {},

        open_popup_add: false, // deactivate button "Add"

    });


    instance.web.form.widgets.add('many2many_calendar','instance.web_calendar.FieldMany2ManyCalendar');
    instance.web.form.widgets.add('one2many_calendar','instance.web_calendar.FieldOne2ManyCalendar');
   
        
    instance.web_calendar.Sidebar = instance.web.Widget.extend({
        template: 'CalendarView.sidebar',
        
        start: function() {
            this._super();
            this.filter = new instance.web_calendar.SidebarFilter(this, this.getParent());
            this.filter.appendTo(this.$el.find('.oe_calendar_filter'));
        }
    });
    instance.web_calendar.SidebarFilter = instance.web.Widget.extend({
        events: {
            'change input:checkbox': 'filter_click'
        },
        init: function(parent, view) {
            this._super(parent);
            this.view = view;            
        },
        events_loaded: function(filters) {
            var self = this;
            self.selected_filters = [];
            self.view.all_filters = filters;
            this.$el.html(QWeb.render('CalendarView.sidebar.responsible', { filters: filters }));
            this.filter_click(null);                        
        },
        filter_click: function(e) {
            var self = this,
            responsibles = [];
            //$e = $(e.target);
            self.view.selected_filters = [];
            this.$('div.oe_calendar_responsible input:checked').each(function() {
                responsibles.push($(this).val());
                
                if (e==null && parseInt($(this).val())<0) {
                    $(this).prop('checked',false);
;                   return;
                }                    
                self.view.selected_filters.push(parseInt($(this).val()));
            });
            
            if (e !== null) { //First intialize 
                self.view.$calendar.fullCalendar('refetchEvents');  //RERENDER ALL...
            }

            
        },
        addUpdateButton: function() {
            var self=this;
            var button = "<button class='oe_button oe_form_button oe_link' style='margin-top:7px'><span class='add_contacts_link' >Manage contacts</span></button>";
            this.$('div.oe_calendar_all_responsibles').append(button);
            this.$(".add_contacts_link").on('click', function() {  
                self.rpc("/web/action/load", { 
                    action_id: "web_calendar.action_calendar_contacts" 
                }).then( function(result) { return self.do_action(result); });
            });
            
        }
    });

};

// vim:et fdc=0 fdl=0 foldnestmax=3 fdm=syntax:
