odoo.define('web_calendar.CalendarView', function (require) {
"use strict";
/*---------------------------------------------------------
 * OpenERP web_calendar
 *---------------------------------------------------------*/

var core = require('web.core');
var data = require('web.data');
var form_common = require('web.form_common');
var formats = require('web.formats');
var Model = require('web.DataModel');
var time = require('web.time');
var utils = require('web.utils');
var View = require('web.View');
var widgets = require('web_calendar.widgets');
var local_storage = require('web.local_storage');

var CompoundDomain = data.CompoundDomain;

var _t = core._t;
var _lt = core._lt;
var QWeb = core.qweb;

function get_fc_defaultOptions() {
    var dateFormat = time.strftime_to_moment_format(_t.database.parameters.date_format);

    // moment.js converts '%p' to 'A' for 'AM/PM'
    // But FullCalendar v1.6.4 supports 'TT' format for 'AM/PM' but not 'A'
    // NB: should be removed when fullcalendar is updated to 2.0 because it would
    // be supported. See the following link
    // http://fullcalendar.io/wiki/Upgrading-to-v2/
    var timeFormat = time.strftime_to_moment_format(_t.database.parameters.time_format).replace('A', 'TT');

    // adapt format for fullcalendar v1.
    // see http://fullcalendar.io/docs1/utilities/formatDate/
    var conversions = [['YYYY', 'yyyy'], ['YY', 'y'], ['DDDD', 'dddd'], ['DD', 'dd']];
    _.each(conversions, function(conv) {
        dateFormat = dateFormat.replace(conv[0], conv[1]);
    });

    // If 'H' is contained in timeFormat display '10:00'
    // Else display '10 AM'. 
    // See : http://fullcalendar.io/docs1/utilities/formatDate/
    var hourFormat = function(timeFormat){
        if (/H/.test(timeFormat))
            return 'HH:mm';
        return 'hh TT';
    };

    return {
        weekNumberTitle: _t("W"),
        allDayText: _t("All day"),
        monthNames: moment.months(),
        monthNamesShort: moment.monthsShort(),
        dayNames: moment.weekdays(),
        dayNamesShort: moment.weekdaysShort(),
        firstDay: moment().startOf('week').isoWeekday(),
        weekNumberCalculation: function(date) {
            return moment(date).week();
        },
        axisFormat: hourFormat(timeFormat),
        // Correct timeformat for agendaWeek and agendaDay
        // http://fullcalendar.io/docs1/text/timeFormat/
        timeFormat: timeFormat + ' {- ' + timeFormat + '}',
        weekNumbers: true,
        titleFormat: {
            month: 'MMMM yyyy',
            week: "w",
            day: dateFormat,
        },
        columnFormat: {
            month: 'ddd',
            week: 'ddd ' + dateFormat,
            day: 'dddd ' + dateFormat,
        },
        weekMode : 'liquid',
        snapMinutes: 15,
    };
}

function is_virtual_id(id) {
    return typeof id === "string" && id.indexOf('-') >= 0;
}

function isNullOrUndef(value) {
    return _.isUndefined(value) || _.isNull(value);
}

var CalendarView = View.extend({
    custom_events: {
        reload_events: function () {
            this.$calendar.fullCalendar('refetchEvents');
        },
    },
    defaults: _.extend({}, View.prototype.defaults, {
        confirm_on_delete: true,
    }),
    display_name: _lt('Calendar'),
    events: {
        'click .o_calendar_sidebar_toggler': 'toggle_full_width',
    },
    icon: 'fa-calendar',
    quick_create_instance: widgets.QuickCreate,
    template: "CalendarView",

    init: function () {
        this._super.apply(this, arguments);
        this.color_map = {};
        this.range_start = null;
        this.range_stop = null;
        this.selected_filters = [];
        this.info_fields = [];

        this.title = (this.options.action)? this.options.action.name : '';

        this.shown = $.Deferred();
        this.current_start = null;
        this.current_end = null;
        this.previous_ids = [];

        var attrs = this.fields_view.arch.attrs;
        if (!attrs.date_start) {
            throw new Error(_t("Calendar view has not defined 'date_start' attribute."));
        }
        this.fields = this.fields_view.fields;
        this.name = this.fields_view.name || attrs.string;
        this.mode = attrs.mode;                 // one of month, week or day
        this.date_start = attrs.date_start;     // Field name of starting date field
        this.date_delay = attrs.date_delay;     // duration
        this.date_stop = attrs.date_stop;
        this.all_day = attrs.all_day;
        this.how_display_event = '';
        this.attendee_people = attrs.attendee;

        // Check whether the date field is editable (i.e. if the events can be dragged and dropped)
        this.editable = !this.options.read_only_mode && !this.fields[this.date_start].readonly;

        //if quick_add = False, we don't allow quick_add
        //if quick_add = not specified in view, we use the default quick_create_instance
        //if quick_add = is NOT False and IS specified in view, we this one for quick_create_instance'   

        this.quick_add_pop = (isNullOrUndef(attrs.quick_add) || utils.toBoolElse(attrs.quick_add, true));
        // The display format which will be used to display the event where fields are between "[" and "]"
        if (!isNullOrUndef(attrs.display)) {
            this.how_display_event = attrs.display; // String with [FIELD]
        }

        // If this field is set ot true, we don't open the event in form view, but in a popup with the view_id passed by this parameter
        if (isNullOrUndef(attrs.event_open_popup) || !utils.toBoolElse(attrs.event_open_popup, true)) {
            this.open_popup_action = false;
        } else {
            this.open_popup_action = attrs.event_open_popup;
        }
        // If this field is set to true, we will use the calendar_friends model as filter and not the color field.
        this.useContacts = !isNullOrUndef(attrs.use_contacts) && _.str.toBool(attrs.use_contacts);

        // If this field is set ot true, we don't add itself as an attendee when we use attendee_people to add each attendee icon on an event
        // The color is the color of the attendee, so don't need to show again that it will be present
        this.colorIsAttendee = !(isNullOrUndef(attrs.color_is_attendee) || !utils.toBoolElse(attrs.color_is_attendee, true));

        // if we have not sidebar, (eg: Dashboard), we don't use the filter "coworkers"
        if (isNullOrUndef(this.options.sidebar)) {
            this.useContacts = false;
            this.colorIsAttendee = false;
            this.attendee_people = undefined;
        }

        /*
                Will be more logic to do it in futur, but see below to stay Retro-compatible
                
                if (isNull(attrs.avatar_model)) {
                    this.avatar_model = 'res.partner'; 
                }
                else {
                    if (attrs.avatar_model == 'False') {
                        this.avatar_model = null;
                    }
                    else {  
                        this.avatar_model = attrs.avatar_model;
                    }
                }            
        */
        if (isNullOrUndef(attrs.avatar_model)) {
            this.avatar_model = null;
        } else {
            this.avatar_model = attrs.avatar_model;
        }

        if (isNullOrUndef(attrs.avatar_title)) {
            this.avatar_title = this.avatar_model;
        } else {
            this.avatar_title = attrs.avatar_title;
        }

        if (isNullOrUndef(attrs.avatar_filter)) {
            this.avatar_filter = this.avatar_model;
        } else {
            this.avatar_filter = attrs.avatar_filter;
        }

        this.color_field = attrs.color;

        if (this.color_field && this.selected_filters.length === 0) {
            var default_filter;
            if ((default_filter = this.dataset.context['calendar_default_' + this.color_field])) {
                this.selected_filters.push(default_filter + '');
            }
        }

        for (var fld = 0; fld < this.fields_view.arch.children.length; fld++) {
            this.info_fields.push(this.fields_view.arch.children[fld].attrs.name);
        }
    },
    willStart: function () {
        var self = this;
        var write_def = this.dataset.call("check_access_rights", ["write", false]);
        var create_def = this.dataset.call("check_access_rights", ["create", false]);
        return $.when(write_def, create_def, this._super()).then(function (write, create) {
            self.write_right = write;
            self.create_right = create;
        });
    },
    start: function () {
        this.$calendar = this.$(".o_calendar_widget");
        this.$sidebar_container = this.$(".o_calendar_sidebar_container");
        this.$el.addClass(this.fields_view.arch.attrs.class);
        this.shown.done(this._do_show_init.bind(this));
        return this._super();
    },
    destroy: function() {
        if (this.$calendar) {
            this.$calendar.fullCalendar('destroy');
        }
        if (this.$small_calendar) {
            this.$small_calendar.datepicker('destroy');
        }
        this._super.apply(this, arguments);
    },

    _do_show_init: function () {
        this.init_calendar().then(function() {
            $(window).trigger('resize');
        });
    },
    /**
     * Render the buttons according to the CalendarView.buttons template and
     * add listeners on it.
     * Set this.$buttons with the produced jQuery element
     * @param {jQuery} [$node] a jQuery node where the rendered buttons should be inserted
     * $node may be undefined, in which case the ListView inserts them into this.options.$buttons
     * or into a div of its template
     */
    render_buttons: function($node) {
        var self = this;
        this.$buttons = $(QWeb.render("CalendarView.buttons", {'widget': this}));
        this.$buttons.on('click', 'button.o_calendar_button_new', function () {
            self.dataset.index = null;
            self.do_switch_view('form');
        });

        var bindCalendarButton = function(selector, arg1, arg2) {
            self.$buttons.on('click', selector, _.bind(self.$calendar.fullCalendar, self.$calendar, arg1, arg2));
        };
        bindCalendarButton('.o_calendar_button_prev', 'prev');
        bindCalendarButton('.o_calendar_button_today', 'today');
        bindCalendarButton('.o_calendar_button_next', 'next');
        bindCalendarButton('.o_calendar_button_day', 'changeView', 'agendaDay');
        bindCalendarButton('.o_calendar_button_week', 'changeView', 'agendaWeek');
        bindCalendarButton('.o_calendar_button_month', 'changeView', 'month');

        this.$buttons.find('.o_calendar_button_' + this.mode).addClass('active');
        
        if ($node) {
            this.$buttons.appendTo($node);
        } else {
            this.$('.o_calendar_buttons').replaceWith(this.$buttons);
        }
    },
    toggle_full_width: function () {
        var full_width = (local_storage.getItem('web_calendar_full_width') !== 'true');
        local_storage.setItem('web_calendar_full_width', full_width);
        this.toggle_sidebar(!full_width);
        this.$calendar.fullCalendar('render'); // to reposition the events
    },
    toggle_sidebar: function (display) {
        this.sidebar.do_toggle(display);
        this.$('.o_calendar_sidebar_toggler')
            .toggleClass('fa-close', display)
            .toggleClass('fa-chevron-left', !display)
            .attr('title', display ? _('Close Sidebar') : _('Open Sidebar'));
        this.$sidebar_container.toggleClass('o_sidebar_hidden', !display);
    },
    get_fc_init_options: function () {
        //Documentation here : http://arshaw.com/fullcalendar/docs/
        var self = this;
        return $.extend({}, get_fc_defaultOptions(), {
            defaultView: (this.mode == "month")? "month" : ((this.mode == "week")? "agendaWeek" : ((this.mode == "day")? "agendaDay" : "agendaWeek")),
            header: false,
            selectable: !this.options.read_only_mode && this.create_right,
            selectHelper: true,
            editable: this.editable,
            droppable: true,

            // callbacks
            viewRender: function(view) {
                var mode = (view.name == "month")? "month" : ((view.name == "agendaWeek") ? "week" : "day");
                if(self.$buttons !== undefined) {
                    self.$buttons.find('.active').removeClass('active');
                    self.$buttons.find('.o_calendar_button_' + mode).addClass('active');
                }

                var title = self.title + ' (' + ((mode === "week")? _t("Week ") : "") + view.title + ")"; 
                self.set({'title': title});

                self.$calendar.fullCalendar('option', 'height', Math.max(290, parseInt(self.$('.o_calendar_view').height())));

                setTimeout(function() {
                    var $fc_view = self.$calendar.find('.fc-view');
                    var width = $fc_view.find('> table').width();
                    $fc_view.find('> div').css('width', (width > $fc_view.width())? width : '100%'); // 100% = fullCalendar default
                }, 0);
            },
            windowResize: function() {
                self.$calendar.fullCalendar('render');
            },
            eventDrop: function (event, _day_delta, _minute_delta, _all_day, _revertFunc) {
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
                    var new_title = current_title.substr(0,current_title.indexOf("<img")>0?current_title.indexOf("<img"):current_title.length);
                    element.find('.fc-event-time').html(new_title);
                }
            },
            eventClick: function (event) { self.open_event(event._id,event.title); },
            select: function (start_date, end_date, all_day, _js_event, _view) {
                var data_template = self.get_event_data({
                    start: start_date,
                    end: end_date,
                    allDay: all_day,
                });
                self.open_quick_create(data_template);
            },

            unselectAuto: false,
        });
    },

    calendarMiniChanged: function (context) {
        return function(datum,obj) {
            var curView = context.$calendar.fullCalendar('getView');
            var curDate = new Date(obj.currentYear , obj.currentMonth, obj.currentDay);

            if (curView.name == "agendaWeek") {
                if (curDate <= curView.end && curDate >= curView.start) {
                    context.$calendar.fullCalendar('changeView','agendaDay');
                }
            }
            else if (curView.name != "agendaDay" || (curView.name == "agendaDay" && moment(curDate).diff(moment(curView.start))===0)) {
                context.$calendar.fullCalendar('changeView','agendaWeek');
            }
            context.$calendar.fullCalendar('gotoDate', obj.currentYear , obj.currentMonth, obj.currentDay);
        };
    },

    init_calendar: function() {
        var defs = [];
        if (!this.sidebar) {
            var translate = get_fc_defaultOptions();
            this.sidebar = new widgets.Sidebar(this);
            defs.push(this.sidebar.appendTo(this.$sidebar_container));

            this.$small_calendar = this.$(".o_calendar_mini");
            this.$small_calendar.datepicker({ 
                onSelect: this.calendarMiniChanged(this),
                dayNamesMin : translate.dayNamesShort,
                monthNames: translate.monthNamesShort,
                firstDay: translate.firstDay,
            });

            defs.push(this.extraSideBar());

            // Add show/hide button and possibly hide the sidebar
            this.$sidebar_container.append($('<i>').addClass('o_calendar_sidebar_toggler fa'));
            this.toggle_sidebar((local_storage.getItem('web_calendar_full_width') !== 'true'));
        }
        this.$calendar.fullCalendar(this.get_fc_init_options());

        return $.when.apply($, defs);
    },
    extraSideBar: function() {
        return $.when();
    },

    get_quick_create_class: function () {
        return widgets.QuickCreate;
    },
    open_quick_create: function(data_template) { // FIXME
        if (!isNullOrUndef(this.quick)) {
            return this.quick.close();
        }
        var QuickCreate = this.get_quick_create_class();

        this.options.disable_quick_create =  this.options.disable_quick_create || !this.quick_add_pop;
        this.quick = new QuickCreate(this, this.dataset, true, this.options, data_template);
        this.quick.on('added', this, this.quick_created)
                .on('slowadded', this, this.slow_created)
                .on('closed', this, function() {
                    delete this.quick;
                    this.$calendar.fullCalendar('unselect');
                });

        if(!this.options.disable_quick_create) {
            this.quick.open();
            this.quick.focus();
        } else {
            this.quick.start();
        }
    },

    /**
     * Refresh one fullcalendar event identified by it's 'id' by reading OpenERP record state.
     * If event was not existent in fullcalendar, it'll be created.
     */
    refresh_event: function(id) {
        var self = this;
        if (is_virtual_id(id)) {
            // Should avoid "refreshing" a virtual ID because it can't
            // really be modified so it should never be refreshed. As upon
            // edition, a NEW event with a non-virtual id will be created.
            console.warn("Unwise use of refresh_event on a virtual ID.");
        }
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
                    var $fc_view = self.$calendar.find('.fc-view');
                    var scrollPosition = $fc_view.scrollLeft();
                    $fc_view.scrollLeft(0);
                    self.$calendar.fullCalendar('renderEvent', new_event);
                    $fc_view.scrollLeft(scrollPosition);
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
        var index = (((_.keys(this.color_map).length + 1) * 5) % 24) + 1;
        this.color_map[key] = index;
        return index;
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
            if (!_(["many2one"]).contains(
                self.fields[fieldname].type))
                return;
            to_get[fieldname] = [];
            _(evts).each(function (evt) {
                var value = evt[fieldname];
                if (value === false || (value instanceof Array)) {
                    return;
                }
                to_get[fieldname].push(value);
            });
            if (to_get[fieldname].length === 0) {
                delete to_get[fieldname];
            }
        });
        var defs = _(to_get).map(function (ids, fieldname) {
            return (new Model(self.fields[fieldname].relation))
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
    
    /**
     * Transform OpenERP event object to fullcalendar event object
     */
    event_data_transform: function(evt) {
        var self = this;
        var date_start;
        var date_stop;
        var date_delay = evt[this.date_delay] || 1.0,
            all_day = this.all_day ? evt[this.all_day] : false,
            res_computed_text = '',
            the_title = '',
            attendees = [];

        if (!all_day) {
            date_start = time.auto_str_to_date(evt[this.date_start]);
            date_stop = this.date_stop ? time.auto_str_to_date(evt[this.date_stop]) : null;
        } else {
            date_start = time.auto_str_to_date(evt[this.date_start].split(' ')[0],'start');
            date_stop = this.date_stop ? time.auto_str_to_date(evt[this.date_stop].split(' ')[0],'start') : null;
        }

        if (this.info_fields) {
            var temp_ret = {};
            res_computed_text = this.how_display_event;
            
            _.each(this.info_fields, function (fieldname) {
                var value = evt[fieldname];
                if (_.contains(["many2one"], self.fields[fieldname].type)) {
                    if (value === false) {
                        temp_ret[fieldname] = null;
                    }
                    else if (value instanceof Array) {
                        temp_ret[fieldname] = value[1]; // no name_get to make
                    }
                    else if (_.contains(["date", "datetime"], self.fields[fieldname].type)) {
                        temp_ret[fieldname] = formats.format_value(value, self.fields[fieldname]);
                    }
                    else {
                        throw new Error("Incomplete data received from dataset for record " + evt.id);
                    }
                }
                else if (_.contains(["one2many","many2many"], self.fields[fieldname].type)) {
                    if (value === false) {
                        temp_ret[fieldname] = null;
                    }
                    else if (value instanceof Array)  {
                        temp_ret[fieldname] = value; // if x2many, keep all id !
                    }
                    else {
                        throw new Error("Incomplete data received from dataset for record " + evt.id);
                    }
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
                _.each(temp_ret, function(val,key) {
                    if( typeof(val) === 'boolean' && val === false ) { }
                    else { res_text.push(val); }
                });
                the_title = res_text.join(', ');
            }
            the_title = _.escape(the_title);
            
            
            var the_title_avatar = '';
            
            if (! _.isUndefined(this.attendee_people)) {
                var MAX_ATTENDEES = 3;
                var attendee_showed = 0;
                var attendee_other = '';

                _.each(temp_ret[this.attendee_people],
                    function (the_attendee_people) {
                        attendees.push(the_attendee_people);
                        attendee_showed += 1;
                        if (attendee_showed<= MAX_ATTENDEES) {
                            if (self.avatar_model !== null) {
                                       the_title_avatar += '<img title="' + _.escape(self.all_attendees[the_attendee_people]) + '" class="o_attendee_head"  \
                                                        src="/web/image/' + self.avatar_model + '/' + the_attendee_people + '/image_small"></img>';
                            }
                            else {
                                if (!self.colorIsAttendee || the_attendee_people != temp_ret[self.color_field]) {
                                        var tempColor = (self.all_filters[the_attendee_people] !== undefined) 
                                                    ? self.all_filters[the_attendee_people].color
                                                    : (self.all_filters[-1] ? self.all_filters[-1].color : 1);
                                        the_title_avatar += '<i class="fa fa-user o_attendee_head o_underline_color_'+tempColor+'" title="' + _.escape(self.all_attendees[the_attendee_people]) + '" ></i>';
                                }//else don't add myself
                            }
                        }
                        else {
                                attendee_other += _.escape(self.all_attendees[the_attendee_people]) +", ";
                        }
                    }
                );
                if (attendee_other.length>2) {
                    the_title_avatar += '<span class="o_attendee_head" title="' + attendee_other.slice(0, -2) + '">+</span>';
                }
                the_title = the_title_avatar + the_title;
            }
        }
        
        if (!date_stop && date_delay) {
            var m_start = moment(date_start).add(date_delay,'hours');
            date_stop = m_start.toDate();
        }
        var r = {
            'start': moment(date_start).format('YYYY-MM-DD HH:mm:ss'),
            'end': moment(date_stop).format('YYYY-MM-DD HH:mm:ss'),
            'title': the_title,
            'allDay': (this.fields[this.date_start].type == 'date' || (this.all_day && evt[this.all_day]) || false),
            'id': evt.id,
            'attendees':attendees
        };

        var color_key = evt[this.color_field];
        if (!self.useContacts || self.all_filters[color_key] !== undefined) {
            if (color_key) {
                if (typeof color_key === "object") {
                    color_key = color_key[0];
                }
                r.className = 'o_calendar_color_'+ this.get_color(color_key);
            }
        } else { // if form all, get color -1
            r.className = 'o_calendar_color_'+ (self.all_filters[-1] ? self.all_filters[-1].color : 1);
        }
        if (evt.is_highlighted) {
            r.className += ' o_event_hightlight';
        }
        return r;
    },
    
    /**
     * Transform fullcalendar event object to OpenERP Data object
     */
    get_event_data: function(event) {
        var date_start_day;
        var date_stop_day;
        var diff_seconds;

        // Normalize event_end without changing fullcalendars event.
        var data = {
            name: event.title
        };            
        
        var event_end = event.end;
        //Bug when we move an all_day event from week or day view, we don't have a dateend or duration...            
        if (event_end === null) {
            var m_date = moment(event.start).add(2, 'hours');
            event_end = m_date.toDate();
        }

        if (event.allDay) {
            // Sometimes fullcalendar doesn't give any event.end.
            if (event_end === null || _.isUndefined(event_end)) {
                event_end = new Date(event.start);
            }
            if (this.all_day) {
                date_start_day = new Date(Date.UTC(event.start.getFullYear(),event.start.getMonth(),event.start.getDate()));
                date_stop_day = new Date(Date.UTC(event_end.getFullYear(),event_end.getMonth(),event_end.getDate()));                    
            }
            else {
                date_start_day = new Date(event.start.getFullYear(),event.start.getMonth(),event.start.getDate(),7);
                date_stop_day = new Date(event_end.getFullYear(),event_end.getMonth(),event_end.getDate(),19);
            }
            data[this.date_start] = time.datetime_to_str(date_start_day);
            if (this.date_stop) {
                data[this.date_stop] = time.datetime_to_str(date_stop_day);
            }
            diff_seconds = Math.round((date_stop_day.getTime() - date_start_day.getTime()) / 1000);
                            
        }
        else {
            data[this.date_start] = time.datetime_to_str(event.start);
            if (this.date_stop) {
                data[this.date_stop] = time.datetime_to_str(event_end);
            }
            diff_seconds = Math.round((event_end.getTime() - event.start.getTime()) / 1000);
        }

        if (this.all_day) {
            data[this.all_day] = event.allDay;
        }

        if (this.date_delay) {
            data[this.date_delay] = diff_seconds / 3600;
        }
        return data;
    },

    do_search: function (domain, context, _group_by) {
        var self = this;
        this.shown.done(function () {
            self._do_search(domain, context, _group_by);
        });
    },
    _do_search: function(domain, context, _group_by) {
        var self = this;
        if (! self.all_filters) {
            self.all_filters = {};
        }

        if (! _.isUndefined(this.event_source)) {
            this.$calendar.fullCalendar('removeEventSource', this.event_source);
        }
        this.event_source = {
            events: function(start, end, callback) {
                // catch invalid dates (start/end dates not parseable yet)
                // => ignore request
                if (isNaN(start) || isNaN(end)) {
                    return;
                }

                var current_event_source = self.event_source;
                    var event_domain = self.get_range_domain(domain, start, end);
                    if (self.useContacts && (!self.all_filters[-1] || !self.all_filters[-1].is_checked)) {
                        var partner_ids = $.map(self.all_filters, function(o) { if (o.is_checked) { return o.value; }});
                        if (!_.isEmpty(partner_ids)) {
                            event_domain = new data.CompoundDomain(
                                event_domain,
                                [[self.attendee_people, 'in', partner_ids]]
                            );
                        }
                    }

                // read_slice is launched uncoditionally, when quickly
                // changing the range in the calender view, all of
                // these RPC calls will race each other. Because of
                // this we keep track of the current range of the
                // calendar view.
                self.current_start = start;
                self.current_end = end;
                self.dataset.read_slice(_.keys(self.fields), {
                    offset: 0,
                    domain: event_domain,
                    context: context,
                }).done(function(events) {
                    // undo the read_slice if it the range has changed since it launched
                    if (self.current_start.getTime() != start.getTime() || self.current_end.getTime() != end.getTime()) {
                        self.dataset.ids = self.previous_ids;
                        return;
                    }
                    self.previous_ids = self.dataset.ids.slice();
                    if (self.dataset.index === null) {
                        if (events.length) {
                            self.dataset.index = 0;
                        }
                    } else if (self.dataset.index >= events.length) {
                        self.dataset.index = events.length ? 0 : null;
                    }

                    if (self.event_source !== current_event_source) {
                        console.log("Consecutive ``do_search`` called. Cancelling.");
                        return;
                    }

                    if (!self.useContacts) {  // If we use all peoples displayed in the current month as filter in sidebars
                        var filter_item;

                        self.now_filter_ids = [];

                        var color_field = self.fields[self.color_field];
                        if (color_field) {
                            _.each(events, function (e) {
                                var key,val = null;
                                if (color_field.type == "selection") {
                                    key = e[self.color_field];
                                    val = _.find(color_field.selection, function(name){ return name[0] === key;});
                                } else {
                                    key = e[self.color_field][0];
                                    val = e[self.color_field];
                                }
                                if (!self.all_filters[key]) {
                                    filter_item = {
                                        value: key,
                                        label: val[1],
                                        color: self.get_color(key),
                                        avatar_model: (utils.toBoolElse(self.avatar_filter, true) ? self.avatar_filter : false ),
                                        is_checked: true
                                    };
                                    self.all_filters[key] = filter_item;
                                }
                                if (! _.contains(self.now_filter_ids, key)) {
                                    self.now_filter_ids.push(key);
                                }
                            });
                        }
                        if (self.sidebar && color_field) {
                            self.sidebar.filter.render();

                            events = $.map(events, function (e) {
                                var key = color_field.type == "selection" ? e[self.color_field] : e[self.color_field][0];
                                if (_.contains(self.now_filter_ids, key) &&  self.all_filters[key].is_checked) {
                                    return e;
                                }
                                return null;
                            });
                        }

                    }
                    var all_attendees = $.map(events, function (e) { return e[self.attendee_people]; });
                    all_attendees = _.chain(all_attendees).flatten().uniq().value();

                    self.all_attendees = {};
                    if (self.avatar_title !== null) {
                        new Model(self.avatar_title).query(["name"]).filter([["id", "in", all_attendees]]).all().then(function(result) {
                            _.each(result, function(item) {
                                self.all_attendees[item.id] = item.name;
                            });
                        }).done(function() {
                            return self.perform_necessary_name_gets(events).then(callback);
                        });
                    }
                    else {
                        _.each(all_attendees,function(item){
                                self.all_attendees[item] = '';
                        });
                        return self.perform_necessary_name_gets(events).then(callback);
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
        var format = time.datetime_to_str;
        var extend_domain = [[this.date_start, '<=', format(end)]];
        if (this.date_stop) {
            extend_domain.push([this.date_stop, '>=', format(start)]);
        } else if (!this.date_delay) {
            extend_domain.push([this.date_start, '>=', format(start)]);
        }
        return new CompoundDomain(domain, extend_domain);
    },

    /**
     * Get all_filters ordered by label
     */
    get_all_filters_ordered: function() {
        return _.values(this.all_filters).sort(function(f1,f2) {
            return _.string.naturalCmp(f1.label, f2.label);
        });
    },

    /**
     * Updates record identified by ``id`` with values in object ``data``
     */
    update_record: function(id, data) {
        var self = this;
        var event_id;
        delete(data.name); // Cannot modify actual name yet
        var index = this.dataset.get_id_index(id);
        if (index !== null) {
            event_id = this.dataset.ids[index];
            this.dataset.write(event_id, data, {}).always(function() {
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
    open_event: function(id, title) {
        var self = this;
        if (! this.open_popup_action) {
            var index = this.dataset.get_id_index(id);
            this.dataset.index = index;
            if (this.write_right) {
                this.do_switch_view('form', { mode: "edit" });
            } else {
                this.do_switch_view('form', { mode: "view" });
            }
        }
        else {
            new form_common.FormViewDialog(this, {
                res_model: this.model,
                res_id: parseInt(id).toString() === id ? parseInt(id) : id,
                context: this.dataset.get_context(),
                title: title,
                view_id: +this.open_popup_action,
                readonly: true,
                buttons: [
                    {text: _t("Edit"), classes: 'btn-primary', close: true, click: function() {
                        self.dataset.index = self.dataset.get_id_index(id);
                        self.do_switch_view('form', { mode: "edit" });
                    }},

                    {text: _t("Delete"), close: true, click: function() {
                        self.remove_event(id);
                    }},

                    {text: _t("Close"), close: true}
                ]
            }).open();
        }
        return false;
    },

    do_show: function() {            
        this.do_push_state({});
        this.shown.resolve();
        return this._super();
    },
    is_action_enabled: function(action) {
        if (action === 'create' && !this.options.creatable) {
            return false;
        }
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
        this.dataset.trigger("dataset_changed", id);
        this.refresh_event(id);
    },
    slow_created: function () {
        // refresh all view, because maybe some recurrents item
        var self = this;
        if (self.sidebar) {
            // force filter refresh
            self.sidebar.filter.is_loaded = false;
        }
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


core.view_registry.add('calendar', CalendarView);

return CalendarView;
});
