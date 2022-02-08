odoo.define('google_calendar.calendar_tests', function (require) {
"use strict";

var GoogleCalendarView = require('@calendar/js/calendar_view')[Symbol.for("default")];
var testUtils = require('web.test_utils');
const session = require('web.session');

var createCalendarView = testUtils.createCalendarView;

var initialDate = new Date("2016-12-12T08:00:00Z");


QUnit.module('Google Calendar', {
    beforeEach: function () {
        this.data = {
            'calendar.event': {
                fields: {
                    id: {string: "ID", type: "integer"},
                    user_id: {string: "user", type: "many2one", relation: 'user'},
                    partner_id: {string: "user", type: "many2one", relation: 'partner', related: 'user_id.partner_id'},
                    name: {string: "name", type: "char"},
                    start_date: {string: "start date", type: "date"},
                    start_date: {string: "start date", type: "date"},
                    stop_date: {string: "stop date", type: "date"},
                    start: {string: "start datetime", type: "datetime"},
                    stop: {string: "stop datetime", type: "datetime"},
                    allday: {string: "allday", type: "boolean"},
                    partner_ids: {string: "attendees", type: "one2many", relation: 'partner'},
                    type: {string: "type", type: "integer"},
                },
                records: [
                    {id: 5, user_id: session.uid, partner_id: 4, name: "event 1", start: "2016-12-13 15:55:05", stop: "2016-12-15 18:55:05", allday: false, partner_ids: [4], type: 2},
                    {id: 6, user_id: session.uid, partner_id: 5, name: "event 2", start: "2016-12-18 08:00:00", stop: "2016-12-18 09:00:00", allday: false, partner_ids: [4], type: 3}
                ],
                check_access_rights: function () {
                    return Promise.resolve(true);
                }
            },
            user: {
                fields: {
                    id: {string: "ID", type: "integer"},
                    display_name: {string: "Displayed name", type: "char"},
                    partner_id: {string: "partner", type: "many2one", relation: 'partner'},
                    image_1920: {string: "image", type: "integer"},
                },
                records: [
                    {id: 4, display_name: "user 4", partner_id: 4},
                ]
            },
            partner: {
                fields: {
                    id: {string: "ID", type: "integer"},
                    display_name: {string: "Displayed name", type: "char"},
                    image_1920: {string: "image", type: "integer"},
                },
                records: [
                    {id: 4, display_name: "partner 4", image_1920: 'DDD'},
                    {id: 5, display_name: "partner 5", image_1920: 'DDD'},
                ]
            },
            filter_partner: {
                fields: {
                    id: {string: "ID", type: "integer"},
                    user_id: {string: "user", type: "many2one", relation: 'user'},
                    partner_id: {string: "partner", type: "many2one", relation: 'partner'},
                    partner_checked: {string: "checked", type: "boolean"},
                },
                records: [
                    {id: 3, user_id: session.uid, partner_id: 4, partner_checked: true}
                ]
            },
        };
    }
}, function () {

    QUnit.test('sync google calendar', async function (assert) {
        assert.expect(11);

        var calendar = await createCalendarView({
            View: GoogleCalendarView,
            model: 'calendar.event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'js_class="attendee_calendar" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'attendee="partner_ids" '+
                'mode="month">'+
                    '<field name="name"/>'+
                    '<field name="partner_ids" write_model="filter_partner" write_field="partner_id"/>'+
            '</calendar>',
            viewOptions: {
                initialDate: initialDate,
            },
            mockRPC: async function (route, args) {
                if (route === '/google_calendar/sync_data') {
                    assert.step(route);
                    this.data['calendar.event'].records.push(
                        {id: 7, user_id: session.uid, partner_id: 4, name: "event from google calendar", start: "2016-12-28 15:55:05", stop: "2016-12-29 18:55:05", allday: false, partner_ids: [4], type: 4}
                    );
                    return Promise.resolve({status: 'need_refresh'});
                } else if (route === '/web/dataset/call_kw/calendar.event/search_read') {
                    assert.step(route);
                } else if (route === '/microsoft_calendar/sync_data') {
                    return Promise.resolve();
                } else if (route === '/web/dataset/call_kw/res.partner/get_attendee_detail') {
                    return Promise.resolve([]);
                }
                return await this._super.apply(this, arguments);
            },
        });
        // select the partner filter
        await testUtils.dom.click(calendar.$('.o_calendar_filter_item[data-value=all] input'));
        // sync_data was called a first time without filter, event from google calendar was created twice
        assert.containsN(calendar, '.fc-event', 4, "should display 4 events on the month");

        await testUtils.dom.click(calendar.$('.o_calendar_button_next'));
        await testUtils.dom.click(calendar.$('.o_calendar_button_prev'));

        assert.verifySteps([
            '/google_calendar/sync_data',
            '/web/dataset/call_kw/calendar.event/search_read',
            '/google_calendar/sync_data',
            '/web/dataset/call_kw/calendar.event/search_read',
            '/google_calendar/sync_data',
            '/web/dataset/call_kw/calendar.event/search_read',
            '/google_calendar/sync_data',
            '/web/dataset/call_kw/calendar.event/search_read',
        ], 'should do a search_read before and after the call to sync_data');

        assert.containsN(calendar, '.fc-event', 6, "should now display 6 events on the month");

        calendar.destroy();
    });
});
});
