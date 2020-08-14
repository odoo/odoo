odoo.define('calendar.systray.ActivityMenu', function (require) {
    "use strict";

    const ActivityMenu = require('mail.systray.ActivityMenu');
    const fieldUtils = require('web.field_utils');

    ActivityMenu.patch("calendar.systray.ActivityMenu", (T) => {
        class CalendarActivityMenu extends T {

            //-----------------------------------------
            // Public
            //-----------------------------------------

            meetingStart(start) {
                return moment(start).local().format("hh:mm A");
            }

            //-----------------------------------------
            // Private
            //-----------------------------------------

            /**
             * parse date to server value
             *
             * @private
             * @override
             */
            async _getActivityData() {
                await super._getActivityData(...arguments);
                const meeting = this.state.activities.find(activity => activity.type === "meeting");
                if (meeting && meeting.meetings) {
                    meeting.meetings.forEach(res => {
                        res.start = fieldUtils.parse.datetime(res.start, false, {
                            isUTC: true,
                        });
                    });
                }
            }

            //-----------------------------------------
            // Handlers
            //-----------------------------------------

            /**
             * @private
             * @override
             */
            _onActivityFilterClick(ev) {
                const el = ev.currentTarget;
                const data = Object.assign({}, el.dataset);
                if (data.res_model === "calendar.event" && data.filter === "my") {
                    this.trigger("do-action", {
                        action: "calendar.action_calendar_event",
                        options: {
                            additional_context: {
                                default_mode: "day",
                                search_default_mymeetings: 1,
                            },
                        },
                    });
                } else {
                    super._onActivityFilterClick(...arguments);
                }
            }
        }

        return CalendarActivityMenu;
    });

    return ActivityMenu;

});
