/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { CalendarCommonRenderer } from "@web/views/calendar/calendar_common/calendar_common_renderer";
import { CalendarYearRenderer } from "@web/views/calendar/calendar_year/calendar_year_renderer";
import { click, getFixture, nextTick, patchDate, patchWithCleanup } from "../../helpers/utils";
import { changeScale, clickEvent, toggleSectionFilter } from "../../views/calendar/helpers";
import { makeView, setupViewRegistries } from "../../views/helpers";
import { tap, swipeRight, tapAndMove } from "../helpers";

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
            target.querySelector(
                ".o_cp_bottom_left .o_calendar_buttons .o_calendar_scale_buttons + button.o_cp_today_button"
            ),
            "today button should be visible near the calendar buttons (bottom left corner)"
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

    QUnit.test("calendar: today button", async function (assert) {
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `<calendar mode="day" date_start="start" date_stop="stop"></calendar>`,
        });
        assert.equal(target.querySelector(".fc-day-header[data-date]").dataset.date, "2016-12-12");

        // Swipe right
        await swipeRight(target, ".o_calendar_widget");
        assert.equal(target.querySelector(".fc-day-header[data-date]").dataset.date, "2016-12-11");

        await click(target, ".o_calendar_button_today");
        assert.equal(target.querySelector(".fc-day-header[data-date]").dataset.date, "2016-12-12");
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
        assert.containsOnce(target, ".o_calendar_renderer");

        // Toggle the other calendar panel should hide the calendar view and show the sidebar
        await click(target, ".o_other_calendar_panel");
        assert.containsOnce(target, ".o_calendar_sidebar");
        assert.containsNone(target, ".o_calendar_renderer");
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
        assert.containsOnce(target, ".o_calendar_renderer");
    });

    QUnit.test('calendar: tap on "Free Zone" opens quick create', async function (assert) {
        patchWithCleanup(CalendarCommonRenderer.prototype, {
            onDateClick(...args) {
                assert.step("dateClick");
                return this._super(...args);
            },
            onSelect(...args) {
                assert.step("select");
                return this._super(...args);
            },
        });

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `<calendar mode="day" date_start="start" date_stop="stop"/>`,
        });

        // Simulate a "TAP" (touch)
        await tap(
            target,
            ".fc-time-grid .fc-minor[data-time='00:30:00'] .fc-widget-content:last-child"
        );
        await nextTick();

        // should open a Quick create modal view in mobile on short tap
        assert.containsOnce(target, ".modal");
        assert.verifySteps(["dateClick"]);
    });

    QUnit.test('calendar: select range on "Free Zone" opens quick create', async function (assert) {
        patchWithCleanup(CalendarCommonRenderer.prototype, {
            get options() {
                return Object.assign({}, this._super(), {
                    selectLongPressDelay: 0,
                });
            },
            onDateClick(info) {
                assert.step("dateClick");
                return this._super(info);
            },
            onSelect(info) {
                assert.step("select");
                const { startStr, endStr } = info;
                assert.equal(startStr, "2016-12-12T01:00:00+01:00");
                assert.equal(endStr, "2016-12-12T02:00:00+01:00");
                return this._super(info);
            },
        });

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `<calendar mode="day" date_start="start" date_stop="stop"/>`,
        });

        // Simulate a "TAP" (touch)
        await tapAndMove(
            target,
            ".fc-time-grid [data-time='01:00:00'] .fc-widget-content:last-child",
            ".fc-time-grid [data-time='02:00:00'] .fc-widget-content:last-child",
            { start: "top", end: "bottom" }
        );
        await nextTick();

        // should open a Quick create modal view in mobile on short tap
        assert.containsOnce(target, ".modal");
        assert.verifySteps(["select"]);
    });

    QUnit.test("calendar (year): select date range opens quick create", async function (assert) {
        patchWithCleanup(CalendarYearRenderer.prototype, {
            get options() {
                return Object.assign({}, this._super(), {
                    longPressDelay: 0,
                    selectLongPressDelay: 0,
                });
            },
            onDateClick(info) {
                assert.step("dateClick");
                return this._super(info);
            },
            onSelect(info) {
                assert.step("select");
                const { startStr, endStr } = info;
                assert.equal(startStr, "2016-02-02");
                assert.equal(endStr, "2016-02-06"); // end date is exclusive
                return this._super(info);
            },
        });

        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `<calendar mode="year" date_start="start" date_stop="stop"/>`,
        });

        // Tap on a date
        await tapAndMove(
            target,
            ".fc-day-top[data-date='2016-02-02']",
            ".fc-day-top[data-date='2016-02-05']"
        );
        await nextTick();

        // should open a Quick create modal view in mobile on short tap
        assert.containsOnce(target, ".modal");
        assert.verifySteps(["select"]);
    });

    QUnit.test("calendar (month/year): tap on date switch to day scale", async function (assert) {
        await makeView({
            type: "calendar",
            resModel: "event",
            serverData,
            arch: `<calendar mode="year" date_start="start" date_stop="stop"/>`,
        });

        // Should display year view
        assert.containsOnce(target, ".fc-dayGridYear-view");
        assert.containsN(target, ".fc-month-container", 12);
        assert.equal(target.querySelector(".breadcrumb-item").textContent, "undefined (2016)");

        // Tap on a date
        await tap(target, ".fc-day-top[data-date='2016-02-05']");
        await nextTick(); // switch renderer
        await nextTick(); // await breadcrumb update

        // Should display day view
        assert.containsNone(target, ".fc-dayGridYear-view");
        assert.containsOnce(target, ".fc-timeGridDay-view");
        assert.equal(
            target.querySelector(".breadcrumb-item").textContent,
            "undefined (February 5, 2016)"
        );

        // Change scale to month
        await changeScale(target, "month");
        assert.containsNone(target, ".fc-timeGridDay-view");
        assert.containsOnce(target, ".fc-dayGridMonth-view");
        assert.equal(
            target.querySelector(".breadcrumb-item").textContent,
            "undefined (February 2016)"
        );

        // Tap on a date
        await tap(target, ".fc-day-top[data-date='2016-02-10']");
        await nextTick(); // await breadcrumb update

        assert.containsNone(target, ".fc-dayGridMonth-view");
        assert.containsOnce(target, ".fc-timeGridDay-view");
        assert.equal(
            target.querySelector(".breadcrumb-item").textContent,
            "undefined (February 10, 2016)"
        );
    });
});
