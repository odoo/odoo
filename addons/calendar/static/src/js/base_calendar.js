odoo.define('base_calendar.base_calendar', function (require) {
"use strict";

var core = require('web.core');
var CalendarView = require('web_calendar.CalendarView');
var data = require('web.data');
var Dialog = require('web.Dialog');
var form_common = require('web.form_common');
var Model = require('web.DataModel');
var Notification = require('web.notification').Notification;
var session = require('web.session');
var WebClient = require('web.WebClient');
var widgets = require('web_calendar.widgets');
var formats = require('web.formats');

var FieldMany2ManyTags = core.form_widget_registry.get('many2many_tags');
var _t = core._t;
var _lt = core._lt;
var QWeb = core.qweb;

function reload_favorite_list(result) {
    var self = result;
    var current = result;
    if (result.view) {
        self = result.view;
    }
    return new Model("res.users")
    .query(["partner_id"])
    .filter([["id", "=", self.dataset.context.uid]])
    .first()
    .done(function(result) {
        var sidebar_items = {};
        var filter_value = result.partner_id[0];
        var filter_item = {
            value: filter_value,
            label: result.partner_id[1] + _lt(" [Me]"),
            color: self.get_color(filter_value),
            avatar_model: self.avatar_model,
            is_checked: true,
            is_remove: false,
        };
        sidebar_items[filter_value] = filter_item;

        filter_item = {
            value: -1,
            label: _lt("Everybody's calendars"),
            color: self.get_color(-1),
            avatar_model: self.avatar_model,
            is_checked: false
        };
        sidebar_items[-1] = filter_item;
        //Get my coworkers/contacts
        new Model("calendar.contacts").query(["partner_id"]).filter([["user_id", "=",self.dataset.context.uid]]).all().then(function(result) {
            _.each(result, function(item) {
                filter_value = item.partner_id[0];
                filter_item = {
                    value: filter_value,
                    label: item.partner_id[1],
                    color: self.get_color(filter_value),
                    avatar_model: self.avatar_model,
                    is_checked: true
                };
                sidebar_items[filter_value] = filter_item;
            });

            self.all_filters = sidebar_items;
            self.now_filter_ids = $.map(self.all_filters, function(o) { return o.value; });
            
            self.sidebar.filter.events_loaded(self.get_all_filters_ordered());
            self.sidebar.filter.set_filters();
            self.sidebar.filter.add_favorite_calendar();
            self.sidebar.filter.destroy_filter();
        }).done(function () {
            self.$calendar.fullCalendar('refetchEvents');
            if (current.ir_model_m2o) {
                current.ir_model_m2o.set_value(false);
            }
        });
    });
}
    
widgets.QuickCreate.include({

    start: function() {
        this._super();
        if(this.dataset.model == 'calendar.event') {
            this.$input.attr("placeholder",_t("4pm Meeting at Brussel"));
        }
    },

    prepare_data_pattern:function(data) {
        var message =  data.name;
        var start_time, stop_time, start_date_time, stop_date_time, time = null;
        var result = false;

        //Regular expression for find patters like 3h, 3:00pm, 3:00:00am, 5h40, 4:20, 3:10:00 and etc.
        var time_expr = /(^|\s|((^|\s)(at)\s)|((^|\s)(from)\s))(((\d{1,2})|(\d{1,2}:\d{2})|(\d{1,2}:\d{2}:\d{2}))(h|[ap]m)
                        |(\d{1,2})h(\d{1,2})
                        |(\d{1,2}:\d{2})
                        |(\d{1,2}:\d{2}:\d{2}))(?=(\s|$))/i;
        var time_value = message.match(time_expr);

        //Regular expression for find patters like 3h to 8h, 5pm to 9AM, 3:20 to 4:50, 5h30 to 9h10.
        var time_range = message.match(new RegExp(time_expr.source +  /\s(to)(?=\s)/.source + time_expr.source,'gi'));
        var time_format = ['hha', 'HH:mm', 'hh:mma', 'HH'];

        var start_date = moment(this.data_template.start.slice(0,10));
        var stop_date = moment(this.data_template.stop.slice(0,10));

        //Check value of start_datetime and stop_datetime
        var check_convert_time = function (time_start, time_stop){
            start_time = (moment(time_start, time_format));
            if (time_range != null)  {
                stop_time = (moment(time_stop, time_format));
                if (start_time.hours() > stop_time.hours()) {
                    stop_date = stop_date.add(1,'days');
                }
            } else if(start_date.valueOf() == stop_date.valueOf()) {
                stop_time = (moment(time_start, time_format)).add(1, 'hours');
                if (start_time.hours() >= 23 ) {
                    stop_date = stop_date.add(1,'days');
                }
            } else {
                stop_time = start_time
            }
            if (start_time.isValid() && stop_time.isValid()) {
                return start_time,stop_time
            }
            return false
        }
        //Get value of start_datetime and stop_datetime
        if (time_value != null) {
            if (time_range != null) {
                time = time_range[0].split(' to ');
                message = message.replace(time_range[0], '');
                result = check_convert_time(time[0],time[1]);
            } else {
                message = message.replace(time_value[0], '');
                result = check_convert_time(time_value[0]);
            }
            if (result) {
                start_date_time = (start_date.hours(start_time.hours()),start_date.minutes(start_time.minutes()));
                stop_date_time = (stop_date.hours(stop_time.hours()),stop_date.minutes(stop_time.minutes()));
            }
        }
        //Regular expression for find patters like at Gandhinagar, @ Ahmedabad.
        var location_expr = message.match(/((^|\s)((at|@)\s)|(@)(\w+))/gi);
        var loc_value, location_data, location_value, loc_data = null;

        //Get value of location
        if (location_expr != null) {
            loc_value = location_expr[location_expr.length-1];
            location_data = loc_value.trim().split(' ');

            if (location_data[0].toLowerCase().indexOf('at') > -1) {
                location_value = message.substring(message.lastIndexOf(loc_value.substring(0,3)));
            } else if(loc_value.indexOf('@') > -1) {
                location_value = message.substring(message.lastIndexOf('@'));
            } else if(loc_value.indexOf('@ ') > -1) {
                location_value = message.substring(message.lastIndexOf('@ '));
            }
            if (location_value.indexOf('@') > -1) {
                loc_data = location_value.replace('@','');
            } else {
                loc_data = location_value.replace(location_data[0],'');
            }
            message = message.replace(location_value,'').trim();
        }
        //Set value of start_datetime,stop_datetime,location,and subject in database.
        if (result) {
            data.allday = false;
            data.start_datetime = formats.parse_value(start_date_time, {type: 'datetime'});
            data.stop_datetime = formats.parse_value(stop_date_time, {type: 'datetime'});
        }
        if (location_expr != null && loc_data != null) {
            data.location = loc_data.trim();
        }
        if (time_value != null || location_expr != null) {
            data.name = message || _t("Meeting Name");
        }
    },
   
    quick_create: function(data, options) {
        var self = this;
        if(this.dataset.model == 'calendar.event') {
            self.prepare_data_pattern(data, self.data_template);
        }
        return this._super.apply(this, arguments)
    },
});

CalendarView.include({
    extraSideBar: function() {
        var result = this._super();
        if (this.useContacts) {
            return result.then(reload_favorite_list(this));
        }
        return result;
    },
    get_all_filters_ordered: function() {
        var filters = this._super();
        if (this.useContacts) {
            var filter_me = _.first(_.values(this.all_filters));
            var filter_all = this.all_filters[-1];
            filters = [].concat(filter_me, _.difference(filters, [filter_me, filter_all]), filter_all);
        }
        return filters;
    }
});

widgets.SidebarFilter.include({
    events_loaded: function() {
        this._super.apply(this, arguments);
        this.reinitialize_m2o();
    },
    add_favorite_calendar: function() {
        if (this.dfm)
            return;
        this.initialize_m2o();
    },
    reinitialize_m2o: function() {
        if (this.dfm) {
            this.dfm.destroy();
            this.dfm = undefined;
        }
        this.initialize_m2o();
    },
    initialize_m2o: function() {
        var self = this;
        this.dfm = new form_common.DefaultFieldManager(self);
        this.dfm.extend_field_desc({
            partner_id: {
                relation: "res.partner",
            },
        });
        var FieldMany2One = core.form_widget_registry.get('many2one');
        this.ir_model_m2o = new FieldMany2One(self.dfm, {
            attrs: {
                class: 'o_add_favorite_calendar',
                name: "partner_id",
                type: "many2one",
                options: '{"no_open": True}',
                placeholder: _t("Add Favorite Calendar"),
            },
        });
        this.ir_model_m2o.appendTo(this.$el);
        this.ir_model_m2o.on('change:value', self, function() { 
            self.add_filter();
        });
    },
    add_filter: function() {
        var self = this;
        var defs = [];
        defs.push(new Model("res.users")
        .query(["partner_id"])
        .filter([["id", "=",this.view.dataset.context.uid]])
        .first()
        .done(function(result){
            $.map(self.ir_model_m2o.display_value, function(element,index) {
                if (result.partner_id[0] != index){
                    self.ds_message = new data.DataSetSearch(self, 'calendar.contacts');
                    defs.push(self.ds_message.call("create", [{'partner_id': index}]));
                }
            });
        }));
        return $.when.apply(null, defs).then(function() {
            return reload_favorite_list(self);
        });
    },
    destroy_filter: function(e) {
        var self = this;
        this.$(".oe_remove_follower").on('click', function(e) {
            self.ds_message = new data.DataSetSearch(self, 'calendar.contacts');
            var id = $(e.currentTarget)[0].dataset.id;

            Dialog.confirm(self, _t("Do you really want to delete this filter from favorite?"), {
                confirm_callback: function() {
                    self.ds_message.call('search', [[['partner_id', '=', parseInt(id)]]]).then(function(record) {
                        return self.ds_message.unlink(record);
                    }).done(function() {
                        reload_favorite_list(self);
                    });
                },
            });
        });
    },
});

var CalendarNotification = Notification.extend({
    template: "CalendarNotification",

    init: function(parent, title, text, eid) {
        this._super(parent, title, text, true);
        this.eid = eid;

        this.events = _.extend(this.events || {}, {
            'click .link2event': function() {
                var self = this;

                this.rpc("/web/action/load", {
                    action_id: "calendar.action_calendar_event_notify",
                }).then(function(r) {
                    r.res_id = self.eid;
                    return self.do_action(r);
                });
            },

            'click .link2recall': function() {
                this.destroy(true);
            },

            'click .link2showed': function() {
                this.destroy(true);
                this.rpc("/calendar/notify_ack");
            },
        });
    },
});

WebClient.include({
    get_next_notif: function() {
        var self = this;

        this.rpc("/calendar/notify")
        .done(function(result) {
            _.each(result, function(res) {
                setTimeout(function() {
                    // If notification not already displayed, we create and display it (FIXME is this check usefull?)
                    if(self.$(".eid_" + res.event_id).length === 0) {
                        self.notification_manager.display(new CalendarNotification(self.notification_manager, res.title, res.message, res.event_id));
                    }
                }, res.timer * 1000);
            });
        })
        .fail(function(err, ev) {
            if(err.code === -32098) {
                // Prevent the CrashManager to display an error
                // in case of an xhr error not due to a server error
                ev.preventDefault();
            }
        });
    },
    check_notifications: function() {
        var self = this;
        this.get_next_notif();
        this.intervalNotif = setInterval(function() {
            self.get_next_notif();
        }, 5 * 60 * 1000);
    },
    //Override the show_application of addons/web/static/src/js/chrome.js       
    show_application: function() {
        this._super();
        this.check_notifications();
    },
    //Override addons/web/static/src/js/chrome.js       
    on_logout: function() {
        this._super();
        clearInterval(this.intervalNotif);
    },
});

var Many2ManyAttendee = FieldMany2ManyTags.extend({
    tag_template: "Many2ManyAttendeeTag",
    get_render_data: function (ids) {
        return this.dataset.call('get_attendee_detail', [ids, this.getParent().datarecord.id || false])
                           .then(process_data);

        function process_data(data) {
            return _.map(data, function (d) {
                return _.object(['id', 'display_name', 'status', 'color'], d);
            });
        }
    },
});

function showCalendarInvitation(db, action, id, view, attendee_data) {
    session.session_bind(session.origin).then(function () {
        if (session.session_is_valid(db) && session.username !== "anonymous") {
            window.location.href = _.str.sprintf('/web?db=%s#id=%s&view_type=form&model=calendar.event', db, id);
        } else {
            $("body").prepend(QWeb.render('CalendarInvitation', {attendee_data: JSON.parse(attendee_data)}));
        }
    });
}

core.form_widget_registry.add('many2manyattendee', Many2ManyAttendee);

return {
    showCalendarInvitation: showCalendarInvitation,
};

});
