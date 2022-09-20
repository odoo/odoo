/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { click, getFixture, nextTick, patchDate, patchWithCleanup } from "../../helpers/utils";
import { clickEvent, toggleSectionFilter } from "../../views/calendar/helpers";
import { makeView, setupViewRegistries } from "../../views/helpers";

// const CalendarRenderer = require("web.CalendarRenderer");
// const CalendarView = require("web.CalendarView");
// const testUtils = require("web.test_utils");

// const preInitialDate = new Date(2016, 11, 12, 8, 0, 0);
// const initialDate = new Date(
//     preInitialDate.getTime() - preInitialDate.getTimezoneOffset() * 60 * 1000
// );

let target;
let serverData;

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

        // serviceRegistry.add(
        //     "user",
        //     {
        //         ...userService,
        //         start() {
        //             const fakeUserService = userService.start(...arguments);
        //             Object.defineProperty(fakeUserService, "userId", {
        //                 get: () => uid,
        //             });
        //             return fakeUserService;
        //         },
        //     },
        //     { force: true }
        // );

        serverData = {
            models: {
                event: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        name: { string: "name", type: "char" },
                        start: { string: "start datetime", type: "datetime" },
                        stop: { string: "stop datetime", type: "datetime" },
                        partner_id: {
                            string: "user",
                            type: "many2one",
                            relation: "partner",
                            related: "user_id.partner_id",
                            default: 1,
                        },
                    },
                    records: [
                        {
                            id: 1,
                            partner_id: 1,
                            name: "event 1",
                            start: "2016-12-11 00:00:00",
                            stop: "2016-12-11 00:00:00",
                        },
                        {
                            id: 2,
                            partner_id: 2,
                            name: "event 2",
                            start: "2016-12-12 10:55:05",
                            stop: "2016-12-12 14:55:05",
                        },
                    ],
                    methods: {
                        check_access_rights() {
                            return Promise.resolve(true);
                        },
                    },
                },
                partner: {
                    fields: {
                        id: { string: "ID", type: "integer" },
                        image: { string: "Image", type: "binary" },
                        display_name: { string: "Displayed name", type: "char" },
                    },
                    records: [
                        { id: 1, display_name: "partner 1", image: "AAA" },
                        { id: 2, display_name: "partner 2", image: "BBB" },
                    ],
                },
            },
        };
    });

    QUnit.module("CalendarView - Mobile");

    QUnit.test("simple calendar rendering in mobile", async function (assert) {
        await makeView({
            type: "calendar",
            resModel: "event",
            arch: `
                <calendar date_start="start" date_stop="stop">
                    <field name="name"/>
                </calendar>`,
            serverData,
        });

        assert.containsNone(target, ".o_calendar_button_prev", "prev button should be hidden");
        assert.containsNone(target, ".o_calendar_button_next", "next button should be hidden");
        assert.isVisible(
            target.querySelector(".o_control_panel .o_cp_bottom_right button.o_cp_today_button"),
            "today button should be visible in the pager area (bottom right corner)"
        );

        // Test all views
        // displays month mode by default
        assert.containsOnce(
            target,
            ".fc-view-container > .fc-timeGridWeek-view",
            "should display the current week"
        );
        assert.equal(
            target.querySelector(".breadcrumb-item").textContent,
            "undefined (Dec 11 – 17, 2016)"
        );

        // switch to day mode
        await click(target, ".o_control_panel .scale_button_selection");
        await click(target, ".o_control_panel .o_calendar_button_day");
        await nextTick();
        assert.containsOnce(
            target,
            ".fc-view-container > .fc-timeGridDay-view",
            "should display the current day"
        );
        assert.equal(
            target.querySelector(".breadcrumb-item").textContent,
            "undefined (December 12, 2016)"
        );

        // switch to month mode
        await click(target, ".o_control_panel .scale_button_selection");
        await click(target, ".o_control_panel .o_calendar_button_month");
        await nextTick();
        assert.containsOnce(
            target,
            ".fc-view-container > .fc-dayGridMonth-view",
            "should display the current month"
        );
        assert.equal(
            target.querySelector(".breadcrumb-item").textContent,
            "undefined (December 2016)"
        );

        // switch to year mode
        await click(target, ".o_control_panel .scale_button_selection");
        await click(target, ".o_control_panel .o_calendar_button_year");
        await nextTick();
        assert.containsOnce(
            target,
            ".fc-view-container > .fc-dayGridYear-view",
            "should display the current year"
        );
        assert.equal(target.querySelector(".breadcrumb-item").textContent, "undefined (2016)");
    });

    QUnit.test("calendar: popover is rendered as dialog in mobile", async function (assert) {
        // Legacy name of this test: "calendar: popover rendering in mobile"
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop">
                    <field name="name"/>
                </calendar>`,
        });

        await clickEvent(target, 1);
        assert.containsNone(target, ".o_cw_popover");
        assert.containsOnce(target, ".modal");
        assert.hasClass(target.querySelector(".modal"), "o_modal_full");

        assert.containsN(target, ".modal-footer .btn", 2);
        assert.containsOnce(target, ".modal-footer .btn.btn-primary.o_cw_popover_edit");
        assert.containsOnce(target, ".modal-footer .btn.btn-secondary.o_cw_popover_delete");
    });

    QUnit.todo("calendar: today button", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `<calendar mode="day" date_start="start" date_stop="stop"></calendar>`,
        });

        // TO MAKE this test pass:
        // - implement the prev/next scale left/right swipe actions
        // - make the view
        // - check that the day header indicates today
        // - swipe left or right
        // - check that the day header indicates the new day
        // - click on the today button
        // - check that the day header indicates today

        // const previousDate = target.querySelector(".fc-day-header[data-date]").dataset.date;
        // await click(target, ".o_calendar_button_today");

        // const newDate = target.querySelector(".fc-day-header[data-date]").dataset.date;
        // assert.notEqual(
        //     newDate,
        //     previousDate,
        //     "The today button must change the view to the today date"
        // );
    });

    QUnit.test("calendar: show and change other calendar", async function (assert) {
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop" color="partner_id">
                    <filter name="user_id" avatar_field="image"/>
                    <field name="partner_id" filters="1" invisible="1"/>
                </calendar>`,
        });

        assert.containsOnce(target, ".o_other_calendar_panel");
        assert.containsN(
            target,
            ".o_other_calendar_panel .o_filter > *",
            3,
            "should contains 3 child nodes -> 1 label (USER) + 2 resources (user 1/2)"
        );
        assert.containsNone(target, ".o_calendar_sidebar");
        assert.containsOnce(target, ".o_calendar_view");

        // Toggle the other calendar panel should hide the calendar view and show the sidebar
        await click(target, ".o_other_calendar_panel");
        assert.containsOnce(target, ".o_calendar_sidebar");
        assert.containsNone(target, ".o_calendar_view");
        assert.containsOnce(target, ".o_calendar_filter");
        assert.containsOnce(target, ".o_calendar_filter[data-name=partner_id]");

        // Toggle the whole section filters by unchecking the all items checkbox
        await toggleSectionFilter(target, "partner_id");
        assert.containsN(
            target,
            ".o_other_calendar_panel .o_filter > *",
            1,
            "should contains 1 child node -> 1 label (USER)"
        );

        // Toggle again the other calendar panel should hide the sidebar and show the calendar view
        await click(target, ".o_other_calendar_panel");
        assert.containsNone(target, ".o_calendar_sidebar");
        assert.containsOnce(target, ".o_calendar_view");
    });

    QUnit.todo('calendar: short tap on "Free Zone" opens quick create', async function (assert) {
        assert.expect(3);

        // testUtils.mock.patch(CalendarRenderer, {
        //     _getFullCalendarOptions: function () {
        //         const options = this._super(...arguments);
        //         const oldSelect = options.select;
        //         options.select = (selectionInfo) => {
        //             assert.step("select");
        //             if (oldSelect) {
        //                 return oldSelect(selectionInfo);
        //             }
        //         };
        //         const oldDateClick = options.dateClick;
        //         options.dateClick = (dateClickInfo) => {
        //             assert.step("dateClick");
        //             if (oldDateClick) {
        //                 return oldDateClick(dateClickInfo);
        //             }
        //         };
        //         return options;
        //     },
        // });

        // await makeView({
        //     type: "calendar",
        //     resModel: "event",
        //     serverData,
        //     arch: `<calendar mode="day" date_start="start" date_stop="stop"/>`,
        // });

        // // Simulate a "TAP" (touch)
        // const initCell = target.querySelector(
        //     '.fc-time-grid .fc-minor[data-time="07:30:00"] .fc-widget-content:last-child'
        // );
        // const boundingClientRect = initCell.getBoundingClientRect();
        // const left = boundingClientRect.left + document.body.scrollLeft;
        // const top = boundingClientRect.top + document.body.scrollTop;
        // await testUtils.dom.triggerPositionalTapEvents(left, top);

        // assert.strictEqual(
        //     $(".modal").length,
        //     1,
        //     "should open a Quick create modal view in mobile on short tap"
        // );
        // assert.verifySteps(["dateClick"]);

        // testUtils.mock.unpatch(CalendarRenderer);
    });
});
