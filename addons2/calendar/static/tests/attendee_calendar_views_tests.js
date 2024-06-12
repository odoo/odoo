/** @odoo-module **/

import { getFixture, patchDate, patchWithCleanup } from "@web/../tests/helpers/utils";

import { changeScale, clickEvent } from "@web/../tests/views/calendar/helpers";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { userService } from "@web/core/user_service";
const serviceRegistry = registry.category("services");

let target;
let serverData;
const uid = -1;

QUnit.module("CalendarView", ({ beforeEach }) => {
    beforeEach(() => {
        // 2016-12-12 08:00:00
        patchDate(2016, 11, 12, 8, 0, 0);

        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => {},
        });

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

        serverData = {
            models: {
                event: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        user_id: {
                            string: "user",
                            type: "many2one",
                            relation: "user",
                            default: uid,
                        },
                        partner_id: {
                            string: "user",
                            type: "many2one",
                            relation: "partner",
                            related: "user_id.partner_id",
                            default: 1,
                        },
                        name: { string: "name", type: "char" },
                        start_date: { string: "start date", type: "date" },
                        stop_date: { string: "stop date", type: "date" },
                        start: { string: "start datetime", type: "datetime" },
                        stop: { string: "stop datetime", type: "datetime" },
                        delay: { string: "delay", type: "float" },
                        duration: { string: "Duration", type: "float", default: 1 },
                        allday: { string: "allday", type: "boolean" },
                        partner_ids: {
                            string: "attendees",
                            type: "one2many",
                            relation: "partner",
                            default: [[6, 0, [1]]],
                        },
                        type: { string: "type", type: "integer" },
                        event_type_id: {
                            string: "Event Type",
                            type: "many2one",
                            relation: "event_type",
                        },
                        color_event: {
                            string: "Color",
                            type: "integer",
                            related: "event_type_id.color_event_type",
                        },
                        is_hatched: { string: "Hatched", type: "boolean" },
                        is_striked: { string: "Striked", type: "boolean" },
                        res_model_name: { string: "Linked Model Name", type: "char" },
                    },
                    records: [
                        {
                            id: 1,
                            user_id: uid,
                            partner_id: 1,
                            name: "event 1",
                            start: "2016-12-11 00:00:00",
                            stop: "2016-12-11 00:00:00",
                            allday: false,
                            partner_ids: [1, 2, 3],
                            type: 1,
                            is_hatched: false,
                        },
                        {
                            id: 2,
                            user_id: uid,
                            partner_id: 1,
                            name: "event 2",
                            start: "2016-12-12 10:55:05",
                            stop: "2016-12-12 14:55:05",
                            allday: false,
                            partner_ids: [1, 2],
                            type: 3,
                            is_hatched: false,
                        },
                    ],
                    methods: {
                        check_access_rights() {
                            return Promise.resolve(true);
                        },
                    },
                },
                user: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        display_name: { string: "Displayed name", type: "char" },
                        partner_id: {
                            string: "partner",
                            type: "many2one",
                            relation: "partner",
                        },
                    },
                    records: [
                        { id: uid, display_name: "user 1", partner_id: 1 },
                        { id: 4, display_name: "user 4", partner_id: 4 },
                    ],
                },
                partner: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        display_name: { string: "Displayed name", type: "char" },
                        image: { string: "image", type: "integer" },
                    },
                    records: [
                        { id: 1, display_name: "partner 1", image: "AAA" },
                        { id: 2, display_name: "partner 2", image: "BBB" },
                        { id: 3, display_name: "partner 3", image: "CCC" },
                        { id: 4, display_name: "partner 4", image: "DDD" },
                    ],
                },
                filter_partner: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        user_id: { string: "user", type: "many2one", relation: "user" },
                        partner_id: {
                            string: "partner",
                            type: "many2one",
                            relation: "partner",
                        },
                        partner_checked: { string: "checked", type: "boolean" },
                    },
                    records: [
                        { id: 1, user_id: uid, partner_id: 1, partner_checked: true },
                        { id: 2, user_id: uid, partner_id: 2, partner_checked: true },
                        { id: 3, user_id: 4, partner_id: 3, partner_checked: true },
                    ],
                },
            },
        };
    });

    QUnit.test(`Linked record rendering`, async (assert) => {
        assert.expect(3);

        serverData.models.event.records.push({
            id: 3,
            user_id: 4,
            partner_id: 1,
            name: "event With record",
            start: "2016-12-11 09:00:00",
            stop: "2016-12-11 10:00:00",
            allday: false,
            partner_ids: [1, 2, 3],
            res_model_name: "Time Off",
        });

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar js_class="attendee_calendar" 
                          event_open_popup="1" 
                          date_start="start" 
                          date_stop="stop" 
                          all_day="allday" 
                          mode="month">
                              <field name="partner_ids" options="{'block': True, 'icon': 'fa fa-users'}"
                                     filters="1" widget="many2manyattendeeexpandable" write_model="filter_partner"
                                     write_field="partner_id" filter_field="partner_checked" avatar_field="avatar_128"
                              />
                              <field name="partner_id" string="Organizer" options="{'icon': 'fa fa-user-o'}"/>
                              <field name="user_id"/>
                              <field name="start"/>
                              <field name="stop"/>
                              <field name="allday"/>
                              <field name="res_model_name" invisible="not res_model_name" 
                                     options="{'icon': 'fa fa-link', 'shouldOpenRecord': true}"
                              />
                          </calendar>
            `,
            mockRPC(route, args) {
                if (route === "/web/dataset/call_kw/res.users/has_group") {
                    return Promise.resolve(true);
                } else if (route === "/web/dataset/call_kw/res.partner/get_attendee_detail") {
                    return Promise.resolve([]);
                } else if (route === "/calendar/check_credentials") {
                    return Promise.resolve({});
                }
            },
        });
        assert.containsOnce(
            target,
            ".o_calendar_renderer .fc-view-container",
            "should instance of fullcalendar"
        );
        await changeScale(target, "week");
        await clickEvent(target, 3);
        assert.containsOnce(target, ".fa-link", "A link icon should be present");
        assert.strictEqual(target.querySelector("li a[href='#']").textContent, "Time Off");
    });
});
