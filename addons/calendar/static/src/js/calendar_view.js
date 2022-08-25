/** @odoo-module alias=calendar.CalendarView **/

import CalendarController from '@calendar/js/calendar_controller';
import CalendarModel from '@calendar/js/calendar_model';
import AttendeeCalendarRenderer from '@calendar/js/calendar_renderer';
import CalendarView from 'web.CalendarView';
import viewRegistry from 'web.view_registry';


import rpc from 'web.rpc';
import FormView from 'web.FormView';
import FormController from 'web.FormController';

const CalendarRenderer = AttendeeCalendarRenderer.AttendeeCalendarRenderer;

var AttendeeCalendarView = CalendarView.extend({
    config: _.extend({}, CalendarView.prototype.config, {
        Renderer: CalendarRenderer,
        Controller: CalendarController,
        Model: CalendarModel,
    }),
});

viewRegistry.add('attendee_calendar', AttendeeCalendarView);

const CalendarFormController = FormController.extend({
    start: async function () {
        rpc.query({
            model: 'calendar.event',
            method: 'get_discuss_videocall_location'
        }).then((discussVideocallLocation) => {
            this.discussVideocallLocation = discussVideocallLocation
        });
        return this._super.apply(this, arguments);
    },
    _onButtonClicked: function (ev) {
        const action = ev.data.attrs.name;
        if (action == 'clear_videocall_location' || action === 'set_discuss_videocall_location') {
            let newVal = false;
            let videoCallSource = 'custom'
            let changes = {};
            if (action === 'set_discuss_videocall_location') {
                newVal = this.discussVideocallLocation;
                videoCallSource = 'discuss';
                changes.access_token = this.discussVideocallLocation.split('/').pop();
            }
            changes = Object.assign(changes, {
                videocall_location: newVal,
                videocall_source: videoCallSource,
            });

            this.trigger_up('field_changed', {
                dataPointID: ev.data.record.id,
                changes
            });
            return;
        }
        return this._super.apply(this, arguments);
    },
});

export const CalendarFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Controller: CalendarFormController,
    }),
});

viewRegistry.add('calendar_form', CalendarFormView);

export default AttendeeCalendarView;
