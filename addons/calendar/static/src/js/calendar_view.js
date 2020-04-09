odoo.define('calendar.CalendarView', function (require) {
"use strict";

var CalendarController = require('calendar.CalendarController');
var CalendarModel = require('calendar.CalendarModel');
const CalendarRenderer = require('calendar.CalendarRenderer');
var CalendarView = require('web.CalendarView');
var viewRegistry = require('web.view_registry');

var AttendeeCalendarView = CalendarView.extend({
    config: _.extend({}, CalendarView.prototype.config, {
        Renderer: CalendarRenderer,
        Controller: CalendarController,
        Model: CalendarModel,
    }),
});

viewRegistry.add('attendee_calendar', AttendeeCalendarView);

return AttendeeCalendarView

});
