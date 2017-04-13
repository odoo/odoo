odoo.define('base_calendar.base_calendar', function (require) {
"use strict";

var bus = require('bus.bus').bus;
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

var FieldMany2ManyTags = core.form_widget_registry.get('many2many_tags');
var _t = core._t;
var _lt = core._lt;
var QWeb = core.qweb;

CalendarView.include({
    extraSideBar: function() {
        var result = this._super();
        if (this.useContacts) {
            return result.then(this.sidebar.filter.initialize_favorites.bind(this.sidebar.filter));
        }
        return result;
    },
    get_all_filters_ordered: function() {
        var filters = this._super();
        if (this.useContacts) {
            var filter_me = this.all_filters[this.session.partner_id];
            var filter_all = this.all_filters[-1];
            filters = [].concat(filter_me, _.difference(filters, [filter_me, filter_all]), filter_all);
        }
        return filters;
    }
});

var FieldMany2One = core.form_widget_registry.get('many2one');
var SidebarFilterM2O = FieldMany2One.extend({
    get_search_blacklist: function () {
        return this._super.apply(this, arguments).concat(this.filter_ids);
    },
    set_filter_ids: function (filter_ids) {
        this.filter_ids = filter_ids;
    },
});

widgets.SidebarFilter.include({
    events: _.extend(widgets.SidebarFilter.prototype.events, {
        'click .o_remove_contact': 'on_remove_filter',
    }),

    init: function () {
        this._super.apply(this, arguments);
        this.ds_contacts = new data.DataSet(this, 'calendar.contacts', session.context);
    },
    initialize_favorites: function () {
        return this.load_favorite_list().then(this.initialize_m2o.bind(this));
    },
    initialize_m2o: function() {
        this.dfm = new form_common.DefaultFieldManager(this);
        if (!this.view.useContacts) {
            return;
        }
        this.dfm.extend_field_desc({
            partner_id: {
                relation: "res.partner",
            },
        });
        this.m2o = new SidebarFilterM2O(this.dfm, {
            attrs: {
                class: 'o_add_favorite_calendar',
                name: "partner_id",
                type: "many2one",
                options: '{"no_open": True, "no_create": True}',
                placeholder: _t("Add Favorite Calendar"),
            },
        });
        this.m2o.set_filter_ids(_.pluck(this.view.all_filters, 'value'));
        this.m2o.appendTo(this.$el);
        var self = this;
        this.m2o.on('change:value', this, function() {
            // once selected, we reset the value to false.
            if (self.m2o.get_value()) {
                self.on_add_filter();
            }
        });
    },
    load_favorite_list: function () {
        var self = this;
        // Untick sidebar's filters if there is an active partner in the context
        var active_partner = (this.view.dataset.context.active_model === 'res.partner');
        return session.is_bound.then(function() {
            self.view.all_filters = {};
            self.view.now_filter_ids = [];
            self._add_filter(session.partner_id, session.name + _lt(" [Me]"), !active_partner);
            self._add_filter(-1, _lt("Everybody's calendars"), false, false);
            //Get my coworkers/contacts
            return new Model("calendar.contacts")
                .query(["partner_id"])
                .filter([["user_id", "=", session.uid]])
                .all()
                .then(function(result) {
                    _.each(result, function(item) {
                        self._add_filter(item.partner_id[0], item.partner_id[1], !active_partner, true);
                    });

                    self.view.now_filter_ids = _.pluck(self.view.all_filters, 'value');

                    self.render();
                });
        });
    },
    reload: function () {
        this.trigger_up('reload_events');
        this.render();
        this.m2o.set_filter_ids(_.pluck(this.view.all_filters, 'value'));
        this.m2o.set_value(false);
    },
    _add_filter: function (value, label, is_checked, can_be_removed) {
        this.view.all_filters[value] = {
            value: value,
            label: label,
            color: this.view.get_color(value),
            avatar_model: this.view.avatar_model,
            is_checked: is_checked || false,
            can_be_removed: can_be_removed || false,
        };
        if (is_checked) {
            this.view.now_filter_ids.push(value);
        }
    },
    _remove_filter: function (value) {
        delete this.view.all_filters[value];
        var index = this.view.now_filter_ids.indexOf(value);
        if (index >= 0) {
            this.view.now_filter_ids.splice(index, 1);
        }
    },
    on_add_filter: function() {
        var self = this;
        var defs = [];
        _.each(this.m2o.display_value, function(element, index) {
            if (session.partner_id !== index) {
                defs.push(self.ds_contacts.call("create", [{'partner_id': index}]).then(function () {
                    self._add_filter(parseInt(index), element, true, true);
                    self.reload();
                }));
            }
        });
        return $.when.apply(null, defs).then(this.reload.bind(this));
    },
    on_remove_filter: function(e) {
        var self = this;
        var id = $(e.currentTarget).data('id');

        Dialog.confirm(this, _t("Do you really want to delete this filter from favorites ?"), {
            confirm_callback: function() {
                self.ds_contacts.call('unlink_from_partner_id', [id]).then(function () {
                    self._remove_filter(id);
                    self.reload();
                });
            },
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
    display_calendar_notif: function(notifications) {
        var self = this;
        var last_notif_timer = 0;

        // Clear previously set timeouts and destroy currently displayed calendar notifications
        clearTimeout(this.get_next_calendar_notif_timeout);
        _.each(this.calendar_notif_timeouts, clearTimeout);
        _.each(this.calendar_notif, function(notif) {
            if (!notif.isDestroyed()) {
                notif.destroy();
            }
        });
        this.calendar_notif_timeouts = {};
        this.calendar_notif = {};

        // For each notification, set a timeout to display it
        _.each(notifications, function(notif) {
            self.calendar_notif_timeouts[notif.event_id] = setTimeout(function() {
                var notification = new CalendarNotification(self.notification_manager, notif.title, notif.message, notif.event_id);
                self.notification_manager.display(notification);
                self.calendar_notif[notif.event_id] = notification;
            }, notif.timer * 1000);
            last_notif_timer = Math.max(last_notif_timer, notif.timer);
        });

        // Set a timeout to get the next notifications when the last one has been displayed
        if (last_notif_timer > 0) {
            this.get_next_calendar_notif_timeout = setTimeout(this.get_next_calendar_notif.bind(this), last_notif_timer * 1000);
        }
    },
    get_next_calendar_notif: function() {
        this.rpc("/calendar/notify", {}, {shadow: true})
            .done(this.display_calendar_notif.bind(this))
            .fail(function(err, ev) {
                if(err.code === -32098) {
                    // Prevent the CrashManager to display an error
                    // in case of an xhr error not due to a server error
                    ev.preventDefault();
                }
            });
    },
    show_application: function() {
        // An event is triggered on the bus each time a calendar event with alarm
        // in which the current user is involved is created, edited or deleted
        this.calendar_notif_timeouts = {};
        this.calendar_notif = {};
        bus.on('notification', this, function (notifications) {
            _.each(notifications, (function (notification) {
                if (notification[0][1] === 'calendar.alarm') {
                    this.display_calendar_notif(notification[1]);
                }
            }).bind(this));
        });
        return this._super.apply(this, arguments).then(this.get_next_calendar_notif.bind(this));
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

core.form_widget_registry.add('many2manyattendee', Many2ManyAttendee);


});
