/** @odoo-module **/

import { registerCleanup } from "../../helpers/cleanup";
import { defaultLocalization } from "../../helpers/mock_services";
import {
    click,
    editInput,
    getFixture,
    makeDeferred,
    nextTick,
    patchDate,
    patchTimeZone,
    patchWithCleanup,
    triggerEvent,
} from "../../helpers/utils";
import {
    changeScale,
    clickDate,
    clickEvent,
    findEvent,
    findFilterPanelFilter,
    findFilterPanelSection,
    findPickedDate,
    findTimeRow,
    moveEventToAllDaySlot,
    moveEventToDate,
    moveEventToTime,
    navigate,
    pickDate,
    resizeEventToTime,
    selectAllDayRange,
    selectDateRange,
    selectTimeRange,
    toggleFilter,
    toggleSectionFilter,
} from "../../views/calendar/helpers";
import { makeView, setupViewRegistries } from "../../views/helpers";
import { createWebClient, doAction } from "../../webclient/helpers";
import { browser } from "@web/core/browser/browser";
import { dialogService } from "@web/core/dialog/dialog_service";
import { localization } from "@web/core/l10n/localization";
import { registry } from "@web/core/registry";
import { userService } from "@web/core/user_service";
import { CalendarYearRenderer } from "@web/views/calendar/calendar_year/calendar_year_renderer";
import { CharField } from "@web/views/fields/char/char_field";
import { actionService } from "@web/webclient/actions/action_service";

const fieldRegistry = registry.category("fields");
const preloadedDataRegistry = registry.category("preloadedData");
const serviceRegistry = registry.category("services");

let target;
let serverData;
const uid = -1;

QUnit.module("Views", ({ beforeEach }) => {
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
                        {
                            id: 3,
                            user_id: 4,
                            partner_id: 4,
                            name: "event 3",
                            start: "2016-12-12 15:55:05",
                            stop: "2016-12-12 16:55:05",
                            allday: false,
                            partner_ids: [1],
                            type: 2,
                            is_hatched: true,
                        },
                        {
                            id: 4,
                            user_id: uid,
                            partner_id: 1,
                            name: "event 4",
                            start: "2016-12-14 15:55:05",
                            stop: "2016-12-14 18:55:05",
                            allday: true,
                            partner_ids: [1],
                            type: 2,
                            is_hatched: false,
                            is_striked: true,
                        },
                        {
                            id: 5,
                            user_id: 4,
                            partner_id: 4,
                            name: "event 5",
                            start: "2016-12-13 15:55:05",
                            stop: "2016-12-20 18:55:05",
                            allday: false,
                            partner_ids: [2, 3],
                            type: 2,
                            is_hatched: true,
                        },
                        {
                            id: 6,
                            user_id: uid,
                            partner_id: 1,
                            name: "event 6",
                            start: "2016-12-18 08:00:00",
                            stop: "2016-12-18 09:00:00",
                            allday: false,
                            partner_ids: [3],
                            type: 3,
                            is_hatched: true,
                        },
                        {
                            id: 7,
                            user_id: uid,
                            partner_id: 1,
                            name: "event 7",
                            start: "2016-11-14 08:00:00",
                            stop: "2016-11-16 17:00:00",
                            allday: false,
                            partner_ids: [2],
                            type: 1,
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
                        image: { string: "image", type: "integer" },
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
                event_type: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        display_name: { string: "Displayed name", type: "char" },
                        color_event_type: { string: "Color", type: "integer" },
                    },
                    records: [
                        { id: 1, display_name: "Event Type 1", color_event_type: 1 },
                        { id: 2, display_name: "Event Type 2", color_event_type: 2 },
                        { id: 3, display_name: "Event Type 3 (color 4)", color_event_type: 4 },
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
            views: {
                "event,false,form": `
                <form>
                    <field name="name" />
                    <field name="allday" />
                    <group attrs="{'invisible': [['allday', '=', True]]}">
                        <field name="start" />
                        <field name="stop" />
                    </group>
                    <group attrs="{'invisible': [['allday', '=', False]]}">
                        <field name="start_date" />
                        <field name="stop_date" />
                    </group>
                </form>
            `,
                "event,1,form": `
                <form>
                    <field name="allday" invisible="1" />
                    <field name="start" attrs="{'invisible': [['allday', '=', False]]}" />
                    <field name="stop" attrs="{'invisible': [['allday', '=', True]]}" />
                </form>
            `,
            },
        };
    });

    QUnit.module("CalendarView");

    QUnit.test(`simple calendar rendering`, async (assert) => {
        assert.expect(24);

        serverData.models.event.records.push({
            id: 8,
            user_id: uid,
            partner_id: false,
            name: "event 7",
            start: "2016-12-18 09:00:00",
            stop: "2016-12-18 10:00:00",
            allday: false,
            partner_ids: [2],
            type: 1,
        });

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar event_open_popup="1" date_start="start" date_stop="stop" all_day="allday" mode="week" attendee="partner_ids" color="partner_id">
                    <filter name="user_id" avatar_field="image" />
                    <field name="partner_ids" write_model="filter_partner" write_field="partner_id" />
                    <field name="partner_id" filters="1" invisible="1" />
                </calendar>
            `,
        });

        assert.containsOnce(
            target,
            ".o_calendar_renderer .fc-view-container",
            "should instance of fullcalendar"
        );

        // test view scales
        assert.containsNone(
            target,
            ".fc-event",
            "By default, only the events of the current user are displayed (0 in this case)"
        );
        // display all events
        await click(target, ".o_calendar_filter_item[data-value='all'] input");
        assert.containsN(
            target,
            ".fc-event",
            9,
            "should display 9 events on the week (4 event + 5 days event)"
        );
        assert.containsN(
            target,
            ".o_calendar_sidebar tr:has(.ui-state-active) td",
            7,
            "week scale should highlight 7 days in mini calendar"
        );
        await click(target, ".scale_button_selection");
        await click(target, ".o_calendar_button_day"); // display only one day
        assert.containsN(target, ".fc-event", 2, "should display 2 events on the day");
        assert.containsOnce(
            target,
            ".o_calendar_sidebar .o_selected_range",
            "should highlight the target day in mini calendar"
        );
        await click(target, ".scale_button_selection");
        await click(target, ".o_calendar_button_month"); // display all the month
        // We display the events or partner 1 2 and 4. Partner 2 has nothing and Event 6 is for partner 6 (not displayed)
        await click(target, ".o_calendar_filter_item[data-value='all'] input");
        await click(
            target.querySelector(".o_calendar_filter .o_calendar_filter_item[data-value='1'] input")
        );
        await click(target, ".o_calendar_filter_item[data-value='2'] input");
        assert.containsN(
            target,
            ".fc-event",
            7,
            "should display 7 events on the month (5 events + 2 week event - 1 'event 6' is filtered + 1 'Undefined event')"
        );
        assert.containsN(
            target,
            ".o_calendar_sidebar td a",
            31,
            "month scale should highlight all days in mini calendar"
        );
        // test filters
        assert.containsN(
            target,
            ".o_calendar_sidebar .o_calendar_filter",
            2,
            "should display 2 filters"
        );
        const typeFilter = target.querySelectorAll(".o_calendar_filter")[1];
        assert.ok(!!typeFilter, "should display 'user' filter");
        assert.containsN(
            typeFilter,
            ".o_calendar_filter_item",
            3,
            "should display 3 filter items for 'user'"
        );
        // filters which has no value should show with string "Undefined", should not have any user image and should show at the last
        let lastFilter;
        {
            const filters = typeFilter.querySelectorAll(".o_calendar_filter_item");
            lastFilter = filters[filters.length - 1];
        }
        assert.strictEqual(
            lastFilter.hasAttribute("data-value"),
            false,
            "filters having false value should be displayed at last in filter items"
        );
        assert.strictEqual(
            lastFilter.querySelector(".o_cw_filter_title").textContent,
            "Undefined",
            "filters having false value should display 'Undefined' string"
        );
        assert.containsNone(
            lastFilter,
            "label img",
            "filters having false value should not have any user image"
        );
        const attendeesFilter = target.querySelectorAll(".o_calendar_filter")[0];
        assert.ok(!!attendeesFilter, "should display 'attendees' filter");
        assert.containsN(
            attendeesFilter,
            ".o_calendar_filter_item",
            3,
            "should display 3 filter items for 'attendees' who use write_model (checkall + 2 saved + Everything)"
        );
        assert.containsOnce(
            attendeesFilter,
            ".o-autocomplete",
            "should display one2many search bar for 'attendees' filter"
        );
        assert.containsN(
            target,
            ".fc-event",
            7,
            "should display 7 events ('event 5' counts for 2 because it spans two weeks and thus generate two fc-event elements)"
        );
        await click(target.querySelectorAll(".o_calendar_filter input[type=checkbox]")[1]); // click on partner 2
        assert.containsN(target, ".fc-event", 4, "should now only display 4 event");
        await click(target.querySelectorAll(".o_calendar_filter input[type=checkbox]")[2]);
        assert.containsNone(target, ".fc-event", "should not display any event anymore");
        // test search bar in filter
        await click(target, ".o_calendar_sidebar input[type=text]");
        let autoCompleteItems = document.body.querySelectorAll("ul.ui-autocomplete li");
        assert.strictEqual(
            autoCompleteItems.length,
            2,
            "should display 2 choices in one2many autocomplete"
        );
        await click(autoCompleteItems[0]);
        assert.containsN(
            attendeesFilter,
            ".o_calendar_filter_item",
            4,
            "should display 4 filter items for 'attendees'"
        );
        await click(target, ".o_calendar_sidebar input[type=text]");
        autoCompleteItems = document.body.querySelectorAll("ul.ui-autocomplete li");
        assert.strictEqual(
            autoCompleteItems[0].textContent,
            "partner 4",
            "should display the last choice in one2many autocomplete"
        );
        await click(target.querySelectorAll(".o_calendar_filter_item .o_remove")[1]);
        assert.containsN(
            attendeesFilter,
            ".o_calendar_filter_item",
            3,
            "click on remove then should display 3 filter items for 'attendees'"
        );
    });

    QUnit.test("filter panel autocomplete: updates when typing", async (assert) => {
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop">
                    <field name="partner_ids" write_model="filter_partner" write_field="partner_id" />
                </calendar>
            `,
        });
        const section = findFilterPanelSection(target, "partner_ids");
        assert.containsNone(section, ".o-autocomplete--dropdown-menu");
        assert.containsNone(section, ".o-autocomplete--dropdown-item");
        await click(section, ".o-autocomplete--input");
        assert.containsOnce(section, ".o-autocomplete--dropdown-menu");
        assert.containsN(section, ".o-autocomplete--dropdown-item", 2);
        assert.deepEqual(
            [...section.querySelectorAll(".o-autocomplete--dropdown-item")].map((el) =>
                el.textContent.trim()
            ),
            ["partner 3", "partner 4"]
        );

        const input = section.querySelector(".o-autocomplete--input");
        input.value = "partner 3";
        await triggerEvent(section, ".o-autocomplete--input", "input");
        assert.containsOnce(section, ".o-autocomplete--dropdown-menu");
        assert.containsOnce(section, ".o-autocomplete--dropdown-item");
        assert.strictEqual(
            section.querySelector(".o-autocomplete--dropdown-item").textContent.trim(),
            "partner 3"
        );

        input.value = "a string that would yield to no result as it is too very much convoluted";
        await triggerEvent(section, ".o-autocomplete--input", "input");
        assert.containsOnce(section, ".o-autocomplete--dropdown-menu");
        assert.containsOnce(section, ".o-autocomplete--dropdown-item");
        assert.strictEqual(
            section.querySelector(".o-autocomplete--dropdown-item").textContent.trim(),
            "No records"
        );
    });

    QUnit.test("add a filter with the search more dialog", async (assert) => {
        serverData.views["partner,false,search"] = `<search></search>`;
        serverData.views["partner,false,list"] = `
            <tree>
                <field name="display_name" />
            </tree>
        `;
        serverData.models.partner.records.push(
            { id: 5, display_name: "foo partner 5" },
            { id: 6, display_name: "foo partner 6" },
            { id: 7, display_name: "foo partner 7" },
            { id: 8, display_name: "foo partner 8" },
            { id: 9, display_name: "foo partner 9" },
            { id: 10, display_name: "foo partner 10" },
            { id: 11, display_name: "foo partner 11" },
            { id: 12, display_name: "foo partner 12" },
            { id: 13, display_name: "foo partner 13" }
        );
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop">
                    <field name="partner_ids" write_model="filter_partner" write_field="partner_id" />
                </calendar>
            `,
            mockRPC(route) {
                if (route.endsWith("/has_group")) {
                    return true;
                }
            },
        });
        const section = findFilterPanelSection(target, "partner_ids");
        assert.containsN(section, ".o_calendar_filter_item", 3);
        assert.deepEqual(
            [...section.querySelectorAll(".o_calendar_filter_item")].map((el) =>
                el.textContent.trim()
            ),
            ["partner 2", "partner 1", "Everything"]
        );

        // Open the autocomplete dropdown
        assert.containsNone(section, ".o-autocomplete--dropdown-menu");
        assert.containsNone(section, ".o-autocomplete--dropdown-item");
        await click(section, ".o-autocomplete--input");
        assert.containsOnce(section, ".o-autocomplete--dropdown-menu");
        assert.containsN(section, ".o-autocomplete--dropdown-item", 9);
        assert.deepEqual(
            [...section.querySelectorAll(".o-autocomplete--dropdown-item")].map((el) =>
                el.textContent.trim()
            ),
            [
                "partner 3",
                "partner 4",
                "foo partner 5",
                "foo partner 6",
                "foo partner 7",
                "foo partner 8",
                "foo partner 9",
                "foo partner 10",
                "Search More...",
            ]
        );

        // Change the search term
        const input = section.querySelector(".o-autocomplete--input");
        input.value = "foo";
        await triggerEvent(section, ".o-autocomplete--input", "input");
        assert.containsOnce(section, ".o-autocomplete--dropdown-menu");
        assert.containsN(section, ".o-autocomplete--dropdown-item", 9);
        assert.deepEqual(
            [...section.querySelectorAll(".o-autocomplete--dropdown-item")].map((el) =>
                el.textContent.trim()
            ),
            [
                "foo partner 5",
                "foo partner 6",
                "foo partner 7",
                "foo partner 8",
                "foo partner 9",
                "foo partner 10",
                "foo partner 11",
                "foo partner 12",
                "Search More...",
            ]
        );

        // Open the search more dialog
        assert.containsNone(target, ".modal");
        await click(section, ".o-autocomplete--dropdown-item:last-child");
        assert.containsOnce(target, ".modal");
        assert.containsN(target, ".modal .o_data_row", 9);
        assert.deepEqual(
            [...target.querySelectorAll(".modal .o_data_row")].map((el) => el.textContent.trim()),
            [
                "foo partner 5",
                "foo partner 6",
                "foo partner 7",
                "foo partner 8",
                "foo partner 9",
                "foo partner 10",
                "foo partner 11",
                "foo partner 12",
                "foo partner 13",
            ]
        );
        assert.containsOnce(target, ".modal .o_searchview_facet");
        assert.strictEqual(
            target.querySelector(".modal .o_searchview_facet").textContent.trim(),
            "Quick search: foo"
        );

        // Choose a record
        await click(target, ".modal .o_data_row:first-child > td:first-child");
        assert.containsNone(target, ".modal");
        assert.containsN(section, ".o_calendar_filter_item", 4);
        assert.deepEqual(
            [...section.querySelectorAll(".o_calendar_filter_item")].map((el) =>
                el.textContent.trim()
            ),
            ["partner 2", "partner 1", "foo partner 5", "Everything"]
        );
        assert.strictEqual(input.value, "");

        // Open the autocomplete dropdown
        assert.containsNone(section, ".o-autocomplete--dropdown-menu");
        assert.containsNone(section, ".o-autocomplete--dropdown-item");
        await click(section, ".o-autocomplete--input");
        assert.containsOnce(section, ".o-autocomplete--dropdown-menu");
        assert.containsN(section, ".o-autocomplete--dropdown-item", 9);
        assert.deepEqual(
            [...section.querySelectorAll(".o-autocomplete--dropdown-item")].map((el) =>
                el.textContent.trim()
            ),
            [
                "partner 3",
                "partner 4",
                "foo partner 6",
                "foo partner 7",
                "foo partner 8",
                "foo partner 9",
                "foo partner 10",
                "foo partner 11",
                "Search More...",
            ]
        );

        // Change the search term
        input.value = "foo";
        await triggerEvent(section, ".o-autocomplete--input", "input");
        assert.containsOnce(section, ".o-autocomplete--dropdown-menu");
        assert.containsN(section, ".o-autocomplete--dropdown-item", 9);
        assert.deepEqual(
            [...section.querySelectorAll(".o-autocomplete--dropdown-item")].map((el) =>
                el.textContent.trim()
            ),
            [
                "foo partner 6",
                "foo partner 7",
                "foo partner 8",
                "foo partner 9",
                "foo partner 10",
                "foo partner 11",
                "foo partner 12",
                "foo partner 13",
                "Search More...",
            ]
        );

        // Open the search more dialog
        assert.containsNone(target, ".modal");
        await click(section, ".o-autocomplete--dropdown-item:last-child");
        assert.containsOnce(target, ".modal");
        assert.containsN(target, ".modal .o_data_row", 8);
        assert.deepEqual(
            [...target.querySelectorAll(".modal .o_data_row")].map((el) => el.textContent.trim()),
            [
                "foo partner 6",
                "foo partner 7",
                "foo partner 8",
                "foo partner 9",
                "foo partner 10",
                "foo partner 11",
                "foo partner 12",
                "foo partner 13",
            ]
        );
        assert.containsOnce(target, ".modal .o_searchview_facet");
        assert.strictEqual(
            target.querySelector(".modal .o_searchview_facet").textContent.trim(),
            "Quick search: foo"
        );

        // Close the search more dialog without choosing a record
        await click(target, ".modal .o_form_button_cancel");
        assert.containsNone(target, ".modal");
        assert.containsN(section, ".o_calendar_filter_item", 4);
        assert.deepEqual(
            [...section.querySelectorAll(".o_calendar_filter_item")].map((el) =>
                el.textContent.trim()
            ),
            ["partner 2", "partner 1", "foo partner 5", "Everything"]
        );
        assert.strictEqual(input.value, "");
    });

    QUnit.test(
        `delete attribute on calendar doesn't show delete button in popover`,
        async (assert) => {
            assert.expect(2);

            await makeView({
                type: "calendar",
                resModel: "event",
                serverData,
                arch: `
                    <calendar event_open_popup="1" date_start="start" date_stop="stop" all_day="allday" delete="0" mode="month" />
                `,
            });

            await clickEvent(target, 4);
            assert.containsOnce(target, ".o_cw_popover", "should open a popover clicking on event");
            assert.containsNone(
                target,
                ".o_cw_popover .o_cw_popover_delete",
                "should not have the 'Delete' Button"
            );
        }
    );

    QUnit.test(`breadcrumbs are updated with the displayed period`, async (assert) => {
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" />
            `,
        });

        // displays week mode by default
        assert.strictEqual(
            target.querySelector(".o_control_panel .breadcrumb-item.active").textContent,
            "undefined (Dec 11 – 17, 2016)",
            "should display the current week"
        );

        // switch to day mode
        await changeScale(target, "day");
        assert.strictEqual(
            target.querySelector(".o_control_panel .breadcrumb-item.active").textContent,
            "undefined (December 12, 2016)",
            "should display the current day"
        );

        // switch to month mode
        await changeScale(target, "month");
        assert.strictEqual(
            target.querySelector(".o_control_panel .breadcrumb-item.active").textContent,
            "undefined (December 2016)",
            "should display the current month"
        );

        // switch to year mode
        await changeScale(target, "year");
        assert.strictEqual(
            target.querySelector(".o_control_panel .breadcrumb-item.active").textContent,
            "undefined (2016)",
            "should display the current year"
        );
    });

    QUnit.test(`create and change events`, async (assert) => {
        assert.expect(28);

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar event_open_popup="1" date_start="start" date_stop="stop" all_day="allday" mode="month" />
            `,
            mockRPC(route, { args, method }) {
                if (method === "write") {
                    assert.deepEqual(
                        args[1],
                        { name: "event 4 modified" },
                        "should update the record"
                    );
                }
            },
        });

        assert.containsOnce(target, ".fc-dayGridMonth-view", "should display in month mode");

        // click on an existing event to open the formViewDialog
        await clickEvent(target, 4);
        assert.containsOnce(target, ".o_cw_popover", "should open a popover clicking on event");
        assert.containsOnce(
            target,
            ".o_cw_popover .o_cw_popover_edit",
            "popover should have an edit button"
        );
        assert.containsOnce(
            target,
            ".o_cw_popover .o_cw_popover_delete",
            "popover should have a delete button"
        );
        assert.containsOnce(
            target,
            ".o_cw_popover .o_cw_popover_close",
            "popover should have a close button"
        );

        await click(target, ".o_cw_popover .o_cw_popover_edit");
        assert.containsOnce(
            target,
            ".modal-body",
            "should open the form view in dialog when click on event"
        );

        await editInput(target.querySelector(".modal-body input"), null, "event 4 modified");
        await click(target, ".modal-footer .o_form_button_save");
        assert.containsNone(target, ".modal-body", "save button should close the modal");

        // create a new event, quick create only
        await clickDate(target, "2016-12-13");
        assert.containsOnce(
            target,
            ".o-calendar-quick-create",
            "should open the quick create dialog"
        );

        await editInput(target, ".o-calendar-quick-create--input", "new event in quick create");
        await click(target, ".o-calendar-quick-create--create-btn");
        assert.strictEqual(
            findEvent(target, 8).textContent,
            "new event in quick create",
            "should display the new record after quick create"
        );
        assert.containsN(
            target,
            "td.fc-event-container[colspan]",
            2,
            "should the new record have only one day"
        );

        // create a new event, quick create only (validated by pressing enter key)
        await clickDate(target, "2016-12-13");
        assert.containsOnce(
            target,
            ".o-calendar-quick-create",
            "should open the quick create dialog"
        );

        await editInput(
            target,
            ".o-calendar-quick-create--input",
            "new event in quick create validated by pressing enter key."
        );
        await triggerEvent(target, ".o-calendar-quick-create--input", "keyup", { key: "Enter" });
        assert.strictEqual(
            findEvent(target, 9).textContent,
            "new event in quick create validated by pressing enter key.",
            "should display the new record by pressing enter key"
        );

        // create a new event and edit it
        await clickDate(target, "2016-12-27");
        assert.containsOnce(
            target,
            ".o-calendar-quick-create",
            "should open the quick create dialog"
        );

        await editInput(target, ".o-calendar-quick-create--input", "coucou");
        await click(target, ".o-calendar-quick-create--edit-btn");
        assert.containsOnce(target, ".modal", "should open the slow create dialog");
        assert.strictEqual(
            target.querySelector(".modal .modal-title").textContent,
            "New Event",
            "should use the string attribute as modal title"
        );
        assert.strictEqual(
            target.querySelector(`.modal [name="name"] input`).value,
            "coucou",
            "should have set the name from the quick create dialog"
        );

        await click(target, ".modal-footer .o_form_button_save");
        assert.strictEqual(
            findEvent(target, 10).textContent,
            "coucou",
            "should display the new record with string attribute"
        );

        // create a new event with 2 days
        await selectDateRange(target, "2016-12-20", "2016-12-21");
        await editInput(target, ".o-calendar-quick-create--input", "new event in quick create 2");

        await click(target, ".o-calendar-quick-create--edit-btn");
        assert.strictEqual(
            target.querySelector(`.modal .o_form_view [name="name"] input`).value,
            "new event in quick create 2",
            "should open the formViewDialog with default values"
        );

        await click(target, ".modal-footer .o_form_button_save");
        assert.containsNone(target, ".modal", "should close dialogs");

        const newEvent = findEvent(target, 11);
        assert.strictEqual(
            newEvent.textContent,
            "new event in quick create 2",
            "should display the 2 days new record"
        );
        assert.hasAttrValue(
            newEvent.closest(".fc-event-container"),
            "colspan",
            "2",
            "the new record should have 2 days"
        );

        await clickEvent(target, 11);
        const popoverDescription = target.querySelector(".o_cw_popover .list-group-item");
        assert.strictEqual(
            popoverDescription.children[1].textContent,
            "December 20-21, 2016",
            "The popover description should indicate the correct range"
        );
        assert.strictEqual(
            popoverDescription.children[2].textContent,
            "(2 days)",
            "The popover description should indicate 2 days"
        );
        await click(target, ".o_cw_popover_close");

        // delete the a record
        await clickEvent(target, 4);
        await click(target, ".o_cw_popover_delete");
        assert.strictEqual(
            target.querySelector(".modal-title").textContent,
            "Confirmation",
            "should display the confirm message"
        );

        await click(target, ".modal-footer button.btn-primary");
        assert.notOk(findEvent(target, 4), "the record should be deleted");

        assert.containsN(target, ".fc-event-container .fc-event", 10, "should display 10 events");
        // move to next month
        await navigate(target, "next");
        assert.containsNone(target, ".fc-event-container .fc-event", "should display 0 events");

        await navigate(target, "prev");
        await selectDateRange(target, "2016-12-20", "2016-12-21");
        await editInput(target, ".o-calendar-quick-create--input", "test");
        await click(target, ".o-calendar-quick-create--create-btn");
    });

    QUnit.test(`quickcreate with custom create_name_field`, async (assert) => {
        assert.expect(4);

        serverData.models.custom_event = {
            fields: {
                id: { string: "ID", type: "integer" },
                x_name: { string: "name", type: "char" },
                x_start_date: { string: "start date", type: "date" },
            },
            records: [{ id: 1, x_name: "some event", x_start_date: "2016-12-06" }],
            methods: {
                async check_access_rights() {
                    return true;
                },
            },
        };

        await makeView({
            type: "calendar",
            resModel: "custom_event",
            serverData,
            arch: `
                <calendar date_start="x_start_date" create_name_field="x_name" mode="month" />
            `,
            mockRPC(route, { args, method }) {
                if (method === "create") {
                    assert.deepEqual(
                        args[0],
                        {
                            x_name: "custom event in quick create",
                            x_start_date: "2016-12-13",
                        },
                        "the custom create_name_field should be used instead of `name`"
                    );
                }
            },
        });

        // create a new event
        await clickDate(target, "2016-12-13");
        assert.containsOnce(
            target,
            ".o-calendar-quick-create",
            "should open the quick create dialog"
        );

        await editInput(target, ".o-calendar-quick-create--input", "custom event in quick create");
        await click(target, ".o-calendar-quick-create--create-btn");
        assert.containsOnce(
            target,
            `.fc-event[data-event-id="2"]`,
            "should display the new custom event record"
        );
        assert.strictEqual(findEvent(target, 2).textContent, "custom event in quick create");
    });

    QUnit.test(`quickcreate switching to actual create for required fields`, async (assert) => {
        assert.expect(4);

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" mode="month" event_open_popup="1" />
            `,
            mockRPC(route, { method }) {
                if (method === "create") {
                    return Promise.reject({
                        message: {
                            code: 200,
                            data: {},
                            message: "Odoo server error",
                        },
                        event: new Event("server_error"),
                    });
                }
            },
        });

        // create a new event
        await clickDate(target, "2016-12-13");
        assert.strictEqual(
            target.querySelector(".modal-title").textContent,
            "New Event",
            "should open the quick create dialog"
        );

        await editInput(target, ".o-calendar-quick-create--input", "custom event in quick create");
        await click(target, ".o-calendar-quick-create--create-btn");
        assert.containsNone(target, ".o-calendar-quick-create");
        assert.strictEqual(
            target.querySelector(".modal-title").textContent,
            "New Event",
            "should have switched to a bigger modal for an actual create rather than quickcreate"
        );
        assert.containsOnce(
            target,
            ".modal .o_form_view .o_form_editable",
            "should open the full event form view in a dialog"
        );
    });

    QUnit.test(`open multiple event form at the same time`, async (assert) => {
        let counter = 0;
        patchWithCleanup(dialogService, {
            start() {
                const result = this._super(...arguments);
                return {
                    ...result,
                    add() {
                        counter++;
                        return result.add(...arguments);
                    },
                };
            },
        });

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" mode="month" event_open_popup="1" quick_add="0">
                    <field name="name" />
                </calendar>
            `,
        });

        for (let i = 0; i < 5; i++) {
            await clickDate(target, "2016-12-13");
        }
        await nextTick();

        assert.strictEqual(counter, 5, "there should had been 5 attemps to open a modal");
        assert.containsOnce(target, ".modal", "there should be only one open modal");
    });

    QUnit.test(`create event with timezone in week mode European locale`, async (assert) => {
        assert.expect(4);

        serverData.models.event.records = [];
        patchTimeZone(120);
        patchWithCleanup(localization, defaultLocalization);

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" mode="week" event_open_popup="1">
                    <field name="name" />
                    <field name="start" />
                    <field name="allday" />
                </calendar>
            `,
            mockRPC(route, { method, args }) {
                if (method === "create") {
                    assert.deepEqual(
                        args,
                        [
                            {
                                allday: false,
                                name: "new event",
                                start: "2016-12-13 06:00:00",
                                stop: "2016-12-13 08:00:00",
                            },
                        ],
                        "should create this event"
                    );
                }
            },
        });

        await selectTimeRange(target, "2016-12-13 08:00:00", "2016-12-13 10:00:00");
        assert.strictEqual(
            target.querySelector(".fc-content .fc-time").textContent,
            "8:00 - 10:00",
            "should display the time in the calendar sticker"
        );

        await editInput(target, ".o-calendar-quick-create--input", "new event");
        await click(target, ".o-calendar-quick-create--create-btn");
        assert.strictEqual(
            target.querySelector(".fc-event .o_event_title").textContent,
            "new event",
            "should display the new event with title"
        );

        // delete record
        await clickEvent(target, 1);
        await click(target, ".o_cw_popover .o_cw_popover_delete");
        await click(target, ".modal button.btn-primary");
        assert.containsNone(target, ".fc-content", "should delete the record");
    });

    QUnit.test(`default week start (US)`, async (assert) => {
        // if not given any option, default week start is on Sunday
        assert.expect(3);

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" mode="week" />
            `,
            mockRPC(route, { method, model, kwargs }) {
                if (model === "event" && method === "search_read") {
                    assert.deepEqual(
                        kwargs.domain,
                        [
                            ["start", "<=", "2016-12-17 22:59:59"],
                            ["stop", ">=", "2016-12-10 23:00:00"],
                        ],
                        "The domain to search events in should be correct"
                    );
                }
            },
        });

        const dayHeaders = target.querySelectorAll(".fc-day-header");
        assert.strictEqual(
            dayHeaders[0].textContent,
            "Sun 11",
            "The first day of the week should be Sunday"
        );
        assert.strictEqual(
            dayHeaders[dayHeaders.length - 1].textContent,
            "Sat 17",
            "The last day of the week should be Saturday"
        );
    });

    QUnit.test(`European week start`, async (assert) => {
        assert.expect(3);

        // the week start depends on the locale
        patchWithCleanup(localization, { weekStart: 1 });

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" mode="week" />
            `,
            mockRPC(route, { method, model, kwargs }) {
                if (model === "event" && method === "search_read") {
                    // called twice (once for records and once for filters)
                    assert.deepEqual(
                        kwargs.domain,
                        [
                            ["start", "<=", "2016-12-18 22:59:59"],
                            ["stop", ">=", "2016-12-11 23:00:00"],
                        ],
                        "The domain to search events in should be correct"
                    );
                }
            },
        });

        const dayHeaders = target.querySelectorAll(".fc-day-header");
        assert.strictEqual(
            dayHeaders[0].textContent,
            "Mon 12",
            "The first day of the week should be Monday"
        );
        assert.strictEqual(
            dayHeaders[dayHeaders.length - 1].textContent,
            "Sun 18",
            "The last day of the week should be Sunday"
        );
    });

    QUnit.test(`week numbering`, async (assert) => {
        // The week is now calculated by FullCalendar (ISO week). If it's start a sunday it
        // returns the week of the monday.

        patchWithCleanup(localization, { weekStart: 7 });

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" mode="week" />
            `,
        });

        assert.strictEqual(target.querySelector(".fc-week-number").textContent, "Week 50");
    });

    QUnit.test(`render popover`, async (assert) => {
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" mode="week">
                    <field name="name" string="Custom Name" />
                    <field name="partner_id" />
                </calendar>
            `,
        });

        await clickEvent(target, 4);
        assert.containsOnce(target, ".o_cw_popover", "should open a popover clicking on event");
        assert.strictEqual(
            target.querySelector(".o_cw_popover .popover-header").textContent,
            "event 4",
            "popover should have a title 'event 4'"
        );
        assert.containsOnce(
            target,
            ".o_cw_popover .o_cw_popover_edit",
            "popover should have an edit button"
        );
        assert.containsOnce(
            target,
            ".o_cw_popover .o_cw_popover_delete",
            "popover should have a delete button"
        );
        assert.containsOnce(
            target,
            ".o_cw_popover .o_cw_popover_close",
            "popover should have a close button"
        );
        assert.strictEqual(
            target.querySelector(".o_cw_popover .list-group-item b.text-capitalize").textContent,
            "December 14, 2016",
            "should display date 'December 14, 2016'"
        );
        assert.containsN(
            target,
            ".o_cw_popover .o_cw_popover_fields_secondary .list-group-item",
            2,
            "popover should have a two fields"
        );

        const groups = target.querySelectorAll(
            ".o_cw_popover .o_cw_popover_fields_secondary .list-group-item"
        );
        assert.containsOnce(groups[0], ".o_field_char", "should apply char widget");
        assert.strictEqual(
            groups[0].querySelector("strong").textContent,
            "Custom Name: ",
            "label should be a 'Custom Name'"
        );
        assert.strictEqual(
            groups[0].querySelector(".o_field_char").textContent,
            "event 4",
            "value should be a 'event 4'"
        );
        assert.containsOnce(groups[1], ".o_form_uri", "should apply m20 widget");
        assert.strictEqual(
            groups[1].querySelector("strong").textContent,
            "user: ",
            "label should be a 'user'"
        );
        assert.strictEqual(
            groups[1].querySelector(".o_form_uri").textContent,
            "partner 1",
            "value should be a 'partner 1'"
        );

        await click(target, ".o_cw_popover .o_cw_popover_close");
        assert.containsNone(target, ".o_cw_popover", "should close a popover");
    });

    QUnit.test(`render popover with modifiers`, async (assert) => {
        serverData.models.event.fields.priority = {
            string: "Priority",
            type: "selection",
            selection: [
                ["0", "Normal"],
                ["1", "Important"],
            ],
        };

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" mode="week">
                    <field name="priority" widget="priority" readonly="1" />
                    <field name="is_hatched" invisible="1" />
                    <field name="partner_id" attrs="{'invisible': [['is_hatched', '=', False]]}" />
                    <field name="start" attrs="{'invisible': [['is_hatched', '=', True]]}" />
                </calendar>
            `,
        });

        await clickEvent(target, 4);
        assert.containsOnce(target, ".o_cw_popover", "should open a popover clicking on event");
        assert.containsOnce(
            target,
            ".o_cw_popover .o_priority span.o_priority_star",
            "priority field should not be editable"
        );
        assert.containsNone(
            target,
            ".o_cw_popover li.o_invisible_modifier",
            "partner_id field should be invisible"
        );
        assert.containsOnce(
            target,
            ".o_cw_popover .o_field_datetime",
            "The start date and time should be visible"
        );

        await click(target, ".o_cw_popover .o_cw_popover_close");
        assert.containsNone(target, ".o_cw_popover", "should close a popover");
    });

    QUnit.test(`render popover with widget which has specialData attribute`, async (assert) => {
        assert.expect(3);

        fieldRegistry.add("specialWidget", CharField);
        preloadedDataRegistry.add("specialWidget", {
            loadOnTypes: ["char"],
            preload: () => {
                assert.step("_fetchSpecialDataForMyWidget");
            },
        });

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" mode="week">
                    <field name="name" string="Custom Name" widget="specialWidget" />
                    <field name="partner_id" />
                </calendar>
            `,
        });

        await clickEvent(target, 4);
        assert.containsOnce(target, ".o_cw_popover", "should open a popover clicking on event");
        assert.verifySteps(["_fetchSpecialDataForMyWidget"]);
    });

    QUnit.test("render popover: inside fullcalendar popover", async (assert) => {
        assert.expect(13);

        // add 10 records the same day
        serverData.models.event.records = Array.from({ length: 10 }).map((_, i) => ({
            id: i + 1,
            name: `event ${i + 1}`,
            start: "2016-12-14 10:00:00",
            stop: "2016-12-14 15:00:00",
            user_id: uid,
        }));

        let expectedRequest;
        serviceRegistry.add(
            "action",
            {
                ...actionService,
                start() {
                    const result = actionService.start(...arguments);
                    const doAction = result.doAction;
                    result.doAction = (request) => {
                        assert.deepEqual(request, expectedRequest);
                        return doAction(request);
                    };
                    return result;
                },
            },
            { force: true }
        );

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" mode="month">
                    <field name="name" string="Custom Name" />
                    <field name="partner_id" />
                </calendar>
            `,
            mockRPC(route, { method }) {
                if (method === "get_formview_id") {
                    return Promise.resolve(false);
                }
            },
        });

        const visibleEventsSelector = ":not(.fc-limited) > :not(.fc-limited) > .fc-event";
        assert.containsN(target, visibleEventsSelector, 4);

        assert.containsOnce(target, ".fc-more");
        assert.strictEqual(target.querySelector(".fc-more").textContent, "+6 more");

        assert.containsNone(target, ".fc-popover");
        await click(target, ".fc-more");
        assert.containsOnce(target, ".fc-popover");
        assert.containsN(target, `.fc-popover ${visibleEventsSelector}`, 10);

        assert.containsNone(target, ".o_cw_popover");
        await click(target, ".fc-popover .fc-event:nth-child(1)");
        assert.containsOnce(target, ".o_cw_popover");

        await triggerEvent(target, ".o_cw_popover .o_cw_popover_edit", "mousedown");
        assert.containsOnce(target, ".o_cw_popover");
        assert.containsOnce(target, ".fc-popover");

        expectedRequest = {
            type: "ir.actions.act_window",
            res_model: "event",
            res_id: 1,
            views: [[false, "form"]],
            target: "current",
            context: {},
        };
        await click(target, ".o_cw_popover .o_cw_popover_edit");
        assert.containsNone(target, ".o_cw_popover");
        assert.containsOnce(target, ".fc-popover");
    });

    QUnit.test(`attributes hide_date and hide_time`, async (assert) => {
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" hide_date="1" hide_time="1" mode="month" />
            `,
        });

        await clickEvent(target, 4);
        assert.containsNone(
            target,
            ".o_cw_popover .list-group-item",
            "popover should not contain date/time"
        );
    });

    QUnit.test(
        `create event with timezone in week mode with formViewDialog European locale`,
        async (assert) => {
            assert.expect(7);

            patchWithCleanup(localization, defaultLocalization);
            patchTimeZone(120);
            serverData.models.event.records = [];
            serverData.models.event.onchanges = {
                allday(obj) {
                    if (obj.allday) {
                        obj.start_date = (obj.start && obj.start.split(" ")[0]) || obj.start_date;
                        obj.stop_date =
                            (obj.stop && obj.stop.split(" ")[0]) || obj.stop_date || obj.start_date;
                    } else {
                        obj.start = (obj.start_date && obj.start_date + " 00:00:00") || obj.start;
                        obj.stop =
                            (obj.stop_date && obj.stop_date + " 00:00:00") || obj.stop || obj.start;
                    }
                },
            };
            let expectedEvent;

            await makeView({
                type: "calendar",
                resModel: "event",
                serverData,
                arch: `
                    <calendar date_start="start" date_stop="stop" all_day="allday" mode="week" event_open_popup="1">
                        <field name="name" />
                    </calendar>
                `,
                mockRPC(route, { args, kwargs, method }) {
                    if (method === "create") {
                        assert.deepEqual(
                            kwargs.context,
                            {
                                default_name: "new event",
                                default_start: "2016-12-13 06:00:00",
                                default_stop: "2016-12-13 08:00:00",
                                default_allday: false,
                                lang: "en",
                                tz: "taht",
                                uid: 7,
                            },
                            "should send the context to create events"
                        );
                    } else if (method === "write") {
                        assert.deepEqual(args[1], expectedEvent, "should move the event");
                    }
                },
            });

            await selectTimeRange(target, "2016-12-13 08:00:00", "2016-12-13 10:00:00");
            await editInput(target, ".o-calendar-quick-create--input", "new event");
            await click(target, ".o-calendar-quick-create--edit-btn");

            let input = target.querySelector(".o_field_widget[name='start'] input");
            assert.strictEqual(input.value, "12/13/2016 08:00:00", "should display the datetime");

            // Set allday to true in formViewDialog
            await click(target, ".modal .o_field_boolean[name='allday'] input");
            input = target.querySelector(".o_field_widget[name='start_date'] input");
            assert.strictEqual(input.value, "12/13/2016", "should display the date");

            await click(target, ".modal .o_field_boolean[name='allday'] input");
            input = target.querySelector(".o_field_widget[name='start'] input");
            assert.strictEqual(
                input.value,
                "12/13/2016 02:00:00",
                "should display the datetime from the date with the timezone"
            );

            // use datepicker to enter a date: 12/13/2016 08:00:00
            await click(target, `.o_field_widget[name="start"] .o_datepicker .o_datepicker_input`);
            await click(
                document.body,
                `.bootstrap-datetimepicker-widget .picker-switch a[data-action="togglePicker"]`
            );
            await click(
                document.body,
                `.bootstrap-datetimepicker-widget .timepicker .timepicker-hour`
            );
            await click(
                document.body.querySelectorAll(
                    `.bootstrap-datetimepicker-widget .timepicker-hours td.hour`
                )[8]
            );
            await click(
                document.body,
                `.bootstrap-datetimepicker-widget .picker-switch a[data-action="close"]`
            );

            // use datepicker to enter a date: 12/13/2016 10:00:00
            await click(target, `.o_field_widget[name="stop"] .o_datepicker .o_datepicker_input`);
            await click(
                document.body,
                `.bootstrap-datetimepicker-widget .picker-switch a[data-action="togglePicker"]`
            );
            await click(
                document.body,
                `.bootstrap-datetimepicker-widget .timepicker .timepicker-hour`
            );
            await click(
                document.body.querySelectorAll(
                    `.bootstrap-datetimepicker-widget .timepicker-hours td.hour`
                )[10]
            );
            await click(
                document.body,
                `.bootstrap-datetimepicker-widget .picker-switch a[data-action="close"]`
            );

            await click(target, ".modal-footer .o_form_button_save");
            assert.strictEqual(
                findEvent(target, 1).querySelector(".o_event_title").textContent,
                "new event",
                "should display the new event with title"
            );

            // Move this event to another day
            expectedEvent = {
                allday: false,
                start: "2016-12-12 06:00:00",
                stop: "2016-12-12 08:00:00",
            };
            await moveEventToTime(target, 1, "2016-12-12 08:00:00");

            // Move to "All day"
            expectedEvent = {
                allday: true,
                start: "2016-12-12",
                stop: "2016-12-12",
            };
            await moveEventToAllDaySlot(target, 1, "2016-12-12");
        }
    );

    QUnit.test(`create event with timezone in week mode American locale`, async (assert) => {
        assert.expect(3);

        patchWithCleanup(localization, defaultLocalization);
        patchTimeZone(120);
        serverData.models.event.records = [];

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" event_open_popup="1">
                    <field name="name" />
                    <field name="start" />
                    <field name="allday" />
                </calendar>
            `,
            mockRPC(route, { kwargs, method }) {
                if (method === "create") {
                    assert.deepEqual(
                        kwargs.context,
                        {
                            default_name: "new event",
                            default_start: "2016-12-13 04:00:00",
                            default_stop: "2016-12-13 06:00:00",
                            default_allday: false,
                            lang: "en",
                            tz: "taht",
                            uid: 7,
                        },
                        "should send the context to create events"
                    );
                }
            },
        });

        await selectTimeRange(target, "2016-12-13 06:00:00", "2016-12-13 08:00:00");
        await editInput(target, ".o-calendar-quick-create--input", "new event");
        await click(target, ".o-calendar-quick-create--create-btn");
        assert.strictEqual(
            findEvent(target, 1).querySelector(".o_event_title").textContent,
            "new event",
            "should display the new event with title"
        );

        // delete record
        await clickEvent(target, 1);
        await click(target, ".o_cw_popover .o_cw_popover_delete");
        await click(target, ".modal button.btn-primary");
        assert.containsNone(target, ".fc-content", "should delete the record");
    });

    QUnit.test(`fetch event when being in timezone`, async (assert) => {
        assert.expect(3);

        patchTimeZone(660);

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" mode="week">
                    <field name="name" />
                    <field name="start" />
                    <field name="allday" />
                </calendar>
            `,
            mockRPC(route, { kwargs, method, model }) {
                if (method === "search_read" && model === "event") {
                    assert.deepEqual(
                        kwargs.domain,
                        [
                            ["start", "<=", "2016-12-17 12:59:59"],
                            ["stop", ">=", "2016-12-10 13:00:00"],
                        ],
                        "The domain should contain the right range"
                    );
                }
            },
        });

        const headers = target.querySelectorAll(".fc-day-header");
        assert.strictEqual(
            headers[0].textContent,
            "Sun 11",
            "The calendar start date should be 2016-12-11"
        );
        assert.strictEqual(
            headers[headers.length - 1].textContent,
            "Sat 17",
            "The calendar start date should be 2016-12-17"
        );
    });

    QUnit.test(
        `create event with timezone in week mode with formViewDialog American locale`,
        async (assert) => {
            assert.expect(7);

            patchWithCleanup(localization, defaultLocalization);
            patchTimeZone(120);
            serverData.models.event.records = [];
            serverData.models.event.onchanges = {
                allday(obj) {
                    if (obj.allday) {
                        obj.start_date = (obj.start && obj.start.split(" ")[0]) || obj.start_date;
                        obj.stop_date =
                            (obj.stop && obj.stop.split(" ")[0]) || obj.stop_date || obj.start_date;
                    } else {
                        obj.start = (obj.start_date && obj.start_date + " 00:00:00") || obj.start;
                        obj.stop =
                            (obj.stop_date && obj.stop_date + " 00:00:00") || obj.stop || obj.start;
                    }
                },
            };
            let expectedEvent = null;

            await makeView({
                type: "calendar",
                resModel: "event",
                serverData,
                arch: `
                    <calendar date_start="start" date_stop="stop" all_day="allday" mode="week" event_open_popup="1">
                        <field name="name" />
                    </calendar>
                `,
                mockRPC(route, { args, kwargs, method }) {
                    if (method === "create") {
                        assert.deepEqual(
                            kwargs.context,
                            {
                                default_name: "new event",
                                default_start: "2016-12-13 06:00:00",
                                default_stop: "2016-12-13 08:00:00",
                                default_allday: false,
                                lang: "en",
                                tz: "taht",
                                uid: 7,
                            },
                            "should send the context to create events"
                        );
                    } else if (method === "write") {
                        assert.deepEqual(args[1], expectedEvent, "should move the event");
                    }
                },
            });

            await selectTimeRange(target, "2016-12-13 08:00:00", "2016-12-13 10:00:00");
            await editInput(target, ".o-calendar-quick-create--input", "new event");
            await click(target, ".o-calendar-quick-create--edit-btn");
            assert.strictEqual(
                target.querySelector(`.o_field_widget[name="start"] input`).value,
                "12/13/2016 08:00:00",
                "should display the datetime"
            );

            await click(target, `.modal .o_field_boolean[name="allday"] input`);
            assert.strictEqual(
                target.querySelector(`.o_field_widget[name="start_date"] input`).value,
                "12/13/2016",
                "should display the date"
            );

            await click(target, `.modal .o_field_boolean[name="allday"] input`);
            assert.strictEqual(
                target.querySelector(`.o_field_widget[name="start"] input`).value,
                "12/13/2016 02:00:00",
                "should display the datetime from the date with the timezone"
            );

            // use datepicker to enter a date: 12/13/2016 08:00:00
            await click(target, `.o_field_widget[name="start"] .o_datepicker .o_datepicker_input`);
            await click(
                document.body,
                `.bootstrap-datetimepicker-widget .picker-switch a[data-action="togglePicker"]`
            );
            await click(
                document.body,
                `.bootstrap-datetimepicker-widget .timepicker .timepicker-hour`
            );
            await click(
                document.body.querySelectorAll(
                    `.bootstrap-datetimepicker-widget .timepicker-hours td.hour`
                )[8]
            );
            await click(
                document.body,
                `.bootstrap-datetimepicker-widget .picker-switch a[data-action="close"]`
            );

            // use datepicker to enter a date: 12/13/2016 10:00:00
            await click(target, `.o_field_widget[name="stop"] .o_datepicker .o_datepicker_input`);
            await click(
                document.body,
                `.bootstrap-datetimepicker-widget .picker-switch a[data-action="togglePicker"]`
            );
            await click(
                document.body,
                `.bootstrap-datetimepicker-widget .timepicker .timepicker-hour`
            );
            await click(
                document.body.querySelectorAll(
                    `.bootstrap-datetimepicker-widget .timepicker-hours td.hour`
                )[10]
            );
            await click(
                document.body,
                `.bootstrap-datetimepicker-widget .picker-switch a[data-action="close"]`
            );

            await click(target, ".modal-footer button.btn-primary:not(.d-none)");
            assert.strictEqual(
                findEvent(target, 1).querySelector(".o_event_title").textContent,
                "new event",
                "should display the new event with title"
            );

            // Move this event to another day
            expectedEvent = {
                allday: false,
                start: "2016-12-12 06:00:00",
                stop: "2016-12-12 08:00:00",
            };
            await moveEventToTime(target, 1, "2016-12-12 08:00:00");

            // Move to "All day"
            expectedEvent = {
                allday: true,
                start: "2016-12-12",
                stop: "2016-12-12",
            };
            await moveEventToAllDaySlot(target, 1, "2016-12-12");
        }
    );

    QUnit.test(`check calendar week column timeformat`, async (assert) => {
        patchWithCleanup(localization, { timeFormat: "hh:mm:ss" });

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" />
            `,
        });

        assert.strictEqual(
            findTimeRow(target, "08:00:00").textContent,
            "8am",
            "calendar should show according to timeformat"
        );
        assert.strictEqual(
            findTimeRow(target, "23:00:00").textContent,
            "11pm",
            "event time format should 12 hour"
        );
    });

    QUnit.test(`create all day event in week mode`, async (assert) => {
        assert.expect(3);
        patchTimeZone(120);
        serverData.models.event.records = [];

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" mode="week" event_open_popup="1">
                    <field name="name" />
                </calendar>
            `,
            mockRPC(route, { args, method }) {
                if (method === "create") {
                    assert.deepEqual(args[0], {
                        name: "new event",
                        start: "2016-12-14",
                        stop: "2016-12-15",
                        allday: true,
                    });
                }
            },
        });

        await selectAllDayRange(target, "2016-12-14", "2016-12-15");
        await editInput(target, ".o-calendar-quick-create--input", "new event");
        await click(target, ".o-calendar-quick-create--create-btn");

        const event = findEvent(target, 1);
        assert.strictEqual(
            event.textContent.replace(/[\s\n\r]+/g, ""),
            "newevent",
            "should display the new event with time and title"
        );
        assert.hasAttrValue(event.parentElement, "colspan", "2", "should appear over two days.");
    });

    QUnit.test("create all day event in month mode: utc-11", async (assert) => {
        assert.expect(3);
        patchTimeZone(-660);
        serverData.models.event.records = [];

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" mode="month" event_open_popup="1">
                    <field name="name" />
                </calendar>
            `,
            mockRPC(route, { args, method }) {
                if (method === "create") {
                    assert.deepEqual(args[0], {
                        name: "new event",
                        start: "2016-12-14",
                        stop: "2016-12-14",
                        allday: true,
                    });
                }
            },
        });

        await clickDate(target, "2016-12-14");
        await editInput(target, ".o-calendar-quick-create--input", "new event");
        await click(target, ".o-calendar-quick-create--create-btn");

        const event = findEvent(target, 1);
        assert.strictEqual(
            event.textContent.replace(/[\s\n\r]+/g, ""),
            "newevent",
            "should display the new event with time and title"
        );

        const evBox = event.getBoundingClientRect();
        const dateCell = target.querySelector(`[data-date="2016-12-14"]`);
        const dtBox = dateCell.getBoundingClientRect();
        assert.ok(
            evBox.left >= dtBox.left &&
                evBox.right <= dtBox.right &&
                evBox.top >= dtBox.top &&
                evBox.bottom <= dtBox.bottom,
            "event should be inside the proper date cell"
        );
    });

    QUnit.test("create all day event in year mode: utc-11", async (assert) => {
        assert.expect(2);
        patchTimeZone(-660);
        serverData.models.event.records = [];

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" mode="year" event_open_popup="1">
                    <field name="name" />
                </calendar>
            `,
            mockRPC(route, { args, method }) {
                if (method === "create") {
                    assert.deepEqual(args[0], {
                        name: "new event",
                        start: "2016-12-14",
                        stop: "2016-12-14",
                        allday: true,
                    });
                }
            },
        });

        await clickDate(target, "2016-12-14");
        await editInput(target, ".o-calendar-quick-create--input", "new event");
        await click(target, ".o-calendar-quick-create--create-btn");

        const event = findEvent(target, 1);
        const evBox = event.getBoundingClientRect();
        const dateCell = target.querySelector(`[data-date="2016-12-14"]`);
        const dtBox = dateCell.getBoundingClientRect();
        assert.ok(
            evBox.left >= dtBox.left &&
                evBox.right <= dtBox.right &&
                evBox.top >= dtBox.top &&
                evBox.bottom <= dtBox.bottom,
            "event should be inside the proper date cell"
        );
    });

    QUnit.test(`create event with default context (no quickCreate)`, async (assert) => {
        assert.expect(3);

        patchTimeZone(120);
        serverData.models.event.records = [];

        serviceRegistry.add(
            "action",
            {
                ...actionService,
                start() {
                    const result = actionService.start(...arguments);
                    const doAction = result.doAction;
                    result.doAction = (request) => {
                        assert.step("doAction");
                        assert.deepEqual(
                            request.context,
                            {
                                default_name: "New",
                                default_start: "2016-12-14",
                                default_stop: "2016-12-15",
                                default_allday: true,
                                lang: "en",
                                tz: "taht",
                                uid: 7,
                            },
                            "should send the correct data to create events"
                        );
                        return doAction(request);
                    };
                    return result;
                },
            },
            { force: true }
        );

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" mode="week" all_day="allday" quick_add="0" />
            `,
            context: {
                default_name: "New",
            },
        });

        await selectAllDayRange(target, "2016-12-14", "2016-12-15");
        assert.verifySteps(["doAction"]);
    });

    QUnit.test(`create event with default title in context (with quickCreate)`, async (assert) => {
        assert.expect(1);

        serverData.models.event.records = [];

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" mode="week" all_day="allday" />
            `,
            context: {
                default_name: "Example Title",
            },
        });

        await selectAllDayRange(target, "2016-12-14", "2016-12-15");
        const input = target.querySelector(".o-calendar-quick-create--input");
        assert.strictEqual(input.value, "Example Title");
    });

    QUnit.test(`create all day event in week mode (no quickCreate)`, async (assert) => {
        assert.expect(1);

        patchTimeZone(120);
        serverData.models.event.records = [];

        serviceRegistry.add(
            "action",
            {
                ...actionService,
                start() {
                    const result = actionService.start(...arguments);
                    const doAction = result.doAction;
                    result.doAction = (request) => {
                        assert.deepEqual(
                            request.context,
                            {
                                default_start: "2016-12-14",
                                default_stop: "2016-12-15",
                                default_allday: true,
                                lang: "en",
                                tz: "taht",
                                uid: 7,
                            },
                            "should send the correct data to create events"
                        );
                        return doAction(request);
                    };
                    return result;
                },
            },
            { force: true }
        );

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" mode="week" quick_add="0" />
            `,
        });

        await selectAllDayRange(target, "2016-12-14", "2016-12-15");
    });

    QUnit.test(`create event in month mode`, async (assert) => {
        assert.expect(3);

        patchTimeZone(120);
        serverData.models.event.records = [];

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" mode="month" event_open_popup="1">
                    <field name="name" />
                </calendar>
            `,
            mockRPC(route, { args, method }) {
                if (method === "create") {
                    assert.deepEqual(
                        args[0],
                        {
                            name: "new event",
                            start: "2016-12-14 05:00:00",
                            stop: "2016-12-15 17:00:00",
                        },
                        "should send the correct data to create events"
                    );
                }
            },
        });

        await selectDateRange(target, "2016-12-14", "2016-12-15");
        await editInput(target, ".o-calendar-quick-create--input", "new event");
        await click(target, ".o-calendar-quick-create--create-btn");

        const event = findEvent(target, 1);
        assert.strictEqual(
            event.textContent.replace(/[\s\n\r]+/g, ""),
            "newevent",
            "should display the new event with time and title"
        );
        assert.hasAttrValue(event.parentElement, "colspan", "2", "should appear over two days.");
    });

    QUnit.test(`use mini calendar`, async (assert) => {
        patchTimeZone(120);

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" mode="week" event_open_popup="1" />
            `,
        });

        assert.containsOnce(target, ".fc-timeGridWeek-view", "should be in week mode");
        assert.containsN(
            target,
            ".fc-event",
            9,
            "should display 9 events on the week (4 event + 5 days event)"
        );

        await pickDate(target, "2016-12-19");
        // Clicking on a day in another week should switch to the other week view
        assert.containsOnce(target, ".fc-timeGridWeek-view", "should be in week mode");
        assert.containsN(
            target,
            ".fc-event",
            4,
            "should display 4 events on the week (1 event + 3 days event)"
        );

        // Clicking on a day in the same week should switch to that particular day view
        await pickDate(target, "2016-12-18");
        assert.containsOnce(target, ".fc-timeGridDay-view", "should be in day mode");
        assert.containsN(target, ".fc-event", 2, "should display 2 events on the day");

        // Clicking on the same day should toggle between day, month and week views
        await pickDate(target, "2016-12-18");
        assert.containsOnce(target, ".fc-dayGridMonth-view", "should be in month mode");
        assert.containsN(
            target,
            ".fc-event",
            7,
            "should display 7 events on the month (event 5 is on multiple weeks and generates to .fc-event)"
        );

        await pickDate(target, "2016-12-18");
        assert.containsOnce(target, ".fc-timeGridWeek-view", "should be in week mode");
        assert.containsN(
            target,
            ".fc-event",
            4,
            "should display 4 events on the week (1 event + 3 days event)"
        );

        await pickDate(target, "2016-12-18");
        assert.containsOnce(target, ".fc-timeGridDay-view", "should be in day mode");
        assert.containsN(target, ".fc-event", 2, "should display 2 events on the day");
    });

    QUnit.test(`rendering, with many2many`, async (assert) => {
        serverData.models.event.fields.partner_ids.type = "many2many";
        serverData.models.event.records[0].partner_ids = [1, 2, 3, 4, 5];
        serverData.models.partner.records.push({ id: 5, display_name: "partner 5", image: "EEE" });

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" event_open_popup="1">
                    <field name="partner_ids" widget="many2many_tags_avatar" avatar_field="image" write_model="filter_partner" write_field="partner_id" />
                </calendar>
            `,
        });

        assert.containsN(
            target,
            ".o_calendar_filter_item .o_cw_filter_avatar",
            3,
            "should have 3 avatars in the side bar"
        );

        await toggleFilter(target, "partner_ids", "all");

        // Event 1
        await clickEvent(target, 4);
        assert.containsOnce(target, ".o_cw_popover", "should open a popover clicking on event");
        assert.containsOnce(target, ".o_cw_popover img", "should have 1 avatar");

        // Event 2
        await clickEvent(target, 1);
        assert.containsOnce(target, ".o_cw_popover", "should open a popover clicking on event");
        assert.containsN(target, ".o_cw_popover img", 5, "should have 5 avatar");
    });

    QUnit.test(`open form view`, async (assert) => {
        assert.expect(2);

        let expectedRequest;
        serviceRegistry.add(
            "action",
            {
                ...actionService,
                start() {
                    const result = actionService.start(...arguments);
                    const doAction = result.doAction;
                    result.doAction = (request) => {
                        assert.deepEqual(request, expectedRequest);
                        return doAction(request);
                    };
                    return result;
                },
            },
            { force: true }
        );

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" mode="month" />
            `,
            mockRPC(route, { method }) {
                if (method === "get_formview_id") {
                    return Promise.resolve("A view");
                }
            },
        });

        // click on an existing event to open the form view
        expectedRequest = {
            type: "ir.actions.act_window",
            res_id: 4,
            res_model: "event",
            views: [["A view", "form"]],
            target: "current",
            context: {},
        };
        await clickEvent(target, 4);
        await click(target, ".o_cw_popover .o_cw_popover_edit");

        // create a new event and edit it
        await clickDate(target, "2016-12-27");
        await editInput(target, ".o-calendar-quick-create--input", "coucou");

        expectedRequest = {
            type: "ir.actions.act_window",
            res_model: "event",
            views: [[false, "form"]],
            target: "current",
            context: {
                default_name: "coucou",
                default_start: "2016-12-27",
                default_stop: "2016-12-27",
                default_allday: true,
                lang: "en",
                tz: "taht",
                uid: 7,
            },
        };
        await click(target, ".o-calendar-quick-create--edit-btn");
    });

    QUnit.test(`create and edit event in month mode (all_day: false)`, async (assert) => {
        assert.expect(1);
        patchTimeZone(-240);

        serviceRegistry.add(
            "action",
            {
                ...actionService,
                start() {
                    const result = actionService.start(...arguments);
                    const doAction = result.doAction;
                    result.doAction = (request) => {
                        assert.deepEqual(
                            request,
                            {
                                type: "ir.actions.act_window",
                                res_model: "event",
                                views: [[false, "form"]],
                                target: "current",
                                context: {
                                    default_name: "coucou",
                                    default_start: "2016-12-27 11:00:00", // 7:00 + 4h
                                    default_stop: "2016-12-27 23:00:00", // 19:00 + 4h
                                    default_allday: true,
                                    lang: "en",
                                    tz: "taht",
                                    uid: 7,
                                },
                            },
                            "should open the form view with the context default values"
                        );
                        return doAction(request);
                    };
                    return result;
                },
            },
            { force: true }
        );

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" mode="month" />
            `,
        });

        // create a new event and edit it
        await clickDate(target, "2016-12-27");
        await editInput(target, ".o-calendar-quick-create--input", "coucou");
        await click(target, ".o-calendar-quick-create--edit-btn");
    });

    QUnit.test(`show start time of single day event for month mode`, async (assert) => {
        patchTimeZone(-240);

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" mode="month" />
            `,
        });

        assert.strictEqual(
            findEvent(target, 2).querySelector(".fc-content .fc-time").textContent,
            "06:55",
            "should have a correct time 06:55 AM in month mode"
        );
        assert.containsNone(
            findEvent(target, 4),
            ".fc-content .fc-time",
            "should not display a time for all day event"
        );
        assert.containsNone(
            findEvent(target, 5),
            ".fc-content .fc-time",
            "should not display a time for multiple days event"
        );

        // switch to week mode
        await changeScale(target, "week");
        assert.containsOnce(
            findEvent(target, 2),
            ".fc-content .fc-time",
            "should show time in week mode"
        );

        // switch to day mode
        await changeScale(target, "day");
        assert.containsOnce(
            findEvent(target, 2),
            ".fc-content .fc-time",
            "should show time in day mode"
        );
    });

    QUnit.test(`start time should not shown for date type field`, async (assert) => {
        patchTimeZone(-240);

        serverData.models.event.fields.start.type = "date";

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" mode="month" />
            `,
        });

        assert.containsNone(
            findEvent(target, 2),
            ".fc-content .fc-time",
            "should not show time for date type field"
        );
    });

    QUnit.test(`start time should not shown in month mode if hide_time is true`, async (assert) => {
        patchTimeZone(-240);

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" mode="month" hide_time="1" />
            `,
        });

        assert.containsNone(
            findEvent(target, 2),
            ".fc-content .fc-time",
            "should not show time for hide_time attribute"
        );
    });

    QUnit.test(`readonly date_start field`, async (assert) => {
        assert.expect(3);

        serverData.models.event.fields.start.readonly = true;

        let expectedRequest;
        serviceRegistry.add(
            "action",
            {
                ...actionService,
                start() {
                    const result = actionService.start(...arguments);
                    const doAction = result.doAction;
                    result.doAction = (request) => {
                        assert.deepEqual(request, expectedRequest);
                        return doAction(request);
                    };
                    return result;
                },
            },
            { force: true }
        );

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" mode="month" />
            `,
            mockRPC(route, { method }) {
                if (method === "get_formview_id") {
                    return Promise.resolve(false);
                }
            },
        });

        assert.containsNone(target, ".fc-resizer", "should not have resize button");

        expectedRequest = {
            type: "ir.actions.act_window",
            res_id: 4,
            res_model: "event",
            views: [[false, "form"]],
            target: "current",
            context: {},
        };
        await clickEvent(target, 4);
        await click(target, ".o_cw_popover .o_cw_popover_edit");

        // create a new event and edit it
        await clickDate(target, "2016-12-27");
        await editInput(target, ".o-calendar-quick-create--input", "coucou");

        expectedRequest = {
            type: "ir.actions.act_window",
            res_model: "event",
            views: [[false, "form"]],
            target: "current",
            context: {
                default_name: "coucou",
                default_start: "2016-12-27",
                default_stop: "2016-12-27",
                default_allday: true,
                lang: "en",
                tz: "taht",
                uid: 7,
            },
        };

        await click(target, ".o-calendar-quick-create--edit-btn");
    });

    QUnit.test(`check filters with filter_field specified`, async (assert) => {
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" mode="week">
                    <field name="partner_ids" write_model="filter_partner" write_field="partner_id" filter_field="partner_checked" />
                </calendar>
            `,
        });

        assert.containsOnce(
            findFilterPanelFilter(target, "partner_ids", 2),
            "input:checked",
            "checkbox should be checked"
        );

        await toggleFilter(target, "partner_ids", 2);
        assert.containsNone(
            findFilterPanelFilter(target, "partner_ids", 2),
            "input:checked",
            "checkbox should not be checked"
        );
        assert.strictEqual(
            serverData.models.filter_partner.records.find((r) => r.id === 2).partner_checked,
            false,
            "the status of this filter should now be false"
        );

        await changeScale(target, "week"); // trick to reload the entire view
        assert.containsNone(
            findFilterPanelFilter(target, "partner_ids", 2),
            "input:checked",
            "checkbox should not be checked after the reload"
        );
        assert.strictEqual(
            serverData.models.filter_partner.records.find((r) => r.id === 2).partner_checked,
            false,
            "the status of this filter should still be false after the reload"
        );
    });

    QUnit.test('"all" filter', async (assert) => {
        assert.expect(8);

        let requestCount = 0;
        const interval = [
            ["start", "<=", "2016-12-17 22:59:59"],
            ["stop", ">=", "2016-12-10 23:00:00"],
        ];
        const expectedDomains = [
            interval.concat([["partner_ids", "in", []]]),
            interval.concat([["partner_ids", "in", [1]]]),
            interval.concat([["partner_ids", "in", [1, 2]]]),
            interval,
        ];

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar event_open_popup="1" date_start="start" date_stop="stop" all_day="allday" mode="week" attendee="partner_ids" color="partner_id">
                    <filter name="user_id" avatar_field="image" />
                    <field name="partner_ids" write_model="filter_partner" write_field="partner_id" />
                </calendar>
            `,
            mockRPC(route, { kwargs, method, model }) {
                if (method === "search_read" && model === "event") {
                    assert.deepEqual(kwargs.domain, expectedDomains[requestCount]);
                    requestCount++;
                }
            },
        });

        // By default, no user is selected
        assert.containsNone(target, ".fc-event", "should not display any event on the week");

        await toggleFilter(target, "partner_ids", 1);
        assert.containsN(target, ".fc-event", 4, "should display 4 events on the week");

        await toggleFilter(target, "partner_ids", 2);
        assert.containsN(target, ".fc-event", 9, "should display 9 events on the week");

        // Click on the "all" filter to reload all events
        await toggleFilter(target, "partner_ids", "all");
        assert.containsN(target, ".fc-event", 9, "should display 9 events on the week");
    });

    QUnit.test("dynamic filters with selection fields", async (assert) => {
        serverData.models.event.fields.selection = {
            name: "selection",
            string: "Ambiance",
            type: "selection",
            selection: [
                ["desert", "Desert"],
                ["forest", "Forest"],
            ],
        };

        serverData.models.event.records[0].selection = "forest";
        serverData.models.event.records[1].selection = "desert";

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: /* xml */ `
                <calendar date_start="start" date_stop="stop">
                    <field name="selection" filters="1" />
                </calendar>
            `,
        });

        const section = findFilterPanelSection(target, "selection");
        assert.deepEqual(section.querySelector(".o_cw_filter_label").textContent, "Ambiance");
        assert.deepEqual(
            [...section.querySelectorAll(".o_calendar_filter_item")].map((el) =>
                el.textContent.trim()
            ),
            ["Forest", "Desert", "Undefined"]
        );
    });

    QUnit.test("Colors: cycling through available colors", async (assert) => {
        serverData.models.filter_partner.records = Array.from({ length: 56 }, (_, i) => ({
            id: i + 1,
            user_id: uid,
            partner_id: i + 1,
            partner_checked: true,
        }));
        serverData.models.partner.records = Array.from({ length: 56 }, (_, i) => ({
            id: i + 1,
            display_name: `partner ${i + 1}`,
        }));
        serverData.models.event.records = Array.from({ length: 56 }, (_, i) => ({
            id: i + 1,
            user_id: uid,
            partner_id: i + 1,
            name: `event ${i + 1}`,
            start: `2016-12-12 0${i % 10}:00:00`,
            stop: `2016-12-12 0${i % 10}:00:00`,
            partner_ids: [i + 1],
        }));
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" mode="day" color="partner_ids">
                    <field name="partner_ids" write_model="filter_partner" write_field="partner_id" filter_field="partner_checked"  />
                </calendar>
            `,
        });
        assert.containsN(target, ".fc-event", 56);
        assert.hasClass(findEvent(target, 1), "o_calendar_color_1");
        assert.hasClass(findEvent(target, 55), "o_calendar_color_55");
        assert.hasClass(findEvent(target, 56), "o_calendar_color_1");

        const partnerSection = findFilterPanelSection(target, "partner_ids");
        assert.containsOnce(partnerSection, ".o_calendar_filter_item[data-value='all']");
        assert.containsN(partnerSection, ".o_calendar_filter_item:not([data-value='all'])", 56);
        assert.hasClass(
            partnerSection.querySelector(".o_calendar_filter_item[data-value='1']"),
            "o_cw_filter_color_1"
        );
        assert.hasClass(
            partnerSection.querySelector(".o_calendar_filter_item[data-value='55']"),
            "o_cw_filter_color_55"
        );
        assert.hasClass(
            partnerSection.querySelector(".o_calendar_filter_item[data-value='56']"),
            "o_cw_filter_color_1"
        );
    });

    QUnit.test("Colors: use available colors when attr is not number", async (assert) => {
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" color="name">
                    <field name="partner_ids" write_model="filter_partner" write_field="partner_id" filter_field="partner_checked"  />
                </calendar>
            `,
        });
        const colorClass = Array.from(findEvent(target, 1).classList).find((className) =>
            className.startsWith("o_calendar_color_")
        );
        assert.notOk(isNaN(Number(colorClass.split("_").at(-1))));
        await clickEvent(target, 1);
        assert.hasClass(target.querySelector(".o_cw_popover"), colorClass);
    });

    QUnit.test(`Add filters and specific color`, async (assert) => {
        serverData.models.event_type.records.push({
            id: 4,
            display_name: "Event Type no color",
            color_event_type: 0,
        });
        serverData.models.event.records.push(
            {
                id: 8,
                user_id: 4,
                partner_id: 1,
                name: "event 8",
                start: "2016-12-11 09:00:00",
                stop: "2016-12-11 10:00:00",
                allday: false,
                partner_ids: [1, 2, 3],
                event_type_id: 3,
                color_event: 4, // related is not managed by the mock server
            },
            {
                id: 9,
                user_id: 4,
                partner_id: 1,
                name: "event 9",
                start: "2016-12-11 19:00:00",
                stop: "2016-12-11 20:00:00",
                allday: false,
                partner_ids: [1, 2, 3],
                event_type_id: 1,
                color_event: 1, // related is not managed by the mock server
            },
            {
                id: 10,
                user_id: 4,
                partner_id: 1,
                name: "event 10",
                start: "2016-12-11 12:00:00",
                stop: "2016-12-11 13:00:00",
                allday: false,
                partner_ids: [1, 2, 3],
                event_type_id: 4,
                color_event: 0, // related is not managed by the mock server
            }
        );

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" mode="week" color="color_event" event_open_popup="1">
                    <field name="partner_ids" write_model="filter_partner" write_field="partner_id" />
                    <field name="event_type_id" filters="1" color="color_event_type" />
                </calendar>
            `,
            mockRPC(route, { method, model, kwargs }) {
                if (route.startsWith("/web/static/lib/fullcalendar")) {
                    return;
                }
                if (kwargs.fields) {
                    assert.step(`${method} (${model}) [${(kwargs.fields || []).join(", ")}]`);
                } else {
                    assert.step(`${method} (${model})`);
                }
            },
        });
        assert.verifySteps([
            "get_views (event)",
            "check_access_rights (event)",
            "search_read (filter_partner) [partner_id]",
            "search_read (event) [display_name, start, stop, allday, color_event, partner_ids, event_type_id]",
        ]);

        // By default no filter is selected. We check before continuing.
        await toggleFilter(target, "partner_ids", 1);
        assert.verifySteps([
            "search_read (filter_partner) [partner_id]",
            "search_read (event) [display_name, start, stop, allday, color_event, partner_ids, event_type_id]",
        ]);
        await toggleFilter(target, "partner_ids", 2);
        assert.verifySteps([
            "search_read (filter_partner) [partner_id]",
            "search_read (event) [display_name, start, stop, allday, color_event, partner_ids, event_type_id]",
        ]);

        assert.containsN(target, ".o_calendar_filter", 2, "should display 2 sections");

        const typeSection = findFilterPanelSection(target, "event_type_id");
        assert.strictEqual(
            typeSection.querySelector(".o_cw_filter_label").textContent,
            "Event Type",
            "should display 'Event Type' filter"
        );
        assert.hasClass(findEvent(target, 8), "o_calendar_color_4");
        assert.hasClass(findEvent(target, 9), "o_calendar_color_1");
        assert.hasClass(findEvent(target, 10), "o_calendar_color_0");
        assert.containsN(
            typeSection,
            ".o_calendar_filter_item",
            4,
            "should display 4 filter items for 'Event Type'"
        );
        assert.containsOnce(
            typeSection,
            `.o_calendar_filter_item[data-value="3"].o_cw_filter_color_4`,
            "Filter for event type 3 must have the color 4"
        );
        assert.containsOnce(
            target,
            `.fc-event[data-event-id="8"].o_calendar_color_4`,
            "Event of event type 3 must have the color 4"
        );
        assert.containsOnce(
            target,
            `.fc-event[data-event-id="10"].o_calendar_color_0`,
            "The first color is used when none is provided (default int field value being 0)"
        );
    });

    QUnit.test(`Colors: dynamic filters without any color attr`, async (assert) => {
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop">
                    <field name="user_id" filters="1" invisible="1"/>
                </calendar>
            `,
        });
        assert.hasClass(findEvent(target, 1), "o_calendar_color_0");
        assert.hasClass(findEvent(target, 2), "o_calendar_color_0");
        assert.hasClass(findEvent(target, 3), "o_calendar_color_0");
        assert.hasClass(findEvent(target, 4), "o_calendar_color_0");
        assert.hasClass(findEvent(target, 5), "o_calendar_color_0");
        assert.containsOnce(target, ".o_calendar_filter[data-name=user_id]");
        assert.containsNone(
            findFilterPanelSection(target, "user_id"),
            "[class*='o_cw_filter_color_']"
        );
    });

    QUnit.test(`Colors: dynamic filters without color attr (related)`, async (assert) => {
        serverData.models.event.records = [
            {
                id: 8,
                user_id: 4,
                partner_id: 1,
                name: "event 8",
                start: "2016-12-11 09:00:00",
                stop: "2016-12-11 10:00:00",
                allday: false,
                partner_ids: [1, 2, 3],
                event_type_id: 3,
                color_event: 4, // related is not managed by the mock server
            },
            {
                id: 9,
                user_id: 4,
                partner_id: 1,
                name: "event 9",
                start: "2016-12-11 19:00:00",
                stop: "2016-12-11 20:00:00",
                allday: false,
                partner_ids: [1, 2, 3],
                event_type_id: 1,
                color_event: 1, // related is not managed by the mock server
            },
            {
                id: 10,
                user_id: 4,
                partner_id: 1,
                name: "event 10",
                start: "2016-12-11 12:00:00",
                stop: "2016-12-11 13:00:00",
                allday: false,
                partner_ids: [1, 2, 3],
                event_type_id: 2,
                color_event: 2, // related is not managed by the mock server
            },
        ];
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" color="color_event">
                    <field name="partner_ids" write_model="filter_partner" write_field="partner_id" />
                    <field name="event_type_id" filters="1" />
                </calendar>
            `,
            mockRPC(route, { method, model }) {
                if (method === "search_read" && model === "event_type") {
                    throw new Error("should not fetch event_type filter colors");
                }
            },
        });
        await toggleSectionFilter(target, "partner_ids");
        assert.hasClass(findEvent(target, 8), "o_calendar_color_4");
        assert.hasClass(findEvent(target, 9), "o_calendar_color_1");
        assert.hasClass(findEvent(target, 10), "o_calendar_color_2");
        assert.containsNone(
            findFilterPanelSection(target, "partner_ids"),
            "[class*='o_cw_filter_color_']"
        );
        assert.containsN(
            findFilterPanelSection(target, "event_type_id"),
            "[class*='o_cw_filter_color_']",
            3
        );
    });

    QUnit.test(`Colors: dynamic filters without color attr (direct)`, async (assert) => {
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" color="user_id">
                    <field name="partner_id" avatar_field="image"/>
                    <field name="user_id" filters="1" invisible="1"/>
                </calendar>
            `,
            mockRPC(route, { method, model }) {
                if (method === "search_read" && model === "event_type") {
                    throw new Error("should not fetch event_type filter colors");
                }
            },
        });
        assert.hasClass(findEvent(target, 1), "o_calendar_color_-1"); // uid = -1 ...
        assert.hasClass(findEvent(target, 2), "o_calendar_color_-1"); // uid = -1 ...
        assert.hasClass(findEvent(target, 3), "o_calendar_color_4");
        assert.hasClass(findEvent(target, 4), "o_calendar_color_-1"); // uid = -1 ...
        assert.hasClass(findEvent(target, 5), "o_calendar_color_4");
        assert.containsNone(
            findFilterPanelSection(target, "partner_id"),
            "[class*='o_cw_filter_color_']"
        );
        assert.containsN(
            findFilterPanelSection(target, "user_id"),
            "[class*='o_cw_filter_color_']",
            2
        );
    });

    QUnit.test(`makeFilterUser: color for current user`, async (assert) => {
        serverData.models["res.partner"] = {
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
        };
        serverData.models.event.fields.partner_id.relation = "res.partner";
        serverData.models.event.fields.partner_ids.relation = "res.partner";
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" color="partner_ids">
                    <field name="partner_ids" write_model="filter_partner" write_field="partner_id" />
                </calendar>
            `,
        });

        const partnerSection = findFilterPanelSection(target, "partner_ids");
        assert.containsN(partnerSection, "[class*='o_cw_filter_color_']", 3);
        assert.strictEqual(
            partnerSection.querySelector(".o_cw_filter_label").textContent,
            "attendees"
        );
        assert.containsN(partnerSection, ".o_calendar_filter_item", 4);
        assert.strictEqual(
            partnerSection.querySelector(".o_calendar_filter_item[data-value='7']").textContent,
            "Mitchell"
        );
        assert.containsOnce(
            partnerSection,
            `.o_calendar_filter_item[data-value="7"].o_cw_filter_color_7`
        );
        assert.containsOnce(
            partnerSection,
            `.o_calendar_filter_item[data-value="2"].o_cw_filter_color_2`
        );
        assert.containsOnce(
            partnerSection,
            `.o_calendar_filter_item[data-value="1"].o_cw_filter_color_1`
        );
        assert.strictEqual(
            partnerSection.querySelector(".o_calendar_filter_item[data-value='all']").textContent,
            "Everybody's calendars"
        );
    });

    QUnit.test(`Colors: dynamic filters with same color as events`, async (assert) => {
        serverData.models.event.records = [
            {
                id: 8,
                user_id: 4,
                partner_id: 1,
                name: "event 8",
                start: "2016-12-11 09:00:00",
                stop: "2016-12-11 10:00:00",
                allday: false,
                partner_ids: [1, 2, 3],
                event_type_id: 3,
                color_event: 4, // related is not managed by the mock server
            },
            {
                id: 9,
                user_id: 4,
                partner_id: 1,
                name: "event 9",
                start: "2016-12-11 19:00:00",
                stop: "2016-12-11 20:00:00",
                allday: false,
                partner_ids: [1, 2, 3],
                event_type_id: 1,
                color_event: 1, // related is not managed by the mock server
            },
            {
                id: 10,
                user_id: 4,
                partner_id: 1,
                name: "event 10",
                start: "2016-12-11 12:00:00",
                stop: "2016-12-11 13:00:00",
                allday: false,
                partner_ids: [1, 2, 3],
                event_type_id: 2,
                color_event: 2, // related is not managed by the mock server
            },
        ];
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" color="color_event">
                    <field name="partner_ids" write_model="filter_partner" write_field="partner_id" />
                    <field name="event_type_id" filters="1" color="color_event_type" />
                </calendar>
            `,
            mockRPC(route, { method, model }) {
                if (method === "search_read" && model === "event_type") {
                    throw new Error("should not fetch event_type filter colors");
                }
            },
        });
        await toggleSectionFilter(target, "partner_ids");
        assert.hasClass(findEvent(target, 8), "o_calendar_color_4");
        assert.hasClass(findEvent(target, 9), "o_calendar_color_1");
        assert.hasClass(findEvent(target, 10), "o_calendar_color_2");
        assert.containsN(
            findFilterPanelSection(target, "event_type_id"),
            "[class*='o_cw_filter_color_']",
            3
        );
        assert.hasClass(findFilterPanelFilter(target, "event_type_id", 1), "o_cw_filter_color_1");
        assert.hasClass(findFilterPanelFilter(target, "event_type_id", 2), "o_cw_filter_color_2");
        assert.hasClass(findFilterPanelFilter(target, "event_type_id", 3), "o_cw_filter_color_4");
    });

    QUnit.test(`Colors: dynamic filters with another color source`, async (assert) => {
        serverData.models.event.records = [
            {
                id: 8,
                user_id: 4,
                partner_id: 3,
                name: "event 8",
                start: "2016-12-11 09:00:00",
                stop: "2016-12-11 10:00:00",
                allday: false,
                partner_ids: [1, 2, 3],
                event_type_id: 3,
                color_event: 4, // related is not managed by the mock server
            },
            {
                id: 9,
                user_id: 4,
                partner_id: 3,
                name: "event 9",
                start: "2016-12-11 19:00:00",
                stop: "2016-12-11 20:00:00",
                allday: false,
                partner_ids: [1, 2, 3],
                event_type_id: 1,
                color_event: 1, // related is not managed by the mock server
            },
            {
                id: 10,
                user_id: 4,
                partner_id: 3,
                name: "event 10",
                start: "2016-12-11 12:00:00",
                stop: "2016-12-11 13:00:00",
                allday: false,
                partner_ids: [1, 2, 3],
                event_type_id: 2,
                color_event: 2, // related is not managed by the mock server
            },
        ];
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" color="partner_id">
                    <field name="partner_ids" write_model="filter_partner" write_field="partner_id" />
                    <field name="event_type_id" filters="1" color="color_event_type" />
                </calendar>
            `,
            mockRPC(route, { method, model }) {
                if (method === "search_read" && model === "event_type") {
                    assert.step("fetching event_type filter colors");
                }
            },
        });
        assert.verifySteps([]);
        await toggleSectionFilter(target, "partner_ids");
        assert.verifySteps(["fetching event_type filter colors"]);
        assert.hasClass(findEvent(target, 8), "o_calendar_color_3");
        assert.hasClass(findEvent(target, 9), "o_calendar_color_3");
        assert.hasClass(findEvent(target, 10), "o_calendar_color_3");
        assert.hasClass(findFilterPanelFilter(target, "event_type_id", 1), "o_cw_filter_color_1");
        assert.hasClass(findFilterPanelFilter(target, "event_type_id", 2), "o_cw_filter_color_2");
        assert.hasClass(findFilterPanelFilter(target, "event_type_id", 3), "o_cw_filter_color_4");
    });

    QUnit.test(`create event with filters`, async (assert) => {
        serverData.models.event.fields.user_id.default = 5;
        serverData.models.event.fields.partner_id.default = 3;
        serverData.models.user.records.push({ id: 5, display_name: "user 5", partner_id: 3 });

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" mode="week" event_open_popup="1" attendee="partner_ids" color="partner_id">
                    <field name="partner_ids" write_model="filter_partner" write_field="partner_id" />
                    <field name="partner_id" filters="1" invisible="1" />
                </calendar>
            `,
        });

        // By default only
        await toggleFilter(target, "partner_ids", 1);
        assert.containsN(target, ".o_calendar_filter_item", 5, "should display 5 filter items");
        assert.containsN(target, ".fc-event", 4, "should display 4 events");

        // quick create a record
        await selectTimeRange(target, "2016-12-15 06:00:00", "2016-12-15 08:00:00");
        await editInput(target, ".o-calendar-quick-create--input", "coucou");
        await click(target, ".o-calendar-quick-create--create-btn");
        assert.containsN(
            target,
            ".o_calendar_filter_item",
            6,
            "should add the missing filter (active)"
        );
        assert.containsN(target, ".fc-event", 5, "should display the created item");

        // change default value for quick create an hide record
        serverData.models.event.fields.user_id.default = 4;
        serverData.models.event.fields.partner_id.default = 4;

        // Disable our filter to create a record without displaying it
        await toggleFilter(target, "partner_id", 4);

        // quick create and other record
        await selectTimeRange(target, "2016-12-13 06:00:00", "2016-12-13 08:00:00");
        await editInput(target, ".o-calendar-quick-create--input", "coucou 2");
        await click(target, ".o-calendar-quick-create--create-btn");
        assert.containsN(target, ".o_calendar_filter_item", 6, "should have the same filters");
        assert.containsN(target, ".fc-event", 4, "should not display the created item");

        await toggleFilter(target, "partner_id", 4);
        await toggleFilter(target, "partner_ids", 2);
        assert.containsN(target, ".fc-event", 11, "should display all records");
    });

    QUnit.test(`create event with filters (no quickCreate)`, async (assert) => {
        serverData.views["event,false,form"] = `
            <form>
                <group>
                    <field name="name" />
                    <field name="start" />
                    <field name="stop" />
                    <field name="user_id" />
                    <field name="partner_id" invisible="1" />
                </group>
            </form>
        `;
        serverData.models.event.fields.user_id.default = 5;
        serverData.models.event.fields.partner_id.default = 3;
        serverData.models.user.records.push({ id: 5, display_name: "user 5", partner_id: 3 });

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" mode="week" event_open_popup="1" attendee="partner_ids" color="partner_id">
                    <filter name="user_id" avatar_field="image" />
                    <field name="partner_ids" write_model="filter_partner" write_field="partner_id" />
                    <field name="partner_id" filters="1" invisible="1" />
                </calendar>
            `,
        });

        // dislay all attendee calendars
        await toggleSectionFilter(target, "partner_ids");
        await toggleFilter(target, "partner_id", 4);
        assert.containsN(target, ".o_calendar_filter_item", 5, "should display 5 filter items");
        assert.containsN(target, ".fc-event", 3, "should display 3 events");

        // quick create a record
        await selectTimeRange(target, "2016-12-15 06:00:00", "2016-12-15 08:00:00");
        await editInput(target, ".o-calendar-quick-create--input", "coucou");
        await click(target, ".o-calendar-quick-create--edit-btn");
        await click(target, ".modal-footer .o_form_button_save");
        assert.containsN(
            target,
            ".o_calendar_filter_item",
            6,
            "should add the missing filter (active)"
        );
        assert.containsN(target, ".fc-event", 4, "should display the created item");
    });

    QUnit.test(`Update event with filters`, async (assert) => {
        const records = serverData.models.user.records;
        records.push({ id: 5, display_name: "user 5", partner_id: 3 });
        serverData.models.event.onchanges = {
            user_id(obj) {
                obj.partner_id = records.find((r) => r.id === obj.user_id).partner_id;
            },
        };
        serverData.views["event,false,form"] = `
            <form>
                <group>
                    <field name="name" />
                    <field name="start" />
                    <field name="stop" />
                    <field name="user_id" />
                    <field name="partner_ids" widget="many2many_tags" />
                    <field name="partner_id" invisible="1" />
                </group>
            </form>
        `;

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" mode="week" event_open_popup="1" attendee="partner_ids" color="partner_id">
                    <filter name="user_id" avatar_field="image" />
                    <field name="partner_ids" write_model="filter_partner" write_field="partner_id" />
                    <field name="partner_id" filters="1" invisible="1" />
                </calendar>
            `,
        });

        // select needed partner filters
        await toggleFilter(target, "partner_ids", 1);
        await toggleFilter(target, "partner_id", 4);
        assert.containsN(target, ".o_calendar_filter_item", 5, "should display 5 filter items");
        assert.containsN(target, ".fc-event", 3, "should display 3 events");

        await clickEvent(target, 2);
        assert.containsOnce(target, ".o_cw_popover", "should open a popover clicking on event");

        await click(target, ".o_cw_popover .o_cw_popover_edit");
        assert.strictEqual(
            target.querySelector(".modal .modal-title").textContent,
            "Open: event 2",
            "dialog should have a valid title"
        );

        await click(target, `.modal .o_field_widget[name="user_id"] input`);
        await click(
            document.body.querySelectorAll(".ui-autocomplete.dropdown-menu .ui-menu-item")[2]
        );
        await click(target, ".modal .o_form_button_save");

        assert.containsN(
            target,
            ".o_calendar_filter_item",
            6,
            "should add the missing filter (active)"
        );
        assert.containsN(target, ".fc-event", 3, "should display the updated item");

        // test the behavior of the 'select all' input checkbox
        assert.containsN(
            target,
            ".o_calendar_filter_item input:checked",
            3,
            "should display 3 active checkbox"
        );
        assert.containsN(
            target,
            ".o_calendar_filter_item input:not(:checked)",
            3,
            "should display 3 inactive checkbox"
        );

        // Click to select all users
        await toggleSectionFilter(target, "partner_id");

        // should contains 4 events
        assert.containsN(target, ".fc-event", 4, "should display the updated events");

        // Should have 4 checked boxes
        assert.containsN(
            target,
            ".o_calendar_filter_item input:checked",
            4, // 3
            "should display 4 active checkbox"
        );

        // unselect all user
        await toggleSectionFilter(target, "partner_id");
        assert.containsN(target, ".fc-event", 0, "should not display any event");
        assert.containsN(
            target,
            ".o_calendar_filter_item input:checked",
            1,
            "should display 1 active checkbox"
        );
    });

    QUnit.test(`change pager with filters`, async (assert) => {
        serverData.models.user.records.push({ id: 5, display_name: "user 5", partner_id: 3 });
        serverData.models.event.records.push(
            {
                id: 8,
                user_id: 5,
                partner_id: 3,
                name: "event 8",
                start: "2016-12-06 04:00:00",
                stop: "2016-12-06 08:00:00",
                allday: false,
                partner_ids: [1, 2, 3],
                type: 1,
            },
            {
                id: 9,
                user_id: uid,
                partner_id: 1,
                name: "event 9",
                start: "2016-12-07 04:00:00",
                stop: "2016-12-07 08:00:00",
                allday: false,
                partner_ids: [1, 2, 3],
                type: 1,
            },
            {
                id: 10,
                user_id: 4,
                partner_id: 4,
                name: "event 10",
                start: "2016-12-08 04:00:00",
                stop: "2016-12-08 08:00:00",
                allday: false,
                partner_ids: [1, 2, 3],
                type: 1,
            }
        );

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" mode="week" event_open_popup="1" attendee="partner_ids" color="partner_id">
                    <filter name="user_id" avatar_field="image" />
                    <field name="partner_ids" write_model="filter_partner" write_field="partner_id" />
                    <field name="partner_id" filters="1" invisible="1" />
                </calendar>
            `,
        });

        // select filter for partner 1, 2 and 4
        await toggleSectionFilter(target, "partner_ids");
        await toggleFilter(target, "partner_id", 4);
        await navigate(target, "prev");
        assert.containsN(target, ".o_calendar_filter_item", 6, "should display 6 filter items");
        assert.containsN(target, ".fc-event", 2, "should display 2 events");
        const events = target.querySelectorAll(".fc-event .o_event_title");
        assert.strictEqual(
            Array.from(events)
                .map((e) => e.textContent)
                .join("")
                .replace(/\s/g, ""),
            "event8event9",
            "should display 2 events"
        );
    });

    QUnit.test(`ensure events are still shown if filters give an empty domain`, async (assert) => {
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" mode="week">
                    <field name="partner_ids" write_model="filter_partner" write_field="partner_id" />
                </calendar>
            `,
        });

        await toggleSectionFilter(target, "partner_ids");
        assert.containsN(target, ".fc-event", 5, "should display 5 events");

        await toggleFilter(target, "partner_ids", "all");
        assert.containsN(target, ".fc-event", 5, "should display 5 events");
    });

    QUnit.test(`events starting at midnight`, async (assert) => {
        patchWithCleanup(localization, defaultLocalization);

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" mode="week" />
            `,
        });

        // Click on Tuesday 12am
        await selectTimeRange(target, "2016-12-13 00:00:00", "2016-12-13 00:30:00");
        assert.containsOnce(
            target,
            ".o-calendar-quick-create",
            "should open the quick create dialog"
        );

        // Creating the event
        await editInput(
            target.querySelector(".modal-body input"),
            null,
            "new event in quick create"
        );
        await click(target, ".o-calendar-quick-create--create-btn");
        assert.strictEqual(
            findEvent(target, 8).querySelector(".o_event_title").textContent,
            "new event in quick create",
            "should display the new record after quick create dialog"
        );
    });

    QUnit.test(`set event as all day when field is date`, async (assert) => {
        assert.expect(2);

        patchTimeZone(-480); // UTC-8
        serverData.models.event.records[0].start_date = "2016-12-14";

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start_date" all_day="allday" mode="week" event_open_popup="1" attendee="partner_ids" color="partner_id">
                    <filter name="user_id" avatar_field="image" />
                    <field name="partner_ids" write_model="filter_partner" write_field="partner_id" />
                </calendar>
            `,
        });

        await toggleFilter(target, "partner_ids", 1);
        assert.containsOnce(
            target,
            ".fc-day-grid .fc-event-container",
            "should be one event in the all day row"
        );
        await clickEvent(target, 1);
        assert.strictEqual(
            target.querySelector(".o_cw_popover .list-group-item").textContent,
            "December 14, 2016 (All day)"
        );
    });

    QUnit.test(
        `set event as all day when field is date (without all_day mapping)`,
        async (assert) => {
            assert.expect(1);

            serverData.models.event.records[0].start_date = "2016-12-14";

            await makeView({
                type: "calendar",
                resModel: "event",
                serverData,
                arch: `
                    <calendar date_start="start_date" mode="week" />
                `,
            });

            assert.containsOnce(
                target,
                ".fc-day-grid .fc-event-container",
                "should be one event in the all day row"
            );
        }
    );

    QUnit.test(`quickcreate avoid double event creation`, async (assert) => {
        assert.expect(1);
        let createCount = 0;
        const def = makeDeferred();

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" mode="month" event_open_popup="1" />
            `,
            async mockRPC(route, { method }, performRPC) {
                if (method === "create") {
                    createCount++;
                    await def;
                    return performRPC(...arguments);
                }
            },
        });

        // create a new event
        await clickDate(target, "2016-12-13");
        await editInput(
            target.querySelector(".modal-body input"),
            null,
            "new event in quick create"
        );

        // Simulate ENTER pressed on Create button (after a TAB)
        await triggerEvent(target.querySelector(".modal-body input"), null, "keyup", {
            key: "Enter",
        });
        await click(target, ".o-calendar-quick-create--create-btn");

        def.resolve();
        await nextTick();
        assert.strictEqual(createCount, 1, "should create only one event");
    });

    QUnit.test(`calendar is configured to have no groupBy menu`, async (assert) => {
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" />
            `,
        });
        assert.containsNone(
            target,
            ".o_control_panel .o_group_by_menu",
            "the control panel has no groupBy menu"
        );
    });

    QUnit.test(`timezone does not affect current day`, async (assert) => {
        assert.expect(2);

        patchTimeZone(2400); // 40 hours timezone
        patchDate(2016, 11, 12, 8, 0, 0); // 2016-12-12 08:00:00

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" />
            `,
        });
        assert.strictEqual(
            findPickedDate(target).textContent,
            "12",
            "should highlight the target day"
        );

        await pickDate(target, "2016-12-11");
        assert.strictEqual(
            findPickedDate(target).textContent,
            "11",
            "should highlight the selected day"
        );
    });

    QUnit.test(`timezone does not affect drag and drop`, async (assert) => {
        assert.expect(10);

        patchTimeZone(-2400); // UTC-40

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" mode="month">
                    <field name="name" />
                    <field name="start" />
                </calendar>
            `,
            mockRPC(route, { method, args }) {
                if (method === "write") {
                    assert.deepEqual(args[0], [6], "event 6 is moved");
                    assert.strictEqual(
                        args[1].start,
                        "2016-11-29 08:00:00",
                        "event moved to 27th nov 16h00 +40 hours timezone"
                    );
                }
            },
        });

        assert.strictEqual(findEvent(target, 1).textContent.replace(/\s/g, ""), "08:00event1");
        await clickEvent(target, 1);
        assert.strictEqual(
            target.querySelector(`.o_field_widget[name="start"]`).textContent,
            "12/09/2016 08:00:00"
        );

        assert.strictEqual(findEvent(target, 6).textContent.replace(/\s/g, ""), "16:00event6");
        await clickEvent(target, 6);
        assert.strictEqual(
            target.querySelector(`.o_field_widget[name="start"]`).textContent,
            "12/16/2016 16:00:00"
        );

        // Move event 6 as on first day of month view (27th november 2016)
        await moveEventToDate(target, 6, "2016-11-27");

        assert.strictEqual(findEvent(target, 6).textContent.replace(/\s/g, ""), "16:00event6");
        await clickEvent(target, 6);
        assert.strictEqual(
            target.querySelector(`.o_field_widget[name="start"]`).textContent,
            "11/27/2016 16:00:00"
        );

        assert.strictEqual(findEvent(target, 1).textContent.replace(/\s/g, ""), "08:00event1");
        await clickEvent(target, 1);
        assert.strictEqual(
            target.querySelector(`.o_field_widget[name="start"]`).textContent,
            "12/09/2016 08:00:00"
        );
    });

    QUnit.test(`timzeone does not affect calendar with date field`, async (assert) => {
        assert.expect(11);

        patchTimeZone(120);

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start_date" mode="month">
                    <field name="name" />
                    <field name="start_date" />
                </calendar>
            `,
            mockRPC(route, { method, args }) {
                if (method === "create") {
                    assert.strictEqual(args[0].start_date, "2016-12-20");
                }
                if (method === "write") {
                    assert.step(args[1].start_date);
                }
            },
        });

        // Create event (on 20 december)
        await clickDate(target, "2016-12-20");
        await editInput(target, ".o-calendar-quick-create--input", "An event");
        await click(target, ".o-calendar-quick-create--create-btn");

        await clickEvent(target, 8);
        assert.containsOnce(target, ".o_cw_popover", "should open a popover clicking on event");
        assert.strictEqual(
            target.querySelector(
                ".o_cw_popover .o_cw_popover_fields_secondary .list-group-item .o_field_date"
            ).textContent,
            "12/20/2016",
            "should have correct start date"
        );

        // Move event to another day (on 27 november)
        await moveEventToDate(target, 8, "2016-11-27");
        assert.verifySteps(["2016-11-27"]);

        await clickEvent(target, 8);
        assert.containsOnce(target, ".o_cw_popover", "should open a popover clicking on event");
        assert.strictEqual(
            target.querySelector(
                ".o_cw_popover .o_cw_popover_fields_secondary .list-group-item .o_field_date"
            ).textContent,
            "11/27/2016",
            "should have correct start date"
        );

        // Move event to last day (on 7 january)
        await moveEventToDate(target, 8, "2017-01-07");
        assert.verifySteps(["2017-01-07"]);

        await clickEvent(target, 8);
        assert.containsOnce(target, ".o_cw_popover", "should open a popover clicking on event");
        assert.strictEqual(
            target.querySelector(
                ".o_cw_popover .o_cw_popover_fields_secondary .list-group-item .o_field_date"
            ).textContent,
            "01/07/2017",
            "should have correct start date"
        );
    });

    QUnit.test(`drag and drop on month mode`, async (assert) => {
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" mode="month" event_open_popup="1" quick_add="0">
                    <field name="name" />
                    <field name="partner_id" />
                </calendar>
            `,
        });

        // Create event (on 20 december)
        await clickDate(target, "2016-12-20");
        await editInput(target, ".modal-body .o_field_widget[name=name] input", "An event");
        await click(target, ".modal .o_form_button_save");

        await moveEventToDate(target, 1, "2016-12-19", { disableDrop: true });
        assert.hasClass(findEvent(target, 1), "dayGridMonth");

        // Move event to another day (on 19 december)
        await moveEventToDate(target, 8, "2016-12-19");
        await clickEvent(target, 8);

        const row = target.querySelectorAll(".o_cw_body .list-group-item")[1];
        assert.strictEqual(
            row.textContent.trim(),
            "07:00 - 19:00 (12 hours)",
            "start and end hours shouldn't have been changed"
        );
    });

    QUnit.test(`drag and drop on month mode with all_day mapping`, async (assert) => {
        // Same test as before but in calendarEventToRecord (calendar_model.js) there is
        // different condition branching with all_day mapping or not
        assert.expect(1);

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" mode="month" event_open_popup="1" quick_add="0" all_day="allday">
                    <field name="name" />
                    <field name="partner_id" />
                </calendar>
            `,
        });

        // Create event (on 20 december)
        await clickDate(target, "2016-12-20");
        await editInput(target.querySelector(".modal-body input"), null, "An event");
        await click(target.querySelector(`.o_field_widget[name="allday"] input`));

        // use datepicker to enter a date: 12/20/2016 07:00:00
        await click(target, `.o_field_widget[name="start"] .o_datepicker .o_datepicker_input`);
        await click(
            document.body,
            `.bootstrap-datetimepicker-widget .picker-switch a[data-action="togglePicker"]`
        );
        await click(document.body, `.bootstrap-datetimepicker-widget .timepicker .timepicker-hour`);
        await click(
            document.body.querySelectorAll(
                `.bootstrap-datetimepicker-widget .timepicker-hours td.hour`
            )[7]
        );
        await click(
            document.body,
            `.bootstrap-datetimepicker-widget .picker-switch a[data-action="close"]`
        );

        // use datepicker to enter a date: 12/20/2016 19:00:00
        await click(target, `.o_field_widget[name="stop"] .o_datepicker .o_datepicker_input`);
        await click(
            document.body,
            `.bootstrap-datetimepicker-widget .picker-switch a[data-action="togglePicker"]`
        );
        await click(document.body, `.bootstrap-datetimepicker-widget .timepicker .timepicker-hour`);
        await click(
            document.body.querySelectorAll(
                `.bootstrap-datetimepicker-widget .timepicker-hours td.hour`
            )[19]
        );
        await click(
            document.body,
            `.bootstrap-datetimepicker-widget .picker-switch a[data-action="close"]`
        );

        await click(target.querySelector(".modal .o_form_button_save"));

        // Move event to another day (on 19 december)
        await moveEventToDate(target, 8, "2016-12-19");
        await clickEvent(target, 8);

        const row = target.querySelectorAll(".o_cw_body .list-group-item")[1];
        assert.strictEqual(
            row.textContent.trim(),
            "07:00 - 19:00 (12 hours)",
            "start and end hours shouldn't have been changed"
        );
    });

    QUnit.test(`drag and drop on month mode with date_start and date_delay`, async (assert) => {
        assert.expect(1);

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_delay="delay" mode="month">
                    <field name="name" />
                    <field name="start" />
                    <field name="delay" />
                </calendar>
            `,
            mockRPC(route, { args, method }) {
                if (method === "write") {
                    // delay should not be written at drag and drop
                    assert.strictEqual(args[1].delay, undefined);
                }
            },
        });

        // Create event (on 20 december)
        await clickDate(target, "2016-12-20");
        await editInput(target.querySelector(".modal-body input"), null, "An event");
        await click(target, ".o-calendar-quick-create--create-btn");

        // Move event to another day (on 27 november)
        await moveEventToDate(target, 8, "2016-11-27");
    });

    QUnit.test(`form_view_id attribute works (for creating events)`, async (assert) => {
        assert.expect(1);

        serviceRegistry.add(
            "action",
            {
                ...actionService,
                start() {
                    const result = actionService.start(...arguments);
                    const doAction = result.doAction;
                    result.doAction = (request) => {
                        assert.strictEqual(
                            request.views[0][0],
                            42,
                            "should do a do_action with view id 42"
                        );
                        return doAction(request);
                    };
                    return result;
                },
            },
            { force: true }
        );

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" mode="month" form_view_id="42" />
            `,
            mockRPC(route, { method }) {
                if (method === "create") {
                    // we simulate here the case where a create call with just
                    // the field name fails.  This is a normal flow, the server
                    // reject the create rpc (quick create), then the web client
                    // fall back to a form view. This happens typically when a
                    // model has required fields
                    return Promise.reject("None shall pass!");
                }
            },
        });

        await clickDate(target, "2016-12-13");
        await editInput(target.querySelector(".modal-body input"), null, "It's just a fleshwound");
        await click(target, ".o-calendar-quick-create--create-btn");
    });

    QUnit.test(`form_view_id attribute works with popup (for creating events)`, async (assert) => {
        assert.expect(1);

        serviceRegistry.add(
            "action",
            {
                ...actionService,
                start() {
                    const result = actionService.start(...arguments);
                    const doAction = result.doAction;
                    result.doAction = (request) => {
                        assert.strictEqual(request.views[0][0], 1, "should load view with id 1");
                        return doAction(request);
                    };
                    return result;
                },
            },
            { force: true }
        );

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" mode="month" open_event_popup="1" quick_add="0" form_view_id="1">
                    <field name="name" />
                </calendar>
            `,
        });

        await clickDate(target, "2016-12-13");
    });

    QUnit.test(`calendar fallback to form view id in action if necessary`, async (assert) => {
        assert.expect(1);
        serviceRegistry.add(
            "action",
            {
                ...actionService,
                start() {
                    const result = actionService.start(...arguments);
                    const doAction = result.doAction;
                    result.doAction = (request) => {
                        assert.deepEqual(request, {
                            type: "ir.actions.act_window",
                            res_model: "event",
                            views: [[43, "form"]], // should use the view id from the config
                            target: "current",
                            context: {
                                lang: "en",
                                uid: 7,
                                tz: "taht",
                                default_name: "It's just a fleshwound",
                                default_start: "2016-12-13 06:00:00",
                                default_stop: "2016-12-13 18:00:00",
                                default_allday: true,
                            },
                        });
                        return doAction(request);
                    };
                    return result;
                },
            },
            { force: true }
        );
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `<calendar date_start="start" date_stop="stop" mode="month" />`,
            config: { views: [[43, "form"]] },
            mockRPC(route, { method }) {
                if (method === "create") {
                    // we simulate here the case where a create call with just
                    // the field name fails.  This is a normal flow, the server
                    // reject the create rpc (quick create), then the web client
                    // fall back to a form view. This happens typically when a
                    // model has required fields
                    return Promise.reject("None shall pass!");
                }
            },
        });

        await clickDate(target, "2016-12-13");
        await editInput(target.querySelector(".modal-body input"), null, "It's just a fleshwound");
        await click(target, ".o-calendar-quick-create--create-btn");
    });

    QUnit.test(`fullcalendar initializes with right locale`, async (assert) => {
        // The machine that runs this test must have this locale available
        patchWithCleanup(luxon.Settings, { defaultLocale: "fr" });
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `<calendar date_start="start" date_stop="stop" mode="week"/>`,
        });
        assert.deepEqual(
            [...target.querySelectorAll(".fc-day-header")].map((el) => el.textContent),
            ["dim. 11", "lun. 12", "mar. 13", "mer. 14", "jeu. 15", "ven. 16", "sam. 17"]
        );
    });

    QUnit.test(`initial_date given in the context`, async (assert) => {
        assert.expect(1);
        serverData.views = {
            "event,1,calendar": `<calendar date_start="start" date_stop="stop" mode="day"/>`,
            "event,false,search": `<search />`,
        };
        serverData.actions = {
            1: {
                id: 1,
                name: "context initial date",
                res_model: "event",
                type: "ir.actions.act_window",
                views: [[1, "calendar"]],
                context: { initial_date: "2016-01-30 08:00:00" }, // 30th of january
            },
        };
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 1);
        await nextTick();
        assert.strictEqual(
            target.querySelector(".o_control_panel .breadcrumb-item").textContent,
            "context initial date (January 30, 2016)",
            "should display day passed in the context"
        );
    });

    QUnit.test(`default week start (US) month mode`, async (assert) => {
        // if not given any option, default week start is on Sunday
        assert.expect(8);

        // 2019-09-12 08:00:00
        patchDate(2019, 8, 12, 8, 0, 0);

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" mode="month" />
            `,
            mockRPC(route, { method, model, kwargs }) {
                if (model === "event" && method === "search_read") {
                    assert.deepEqual(
                        kwargs.domain,
                        [
                            ["start", "<=", "2019-10-12 22:59:59"],
                            ["stop", ">=", "2019-08-31 23:00:00"],
                        ],
                        "The domain to search events in should be correct"
                    );
                }
            },
        });

        const dayHeaders = target.querySelectorAll(".fc-day-header");
        assert.strictEqual(
            dayHeaders[0].textContent,
            "Sunday",
            "The first day of the week should be Sunday"
        );
        assert.strictEqual(
            dayHeaders[dayHeaders.length - 1].textContent,
            "Saturday",
            "The last day of the week should be Saturday"
        );

        const dayTops = target.querySelectorAll(".fc-day-top");
        assert.strictEqual(
            dayTops[0].querySelector(".fc-week-number").textContent,
            "36",
            "The number of the week should be correct"
        );
        assert.strictEqual(dayTops[0].querySelector(".fc-day-number").textContent, "1");
        assert.strictEqual(dayTops[0].dataset.date, "2019-09-01");
        assert.strictEqual(
            dayTops[dayTops.length - 1].querySelector(".fc-day-number").textContent,
            "12"
        );
        assert.strictEqual(dayTops[dayTops.length - 1].dataset.date, "2019-10-12");
    });

    QUnit.test(`European week start month mode`, async (assert) => {
        assert.expect(8);

        patchDate(2019, 8, 15, 8, 0, 0); // 2019-09-15 08:00:00
        // the week start depends on the locale
        patchWithCleanup(localization, { weekStart: 1 });

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" mode="month" />
            `,
            mockRPC(route, { method, model, kwargs }) {
                if (model === "event" && method === "search_read") {
                    assert.deepEqual(
                        kwargs.domain,
                        [
                            ["start", "<=", "2019-10-06 22:59:59"],
                            ["stop", ">=", "2019-08-25 23:00:00"],
                        ],
                        "The domain to search events in should be correct"
                    );
                }
            },
        });

        const dayHeaders = target.querySelectorAll(".fc-day-header");
        assert.strictEqual(
            dayHeaders[0].textContent,
            "Monday",
            "The first day of the week should be Monday"
        );
        assert.strictEqual(
            dayHeaders[dayHeaders.length - 1].textContent,
            "Sunday",
            "The last day of the week should be Sunday"
        );

        const dayTops = target.querySelectorAll(".fc-day-top");
        assert.strictEqual(
            dayTops[0].querySelector(".fc-week-number").textContent,
            "35",
            "The number of the week should be correct"
        );
        assert.strictEqual(dayTops[0].querySelector(".fc-day-number").textContent, "26");
        assert.strictEqual(dayTops[0].dataset.date, "2019-08-26");
        assert.strictEqual(
            dayTops[dayTops.length - 1].querySelector(".fc-day-number").textContent,
            "6"
        );
        assert.strictEqual(dayTops[dayTops.length - 1].dataset.date, "2019-10-06");
    });

    QUnit.test(`Monday week start week mode`, async (assert) => {
        assert.expect(4);

        patchDate(2019, 8, 15, 8, 0, 0); // 2019-09-15 08:00:00
        // the week start depends on the locale
        patchWithCleanup(localization, { weekStart: 1 });

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" mode="week" />
            `,
            mockRPC(route, { method, model, kwargs }) {
                if (model === "event" && method === "search_read") {
                    assert.deepEqual(
                        kwargs.domain,
                        [
                            ["start", "<=", "2019-09-15 22:59:59"],
                            ["stop", ">=", "2019-09-08 23:00:00"],
                        ],
                        "The domain to search events in should be correct"
                    );
                }
            },
        });

        const dayHeaders = target.querySelectorAll(".fc-day-header");
        assert.strictEqual(
            dayHeaders[0].textContent,
            "Mon 9",
            "The first day of the week should be Monday the 9th"
        );
        assert.strictEqual(
            dayHeaders[dayHeaders.length - 1].textContent,
            "Sun 15",
            "The last day of the week should be Sunday the 15th"
        );
        assert.strictEqual(
            target.querySelector(".fc-head .fc-week-number").textContent,
            "Week 37",
            "The number of the week should be correct"
        );
    });

    QUnit.test(`Saturday week start week mode`, async (assert) => {
        assert.expect(4);

        patchDate(2019, 8, 12, 8, 0, 0); // 2019-09-12 08:00:00

        // the week start depends on the locale
        patchWithCleanup(localization, { weekStart: 6 });

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" mode="week" />
            `,
            mockRPC(route, { method, model, kwargs }) {
                if (model === "event" && method === "search_read") {
                    assert.deepEqual(
                        kwargs.domain,
                        [
                            ["start", "<=", "2019-09-13 22:59:59"],
                            ["stop", ">=", "2019-09-06 23:00:00"],
                        ],
                        "The domain to search events in should be correct"
                    );
                }
            },
        });

        const dayHeaders = target.querySelectorAll(".fc-day-header");
        assert.strictEqual(
            dayHeaders[0].textContent,
            "Sat 7",
            "The first day of the week should be Saturday the 7th"
        );
        assert.strictEqual(
            dayHeaders[dayHeaders.length - 1].textContent,
            "Fri 13",
            "The last day of the week should be Friday the 13th"
        );
        assert.strictEqual(
            target.querySelector(".fc-head .fc-week-number").textContent,
            "Week 36",
            "The number of the week should be correct"
        );
    });

    QUnit.test(`Monday week start year mode`, async (assert) => {
        assert.expect(4);

        patchDate(2019, 8, 15, 8, 0, 0); // 2019-09-15 08:00:00
        // the week start depends on the locale
        patchWithCleanup(localization, { weekStart: 1 });

        patchWithCleanup(CalendarYearRenderer.prototype, {
            get options() {
                return { ...this._super(), weekNumbers: true };
            },
        });

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" mode="year" />
            `,
            mockRPC(route, { method, model, kwargs }) {
                if (model === "event" && method === "search_read") {
                    assert.deepEqual(
                        kwargs.domain,
                        [
                            ["start", "<=", "2019-12-31 22:59:59"],
                            ["stop", ">=", "2018-12-31 23:00:00"],
                        ],
                        "The domain to search events in should be correct"
                    );
                }
            },
        });

        const weekRow = target.querySelector(".fc-day-top.fc-today").closest("tr");
        const weekDays = weekRow.querySelectorAll(".fc-day-top");
        assert.strictEqual(
            weekDays[0].textContent,
            "9",
            "The first day of the week should be Monday the 9th"
        );
        assert.strictEqual(
            weekDays[weekDays.length - 1].textContent,
            "15",
            "The last day of the week should be Sunday the 15th"
        );
        assert.strictEqual(
            weekRow.querySelector(".fc-week-number").textContent,
            "37",
            "The number of the week should be correct"
        );
    });

    QUnit.test(`Sunday week start year mode`, async (assert) => {
        assert.expect(4);

        patchDate(2019, 8, 15, 8, 0, 0); // 2019-09-15 08:00:00
        // the week start depends on the locale
        // the localization presents a python-like 1 to 7 weekStart value
        patchWithCleanup(localization, { weekStart: 7 });

        patchWithCleanup(CalendarYearRenderer.prototype, {
            get options() {
                return { ...this._super(), weekNumbers: true };
            },
        });

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" mode="year" />
            `,
            mockRPC(route, { method, model, kwargs }) {
                if (model === "event" && method === "search_read") {
                    assert.deepEqual(
                        kwargs.domain,
                        [
                            ["start", "<=", "2019-12-31 22:59:59"],
                            ["stop", ">=", "2018-12-31 23:00:00"],
                        ],
                        "The domain to search events in should be correct"
                    );
                }
            },
        });

        const weekRow = target.querySelector(".fc-day-top.fc-today").closest("tr");
        const weekDays = weekRow.querySelectorAll(".fc-day-top");
        assert.strictEqual(
            weekDays[0].textContent,
            "15",
            "The first day of the week should be Sunday the 15th"
        );
        assert.strictEqual(
            weekDays[weekDays.length - 1].textContent,
            "21",
            "The last day of the week should be Saturday the 21st"
        );
        assert.strictEqual(
            weekRow.querySelector(".fc-week-number").textContent,
            "38",
            "The number of the week should be correct"
        );
    });

    QUnit.test(
        `edit record and attempt to create a record with "create" attribute set to false`,
        async (assert) => {
            assert.expect(8);

            await makeView({
                type: "calendar",
                resModel: "event",
                serverData,
                arch: `
                    <calendar event_open_popup="1" create="0" date_start="start" date_stop="stop" mode="month" />
                `,
                mockRPC(route, { args, method }) {
                    if (method === "write") {
                        assert.deepEqual(
                            args[1],
                            { name: "event 4 modified" },
                            "should update the record"
                        );
                    }
                },
            });

            // editing existing events should still be possible
            // click on an existing event to open the formViewDialog
            await clickEvent(target, 4);
            assert.containsOnce(target, ".o_cw_popover", "should open a popover clicking on event");
            assert.containsOnce(
                target,
                ".o_cw_popover .o_cw_popover_edit",
                "popover should have an edit button"
            );
            assert.containsOnce(
                target,
                ".o_cw_popover .o_cw_popover_delete",
                "popover should have a delete button"
            );
            assert.containsOnce(
                target,
                ".o_cw_popover .o_cw_popover_close",
                "popover should have a close button"
            );

            await click(target, ".o_cw_popover .o_cw_popover_edit");
            assert.containsOnce(
                target,
                ".modal-body",
                "should open the form view in dialog when click on edit"
            );

            await editInput(target.querySelector(".modal-body input"), null, "event 4 modified");
            await click(target.querySelector(".modal-footer .o_form_button_save"));
            assert.containsNone(target, ".modal", "save button should close the modal");

            // creating an event should not be possible
            // attempt to create a new event with create set to false
            await clickDate(target, "2016-12-13");
            assert.containsNone(
                target,
                ".modal",
                "shouldn't open a quick create dialog for creating a new event with create attribute set to false"
            );
        }
    );

    QUnit.test(
        `attempt to create record with "create" and "quick_add" attributes set to false`,
        async (assert) => {
            assert.expect(1);

            await makeView({
                type: "calendar",
                resModel: "event",
                serverData,
                arch: `
                    <calendar create="0" event_open_popup="1" quick_add="0" date_start="start" date_stop="stop" mode="month" />
                `,
            });

            // attempt to create a new event with create set to false
            await clickDate(target, "2016-12-13");
            assert.containsNone(
                target,
                ".modal",
                "shouldn't open a form view for creating a new event with create attribute set to false"
            );
        }
    );

    QUnit.test(
        `attempt to create multiples events and the same day and check the ordering on month view`,
        async (assert) => {
            // This test aims to verify that the order of the event in month view is coherent with their start date.
            patchDate(2020, 2, 12, 8, 0, 0); // 2020-03-12 08:00:00

            serverData.models.event.records = [
                {
                    id: 1,
                    name: "Second event",
                    start: "2020-03-12 05:00:00",
                    stop: "2020-03-12 07:00:00",
                    allday: false,
                },
                {
                    id: 2,
                    name: "First event",
                    start: "2020-03-12 02:00:00",
                    stop: "2020-03-12 03:00:00",
                    allday: false,
                },
                {
                    id: 3,
                    name: "Third event",
                    start: "2020-03-12 08:00:00",
                    stop: "2020-03-12 09:00:00",
                    allday: false,
                },
            ];

            await makeView({
                type: "calendar",
                resModel: "event",
                serverData,
                arch: `
                    <calendar date_start="start" date_stop="stop" all_day="allday" mode="month" />
                `,
            });

            assert.containsOnce(
                target,
                ".o_calendar_renderer .fc-view-container",
                "should display in the calendar"
            );

            // Testing the order of the events: by start date
            assert.containsN(target, ".o_event_title", 3, "3 events should be available");
            assert.strictEqual(
                target.querySelector(".o_event_title").textContent,
                "First event",
                "First event should be on top"
            );
        }
    );

    QUnit.test(`create event and resize to next day (24h) on week mode`, async (assert) => {
        // WOWL FYI Legacy test name: "drag and drop 24h event on week mode"
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar event_open_popup="1" quick_add="0" date_start="start" date_stop="stop" all_day="allday" mode="week" />
            `,
            mockRPC(route, { args, method }) {
                if (method === "create") {
                    assert.deepEqual(args[0], {
                        allday: false,
                        name: "foobar",
                        start: "2016-12-13 07:00:00",
                        start_date: false,
                        stop: "2016-12-13 15:00:00",
                        stop_date: false,
                    });
                }
                if (method === "write") {
                    assert.deepEqual(args[1], {
                        allday: false,
                        start: "2016-12-13 07:00:00",
                        stop: "2016-12-14 07:00:00",
                    });
                }
            },
        });
        await selectTimeRange(target, "2016-12-13 08:00:00", "2016-12-13 16:00:00");
        await editInput(target, ".modal [name=name] input", "foobar");
        await click(target, ".modal .o_form_button_save");
        await resizeEventToTime(target, 8, "2016-12-14 08:00:00");
        const event = findEvent(target, 8);
        assert.strictEqual(event.textContent, "foobar");
        assert.notOk(event.closest(".fc-day-grid"), "event should not be in the all day slots");
    });

    QUnit.test(`correctly display year view`, async (assert) => {
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar create="0" event_open_popup="1" date_start="start" date_stop="stop" all_day="allday" mode="year" attendee="partner_ids" color="partner_id">
                    <field name="partner_ids" write_model="filter_partner" write_field="partner_id" />
                    <field name="partner_id" filters="1" invisible="1" />
                    <field name="is_hatched" invisible="1" />
                    <field name="is_striked" invisible="1" />
                </calendar>
            `,
        });

        await toggleFilter(target, "partner_ids", 1);
        await toggleFilter(target, "partner_ids", 2);

        // Check view
        assert.containsN(target, ".fc-month", 12);
        assert.strictEqual(
            target.querySelector(".fc-month .fc-header-toolbar").textContent,
            "Jan 2016"
        );
        assert.containsN(
            target,
            ".fc-bgevent",
            7,
            "There should be 6 events displayed but there is 1 split on 2 weeks"
        );
        assert.containsN(target, ".o_event_hatched", 3);
        assert.containsOnce(target, ".o_event_striked");

        await clickDate(target, "2016-11-17");
        assert.containsNone(target, ".o_popover");

        await clickDate(target, "2016-11-16");
        assert.containsOnce(target, ".o_popover");

        let popoverText = target
            .querySelector(".o_popover")
            .textContent.replace(/\s{2,}/g, " ")
            .trim();
        assert.strictEqual(popoverText, "November 14-16, 2016event 7");
        await click(target, ".o_cw_popover_close");
        assert.containsNone(target, ".o_popover");

        await clickDate(target, "2016-11-14");
        assert.containsOnce(target, ".o_popover");
        popoverText = target
            .querySelector(".o_popover")
            .textContent.replace(/\s{2,}/g, " ")
            .trim();
        assert.strictEqual(popoverText, "November 14-16, 2016event 7");
        await click(target, ".o_cw_popover_close");
        assert.containsNone(target, ".o_popover");

        await clickDate(target, "2016-11-13");
        assert.containsNone(target, ".o_popover");

        await clickDate(target, "2016-12-10");
        assert.containsNone(target, ".o_popover");

        await clickDate(target, "2016-12-12");
        assert.containsOnce(target, ".o_popover");
        popoverText = target
            .querySelector(".o_popover")
            .textContent.replace(/\s{2,}/g, " ")
            .trim();
        assert.strictEqual(popoverText, "December 12, 201611:55 event 216:55 event 3");
        await click(target, ".o_cw_popover_close");
        assert.containsNone(target, ".o_popover");

        await clickDate(target, "2016-12-14");
        assert.containsOnce(target, ".o_popover");
        popoverText = target
            .querySelector(".o_popover")
            .textContent.replace(/\s{2,}/g, " ")
            .trim();
        assert.strictEqual(popoverText, "December 14, 2016event 4December 13-20, 2016event 5");
        await click(target, ".o_cw_popover_close");
        assert.containsNone(target, ".o_popover");

        await clickDate(target, "2016-12-21");
        assert.containsNone(target, ".o_popover");
    });

    QUnit.test(`toggle filters in year view`, async (assert) => {
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar event_open_popup="1" date_start="start" date_stop="stop" all_day="allday" mode="year" attendee="partner_ids" color="partner_id">
                    <field name="partner_ids" write_model="filter_partner" write_field="partner_id" />
                    <field name="partner_id" filters="1" invisible="1" />
                </calendar>
            `,
        });

        function checkEvents(countMap) {
            for (const [id, count] of Object.entries(countMap)) {
                assert.containsN(target, `.fc-bgevent[data-event-id="${id}"]`, count);
            }
        }

        // activate partner filter
        await toggleFilter(target, "partner_ids", 1);
        await toggleFilter(target, "partner_ids", 2);
        checkEvents({ 1: 1, 2: 1, 3: 1, 4: 1, 5: 2, 7: 1 });

        await toggleFilter(target, "partner_ids", 2);
        checkEvents({ 1: 1, 2: 1, 3: 1, 4: 1, 5: 0, 7: 0 });

        await toggleFilter(target, "partner_id", 1);
        checkEvents({ 1: 0, 2: 0, 3: 1, 4: 0, 5: 0, 7: 0 });

        await toggleFilter(target, "partner_id", 4);
        checkEvents({ 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 7: 0 });

        await toggleFilter(target, "partner_ids", 1);
        checkEvents({ 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 7: 0 });

        await toggleFilter(target, "partner_ids", 2);
        checkEvents({ 1: 1, 2: 1, 3: 0, 4: 0, 5: 2, 7: 1 });

        await toggleFilter(target, "partner_id", 4);
        checkEvents({ 1: 1, 2: 1, 3: 0, 4: 0, 5: 0, 7: 1 });
    });

    QUnit.test(`allowed scales`, async (assert) => {
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" scales="day,week" />
            `,
        });

        await click(target, ".o_calendar_scale_buttons .scale_button_selection");
        assert.containsOnce(target, ".o_calendar_scale_buttons .o_calendar_button_day");
        assert.containsOnce(target, ".o_calendar_scale_buttons .o_calendar_button_week");
        assert.containsNone(target, ".o_calendar_scale_buttons .o_calendar_button_month");
        assert.containsNone(target, ".o_calendar_scale_buttons .o_calendar_button_year");
    });

    QUnit.test(`click outside the popup should close it`, async (assert) => {
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar create="0" event_open_popup="1" quick_add="0" date_start="start" date_stop="stop" all_day="allday" mode="month" />
            `,
        });

        assert.containsNone(target, ".o_cw_popover");

        await clickEvent(target, 1);
        assert.containsOnce(target, ".o_cw_popover", "open popup when click on event");

        await click(target, ".o_cw_popover .o_cw_body");
        assert.containsOnce(target, ".o_cw_popover", "keep popup openned when click inside popup");

        await click(target);
        assert.containsNone(target, ".o_cw_popover", "close popup when click outside popup");
    });

    QUnit.test(`fields are added in the right order in popover`, async (assert) => {
        const def = makeDeferred();
        class DeferredWidget extends owl.Component {
            setup() {
                owl.onWillStart(() => def);
            }
        }
        DeferredWidget.template = owl.xml``;
        fieldRegistry.add("deferred_widget", DeferredWidget);
        registerCleanup(() => fieldRegistry.remove("deferred_widget"));

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" mode="month">
                    <field name="user_id" widget="deferred_widget" />
                    <field name="name" />
                </calendar>
            `,
        });

        await clickEvent(target, 4);
        assert.containsNone(target, ".o_cw_popover");

        def.resolve();
        await nextTick();
        assert.containsOnce(target, ".o_cw_popover");

        assert.strictEqual(
            target.querySelector(".o_cw_popover .o_cw_popover_fields_secondary").textContent,
            "user: name: event 4"
        );
    });

    QUnit.test(`select events and discard create`, async (assert) => {
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar event_open_popup="1" date_start="start" date_stop="stop" all_day="allday" mode="year" />
            `,
        });

        assert.containsN(target, ".fc-dayGridMonth-view", 12, "should display in year mode");
        await selectDateRange(target, "2016-11-13", "2016-11-19");
        assert.containsOnce(
            target,
            ".o-calendar-quick-create",
            "should open the form view in dialog when select multiple days"
        );

        assert.hasAttrValue(
            target.querySelector(".fc-highlight"),
            "colspan",
            "7",
            "should highlight 7 days"
        );

        await click(target, ".o-calendar-quick-create--cancel-btn");
        assert.containsNone(target, ".fc-highlight", "should not highlight days");
    });

    QUnit.test(`create event in year view`, async (assert) => {
        assert.expect(6);
        let expectedEvent;
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar event_open_popup="1" date_start="start" date_stop="stop" all_day="allday" mode="year" />
            `,
            mockRPC(route, { method, args }) {
                if (method === "create") {
                    assert.deepEqual(args[0], expectedEvent);
                }
            },
        });

        // Select the whole month of July
        expectedEvent = {
            allday: true,
            start: "2016-07-01",
            stop: "2016-07-31",
            name: "Whole July",
        };
        await selectDateRange(target, "2016-07-01", "2016-07-31");
        await editInput(target, ".o-calendar-quick-create--input[name=title]", "Whole July");
        await click(target, ".o-calendar-quick-create--create-btn");

        // get all rows for event 8
        assert.containsN(target, ".o_event[data-event-id='8']", 6);
        assert.deepEqual(
            [...target.querySelectorAll(".o_event[data-event-id='8']")].map((cell) => cell.colSpan),
            [2, 7, 7, 7, 7, 1],
            "rows should highlight multiple days"
        );

        // Select the whole month of November
        expectedEvent = {
            allday: true,
            start: "2016-11-01",
            stop: "2016-11-30",
            name: "Whole November",
        };
        await selectDateRange(target, "2016-11-01", "2016-11-30");
        await editInput(target, ".o-calendar-quick-create--input[name=title]", "Whole November");
        await click(target, ".o-calendar-quick-create--create-btn");

        // get all rows for event 9
        assert.containsN(target, ".o_event[data-event-id='9']", 5);
        assert.deepEqual(
            [...target.querySelectorAll(".o_event[data-event-id='9']")].map((cell) => cell.colSpan),
            [5, 7, 7, 7, 4],
            "rows should highlight multiple days"
        );
    });

    QUnit.test(`popover ignores readonly field modifier`, async (assert) => {
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" mode="month">
                    <field name="name" attrs="{'readonly': [['unknown_field', '=', 42]]}" />
                </calendar>
            `,
        });

        await clickEvent(target, 4);
        // test would fail here if we don't ignore readonly modifier
        assert.containsOnce(target, ".o_cw_popover");
    });

    QUnit.test("can not select invalid scale from datepicker", async (assert) => {
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" all_day="allday" mode="month" scales="month,year">
                    <field name="name" attrs="{'readonly': [['unknown_field', '=', 42]]}" />
                </calendar>
            `,
        });

        await click(target, ".ui-datepicker-today");
        // test would fail here if we went to week mode
        assert.containsOnce(target, ".fc-dayGridMonth-view");
    });
});
