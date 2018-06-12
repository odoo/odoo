odoo.define('calendar.systray.ActivityMenu', function (require) {
"use strict";

var ActivityMenu = require('mail.systray.ActivityMenu');
var fieldUtils = require('web.field_utils');

ActivityMenu.include({
    events: _.extend({}, ActivityMenu.prototype.events, {
        'click .o_meeting_filter': '_onMeetingFilterClick'
    }),

    //-----------------------------------------
    // Private
    //-----------------------------------------

    /**
     * parse date to server value
     *
     * @private
     * @override
     */
    _getActivityData: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            var meeting = _.find(self._activities, {type: 'meeting'});
            if (meeting && meeting.meetings)  {
                _.each(meeting.meetings, function (res) {
                    res.start = fieldUtils.parse.datetime(res.start, false, {isUTC: true});
                });
            }
        });
    },

    //-----------------------------------------
    // Handlers
    //-----------------------------------------

    /**
     * @private
     * @override
     */
    _onActivityFilterClick: function (ev) {
        var $el = $(ev.currentTarget);
        var data = _.extend({}, $el.data());
        if (data.res_model === "calendar.event" && data.filter === "my") {
            this.do_action('calendar.action_calendar_event', {
                additional_context: {
                    default_mode: 'day',
                    search_default_mymeetings: 1,
                }
            });
        } else {
            this._super.apply(this, arguments);
        }
    },

    /**
     * When particular meeting clicked, open particular meeting in form view
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onMeetingFilterClick: function (ev) {
        ev.stopPropagation();
        var $el = $(ev.currentTarget);
        var data = _.extend({}, $el.data());
        if (data.res_model === "calendar.event") {
            this.do_action({
                type: 'ir.actions.act_window',
                name: data.model_name,
                res_model:  data.res_model,
                res_id: data.res_id,
                views: [[false, 'form'], [false, 'calendar'], [false, 'list']],
            });
        }
    },
});

});
