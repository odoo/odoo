/** @odoo-module **/

import { click, getFixture, patchDate } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";
import { userService } from "@web/core/user_service";

const serviceRegistry = registry.category("services");

let target;
let serverData;
const uid = -1;

QUnit.module('Google Calendar', {
    beforeEach: function () {
        patchDate(2016, 11, 12, 8, 0, 0);
        serverData = {
            models: {
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
                        {id: 5, user_id: uid, partner_id: 4, name: "event 1", start: "2016-12-13 15:55:05", stop: "2016-12-15 18:55:05", allday: false, partner_ids: [4], type: 2},
                        {id: 6, user_id: uid, partner_id: 5, name: "event 2", start: "2016-12-18 08:00:00", stop: "2016-12-18 09:00:00", allday: false, partner_ids: [4], type: 3}
                    ],
                    check_access_rights: function () {
                        return Promise.resolve(true);
                    }
                },
                'appointment.type': {
                    fields: {},
                    records: [],
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
                        {id: 3, user_id: uid, partner_id: 4, partner_checked: true}
                    ]
                },
            },
            views: {},
        };
        target = getFixture();
        setupViewRegistries();
        serviceRegistry.add(
            "user",
            {
                ...userService,
                start() {
                    const fakeUserService = userService.start(...arguments);
                    Object.defineProperty(fakeUserService, "userId", {
                        get: () => uid,
                    });
                    return fakeUserService;
                },
            },
            { force: true }
        );
    }
}, function () {

    QUnit.test('sync google calendar', async function (assert) {
        assert.expect(13);

        let id = 7;
        await makeView({
            type: "calendar",
            resModel: 'calendar.event',
            serverData,
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
            mockRPC: async function (route, args) {
                if (route === '/google_calendar/sync_data') {
                    assert.step(route);
                    serverData.models['calendar.event'].records.push(
                        {id: id++, user_id: uid, partner_id: 4, name: "event from google calendar", start: "2016-12-28 15:55:05", stop: "2016-12-29 18:55:05", allday: false, partner_ids: [4], type: 4}
                    );
                    return Promise.resolve({status: 'need_refresh'});
                } else if (route === '/web/dataset/call_kw/calendar.event/search_read') {
                    assert.step(route);
                } else if (route === '/web/dataset/call_kw/res.partner/get_attendee_detail') {
                    return Promise.resolve([]);
                } else if (route === '/web/dataset/call_kw/res.users/has_group') {
                    return Promise.resolve(true);
                } else if (route === '/calendar/check_credentials') {
                    return Promise.resolve({
                        google_calendar: true,
                    });
                }
            },
        });
        // select the partner filter
        await click(target.querySelector('.o_calendar_filter_item[data-value=all] input'));
        // sync_data was called a first time without filter, event from google calendar was created twice
        assert.containsN(target, '.fc-event-container', 4, "should display 4 events on the month");

        await click(target.querySelector('.o_datetime_picker_header .o_next'));
        await click(target.querySelector('.o_datetime_picker .o_date_item_cell'));
        await click(target.querySelector('.o_view_scale_selector .dropdown-toggle'));
        await click(target.querySelector('.o_scale_button_month'));
        await click(target.querySelector('.o_calendar_button_today'));

        assert.verifySteps([
            '/google_calendar/sync_data',
            '/web/dataset/call_kw/calendar.event/search_read',
            '/google_calendar/sync_data',
            '/web/dataset/call_kw/calendar.event/search_read',
            '/google_calendar/sync_data',
            '/web/dataset/call_kw/calendar.event/search_read',
            '/google_calendar/sync_data',
            '/web/dataset/call_kw/calendar.event/search_read',
            "/google_calendar/sync_data",
            "/web/dataset/call_kw/calendar.event/search_read",
        ], 'should do a search_read before and after the call to sync_data');

        assert.containsN(target, '.fc-event-container', 7, "should now display 7 events on the month");
    });
});
