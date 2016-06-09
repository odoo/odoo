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
            var filter_me = _.first(_.values(this.all_filters));
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
                options: '{"no_open": True}',
                placeholder: _t("Add Favorite Calendar"),
            },
        });
        this.m2o.set_filter_ids(_.pluck(this.view.all_filters, 'value'));
        this.m2o.appendTo(this.$el);
        this.m2o.on('change:value', this, this.on_add_filter.bind(this));
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
    get_next_notif: function() {
        var self = this;

        this.rpc("/calendar/notify", {}, {shadow: true})
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
    show_application: function() {
        return this._super.apply(this, arguments).then(this.check_notifications.bind(this));
    },
    //Override addons/web/static/src/js/chrome.js       
    // FIXME: on_logout is no longer used
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
