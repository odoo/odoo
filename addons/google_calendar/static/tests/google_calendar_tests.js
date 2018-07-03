odoo.define('google_calendar.calendar_tests', function (require) {
"use strict";

var CalendarView = require('web.CalendarView');
var testUtils = require('web.test_utils');

var createAsyncView = testUtils.createAsyncView;

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
                    stop_date: {string: "stop date", type: "date"},
                    start: {string: "start datetime", type: "datetime"},
                    stop: {string: "stop datetime", type: "datetime"},
                    allday: {string: "allday", type: "boolean"},
                    partner_ids: {string: "attendees", type: "one2many", relation: 'partner'},
                    type: {string: "type", type: "integer"},
                },
                records: [
                    {id: 5, user_id: 4, partner_id: 4, name: "event 1", start: "2016-12-13 15:55:05", stop: "2016-12-15 18:55:05", allday: false, partner_ids: [], type: 2},
                    {id: 6, user_id: 4, partner_id: 4, name: "event 2", start: "2016-12-18 08:00:00", stop: "2016-12-18 09:00:00", allday: false, partner_ids: [], type: 3}
                ],
                check_access_rights: function () {
                    return $.when(true);
                }
            },
            user: {
                fields: {
                    id: {string: "ID", type: "integer"},
                    display_name: {string: "Displayed name", type: "char"},
                    partner_id: {string: "partner", type: "many2one", relation: 'partner'},
                    image: {string: "image", type: "integer"},
                },
                records: [
                    {id: 4, display_name: "user 4", partner_id: 4},
                ]
            },
            partner: {
                fields: {
                    id: {string: "ID", type: "integer"},
                    display_name: {string: "Displayed name", type: "char"},
                    image: {string: "image", type: "integer"},
                },
                records: [
                    {id: 4, display_name: "partner 4", image: 'DDD'}
                ]
            },
            filter_partner: {
                fields: {
                    id: {string: "ID", type: "integer"},
                    user_id: {string: "user", type: "many2one", relation: 'user'},
                    partner_id: {string: "partner", type: "many2one", relation: 'partner'},
                },
                records: [
                    {id: 3, user_id: 4, partner_id: 4}
                ]
            },
        };
    }
}, function () {

    QUnit.test('sync google calendar', function (assert) {
        assert.expect(6);
        var done = assert.async();

        createAsyncView({
            View: CalendarView,
            model: 'calendar.event',
            data: this.data,
            arch:
            '<calendar class="o_calendar_test" '+
                'date_start="start" '+
                'date_stop="stop" '+
                'mode="month">'+
                    '<field name="name"/>'+
            '</calendar>',
            viewOptions: {
                initialDate: initialDate,
            },
            mockRPC: function (route, args) {
                if (route === '/google_calendar/sync_data') {
                    assert.step(route);
                    this.data['calendar.event'].records.push(
                        {id: 7, user_id: 4, partner_id: 4, name: "event from google calendar", start: "2016-12-28 15:55:05", stop: "2016-12-29 18:55:05", allday: false, partner_ids: [], type: 2}
                    );
                    return $.when({status: 'need_refresh'});
                } else if (route === '/web/dataset/call_kw/calendar.event/search_read') {
                    assert.step(route);
                }
                return this._super.apply(this, arguments);
            },
        }).then(function (calendar) {
            assert.strictEqual(calendar.$('.fc-event').length, 2, "should display 2 events on the month");

            var $sidebar = calendar.$('.o_calendar_sidebar');

            calendar.$('.o_google_sync_button').click();

            assert.verifySteps([
                '/web/dataset/call_kw/calendar.event/search_read',
                '/google_calendar/sync_data',
                '/web/dataset/call_kw/calendar.event/search_read',
            ], 'should do a search_read before and after the call to sync_data');

            assert.strictEqual(calendar.$('.fc-event').length, 3, "should now display 3 events on the month");

            calendar.destroy();
            done();
        });
    });
});
});
