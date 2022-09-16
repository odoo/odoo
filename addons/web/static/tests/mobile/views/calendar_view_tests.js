/** @odoo-module **/

import { click, getFixture, nextTick, patchDate } from "../../helpers/utils";
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
        // patchWithCleanup(browser, {
        //     setTimeout: (fn) => fn(),
        //     clearTimeout: () => { },
        // });

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

    QUnit.todo("simple calendar rendering in mobile", async function (assert) {
        assert.expect(7);

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

        // switch to day mode
        await click(target, ".o_control_panel .scale_button_selection");
        await click(target, ".o_control_panel .o_calendar_button_day");
        assert.containsOnce(
            target,
            ".fc-view-container > .fc-timeGridDay-view",
            "should display the current day"
        );

        // switch to month mode
        await click(target, ".o_control_panel .scale_button_selection");
        await click(target, ".o_control_panel .o_calendar_button_month");
        assert.containsOnce(
            target,
            ".fc-view-container > .fc-dayGridMonth-view",
            "should display the current month"
        );

        // switch to year mode
        await click(target, ".o_control_panel .scale_button_selection");
        await click(target, ".o_control_panel .o_calendar_button_year");
        assert.containsOnce(
            target,
            ".fc-view-container > .fc-dayGridYear-view",
            "should display the current year"
        );
    });

    QUnit.todo("calendar: popover rendering in mobile", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `
                <calendar date_start="start" date_stop="stop">
                    <field name="name"/>
                </calendar>`,
        });

        const fullCalendarEvent = target.querySelector(".fc-event");

        await click(target, fullCalendarEvent);
        await nextTick();

        let popover = document.querySelector(".o_cw_popover");
        assert.ok(popover !== null, "there should be a modal");
        assert.ok(
            popover.parentNode === document.body,
            "the container of popover must be the body"
        );

        // Check if the popover is "fullscreen"
        const actualPosition = popover.getBoundingClientRect();
        const windowRight = document.documentElement.clientWidth;
        const windowBottom = document.documentElement.clientHeight;
        const expectedPosition = [0, windowRight, windowBottom, 0];

        assert.deepEqual(
            [actualPosition.top, actualPosition.right, actualPosition.bottom, actualPosition.left],
            expectedPosition,
            "popover should be at position 0 " +
                windowRight +
                " " +
                windowBottom +
                " 0 (top right bottom left)"
        );
        const closePopoverButton = document.querySelector(".o_cw_popover_close");
        await click(target, closePopoverButton);

        popover = document.querySelector(".o_cw_popover");
        assert.ok(popover === null, "there should be any modal");
    });

    QUnit.todo("calendar: today button", async function (assert) {
        assert.expect(1);
        // Take the current day
        const initialDate = new Date();
        // Increment by two days to avoid test error near midnight
        initialDate.setDate(initialDate.getDate() + 2);

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `<calendar mode="day" date_start="start" date_stop="stop"></calendar>`,
        });

        const previousDate = target.querySelector(".fc-day-header[data-date]").dataset.date;
        const todayButton = target.querySelector(".o_calendar_button_today");
        await click(target, todayButton);

        const newDate = target.querySelector(".fc-day-header[data-date]").dataset.date;
        assert.notEqual(
            newDate,
            previousDate,
            "The today button must change the view to the today date"
        );
    });

    QUnit.todo("calendar: show and change other calendar", async function (assert) {
        assert.expect(8);

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

        let otherCalendarPanel = target.querySelector(".o_other_calendar_panel");
        assert.ok(otherCalendarPanel !== null, "there should be a panel over the calendar");
        const span = otherCalendarPanel.querySelectorAll(".o_filter > span");
        assert.equal(
            span.length,
            3,
            "Panel should contains 3 span (1 label (USER) + 2 resources (user 1/2)"
        );

        const calendarSidebar = target.querySelector(".o_calendar_sidebar");
        const calendarElement = target.querySelector(".o_legacy_calendar_view");
        assert.isVisible(calendarElement, "the calendar should be visible");
        assert.isNotVisible(calendarSidebar, "the panel with other calendar shouldn't be visible");
        otherCalendarPanel = target.querySelector(".o_other_calendar_panel");
        await click(target, otherCalendarPanel);

        assert.isNotVisible(calendarElement, "the calendar shouldn't be visible");
        assert.isVisible(calendarSidebar, "the panel with other calendar should be visible");
        otherCalendarPanel = target.querySelector(".o_other_calendar_panel");
        await click(target, otherCalendarPanel);

        assert.isVisible(calendarElement, "the calendar should be visible again");
        assert.isNotVisible(
            calendarSidebar,
            "the panel with other calendar shouldn't be visible again"
        );
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
