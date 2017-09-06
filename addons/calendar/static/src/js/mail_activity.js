odoo.define('calendar.Activity', function (require) {
"use strict";

var Activity = require('mail.Activity');
var Dialog = require('web.Dialog');
var core = require('web.core');
var _t = core._t;

Activity.include({
    _onEditActivity: function (event) {
        var self = this;
        var activity_id = $(event.currentTarget).data('activity-id');
        _.each(this.activities, function(activity) {
            if(activity.id === activity_id) {
                if (activity.activity_meeting_type === 'meeting') {
                    return self._super(event, {
                        res_model: 'calendar.event',
                        res_id: activity.calendar_event_id[0]
                    });
                } else {
                    return self._super(event);
                }
            }
        });
    },
    _onUnlinkActivity: function (event) {
        event.preventDefault();
        var self = this;
        var _super = this._super;
        var activity_id = $(event.currentTarget).data('activity-id');
        _.each(this.activities, function(activity) {
            if(activity.id === activity_id) {
                if (activity.activity_meeting_type === 'meeting') {
                    Dialog.confirm(self, _t("The activity is linked to a meeting. Deleting it will remove the meeting as well. Do you want to proceed ?"), {
                        confirm_callback: function () {
                            return _super.call(self, event, {
                                model: 'calendar.event',
                                args: [[activity.calendar_event_id[0]]],
                            });
                        }
                    });
                } else {
                    return self._super(event);
                }
            }
        });
    },
});

});
