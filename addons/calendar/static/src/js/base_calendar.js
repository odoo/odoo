odoo.define('base_calendar.base_calendar', function (require) {
"use strict";

var bus = require('bus.bus').bus;
var BasicModel = require('web.BasicModel');
var field_registry = require('web.field_registry');
var Notification = require('web.Notification');
var relational_fields = require('web.relational_fields');
var session = require('web.session');
var WebClient = require('web.WebClient');

var FieldMany2ManyTags = relational_fields.FieldMany2ManyTags;


var CalendarNotification = Notification.extend({
    template: "CalendarNotification",

    init: function(parent, params) {
        this._super(parent, params);
        this.eid = params.eventID;
        this.sticky = true;

        this.events = _.extend(this.events || {}, {
            'click .link2event': function() {
                var self = this;

                this._rpc({
                        route: '/web/action/load',
                        params: {
                            action_id: 'calendar.action_calendar_event_notify',
                        },
                    })
                    .then(function(r) {
                        r.res_id = self.eid;
                        return self.do_action(r);
                    });
            },

            'click .link2recall': function() {
                this.destroy(true);
            },

            'click .link2showed': function() {
                this.destroy(true);
                this._rpc({route: '/calendar/notify_ack'});
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
                var notification = new CalendarNotification(self.notification_manager, {
                    title: notif.title,
                    text: notif.message,
                    eventID: notif.event_id,
                });
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
        session.rpc("/calendar/notify", {}, {shadow: true})
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

BasicModel.include({
    /**
     * @private
     * @param {Object} record
     * @param {string} fieldName
     * @returns {Deferred}
     */
    _fetchSpecialAttendeeStatus: function (record, fieldName) {
        var context = record.getContext({fieldName: fieldName});
        var attendeeIDs = record.data[fieldName] ? this.localData[record.data[fieldName]].res_ids : [];
        var meetingID = _.isNumber(record.res_id) ? record.res_id : false;
        return this._rpc({
            model: 'res.partner',
            method: 'get_attendee_detail',
            args: [attendeeIDs, meetingID],
            context: context,
        }).then(function (result) {
            return _.map(result, function (d) {
                return _.object(['id', 'display_name', 'status', 'color'], d);
            });
        });
    },
});

var Many2ManyAttendee = FieldMany2ManyTags.extend({
    // as this widget is model dependant (rpc on res.partner), use it in another
    // context probably won't work
    // supportedFieldTypes: ['many2many'],
    tag_template: "Many2ManyAttendeeTag",
    specialData: "_fetchSpecialAttendeeStatus",

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _getRenderTagsContext: function () {
        var result = this._super.apply(this, arguments);
        result.attendeesData = this.record.specialData.partner_ids;
        return result;
    },
});

field_registry.add('many2manyattendee', Many2ManyAttendee);

});
