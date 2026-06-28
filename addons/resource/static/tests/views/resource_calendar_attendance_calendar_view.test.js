import { contains, findComponent, onRpc } from "@web/../tests/web_test_helpers";
import {
    animationFrame,
    beforeEach,
    click,
    drag,
    expect,
    mockDate,
    test,
} from "@web/../lib/hoot/hoot";
import { disableAnimations } from "@odoo/hoot-mock";
import { editSelectMenu, mountView } from "@web/../tests/_framework/view_test_helpers";
import {
    clickEvent,
    moveEventToTime,
    resizeEventToTime,
    selectTimeRange,
} from "@web/../tests/views/calendar/calendar_test_helpers";
import { CalendarController } from "@web/views/calendar/calendar_controller";
import { defineResourceModels } from "../resource_test_helpers";
import { ResourceCalendarAttendance } from "../mock_server/mock_models/resource_calendar_attendance";
import { waitFor } from "@odoo/hoot-dom";

defineResourceModels();
beforeEach(async () => {
    mockDate("2025-01-01 10:00:00");
    disableAnimations();
});

test.tags("desktop");
test(`resource calendar week multi select creation`, async () => {
    onRpc("resource.calendar.attendance", "create", ({ args }) => {
        expect.step("create");
        const records = args[0];
        expect(records).toHaveLength(3);
        expect(records.map((r) => r.date)).toEqual(["2025-01-01", "2025-01-02", "2025-01-03"]);
        for (const rec of records) {
            expect(rec.duration_hours).toBe(2);
            expect(rec.hour_from).toBe(0);
            expect(rec.hour_to).toBe(0);
        }
    });
    await mountView({
        resModel: "resource.calendar.attendance",
        type: "calendar",
        context: { default_calendar_id: 1 },
    });
    await animationFrame();
    const { drop, moveTo } = await drag(".fc-day[data-date='2025-01-01'] .fc-daygrid-day-events");
    await moveTo(".fc-day[data-date='2025-01-03'] .fc-daygrid-day-events");
    await animationFrame();
    await drop();
    await animationFrame();
    expect(".o_multi_selection_buttons").toBeDisplayed({
        message: "Dragging across days should open the multi-selection toolbar",
    });
    await click(".o_multi_selection_buttons .btn:contains(Add)");
    await animationFrame();
    expect(".o_multi_create_popover").toBeDisplayed({
        message: "Clicking Add should open the multi-create popover",
    });
    await contains("div[name=duration_hours] input").fill(2);
    await animationFrame();
    await click(".o_multi_create_popover .popover-footer .btn:contains(Add)");
    await animationFrame();
    expect.verifySteps(["create"]);
});

test.tags("desktop");
test(`resource calendar multi create strips recurrency_until and uses per-day date`, async () => {
    onRpc("resource.calendar.attendance", "create", ({ args }) => {
        expect.step("create");
        const records = args[0];
        expect(records).toHaveLength(3);
        expect(records.map((r) => r.date)).toEqual(["2025-01-01", "2025-01-02", "2025-01-03"]);
        for (const rec of records) {
            expect(rec.recurrency).toBe(true);
            expect(rec.recurrency_end_type).toBe("forever");
            expect("recurrency_until" in rec).toBe(false, {
                message:
                    "recurrency_until must be stripped so the server precompute runs per record",
            });
        }
    });
    await mountView({
        resModel: "resource.calendar.attendance",
        type: "calendar",
        context: { default_calendar_id: 1 },
    });
    await animationFrame();
    const { drop, moveTo } = await drag(".fc-day[data-date='2025-01-01'] .fc-daygrid-day-events");
    await moveTo(".fc-day[data-date='2025-01-03'] .fc-daygrid-day-events");
    await animationFrame();
    await drop();
    await animationFrame();
    await click(".o_multi_selection_buttons .btn:contains(Add)");
    await animationFrame();
    await waitFor(".o_multi_create_popover");
    await click(".o_multi_create_popover div[name=recurrency] input");
    await animationFrame();
    await editSelectMenu(".o_multi_create_popover div[name=recurrency_type] input", {
        value: "Days",
    });
    await editSelectMenu(".o_multi_create_popover div[name=recurrency_end_type] input", {
        value: "Forever",
    });
    await animationFrame();
    await click(".o_multi_create_popover .popover-footer .btn:contains(Add)");
    await animationFrame();
    expect.verifySteps(["create"]);
});

test.tags("desktop");
test(`resource calendar week daygrid to timegrid`, async () => {
    ResourceCalendarAttendance._records = [
        {
            id: 1,
            calendar_id: 1,
            date: "2025-01-01",
            hour_from: 0,
            hour_to: 0,
            duration_hours: 2,
            duration_based: true,
        },
    ];
    onRpc("resource.calendar.attendance", "write", ({ args }) => {
        expect.step("write");
        const [ids, values] = args;
        expect(ids).toEqual([1]);
        expect(values.duration_based).toBe(false);
        expect(values.hour_from).toBe(10);
        expect(values.hour_to).toBe(12);
    });
    const view = await mountView({
        resModel: "resource.calendar.attendance",
        type: "calendar",
    });
    expect(".fc-timegrid-event").toHaveCount(0, {
        message: "No not duration_based attendance exists at mount time",
    });
    expect(".fc-daygrid-event").toHaveCount(1, {
        message: "The preloaded duration_based attendance should appear in daygrid",
    });

    const calendar = findComponent(view, (c) => c instanceof CalendarController);
    await calendar.model.updateRecord({
        id: 1,
        start: luxon.DateTime.local(2025, 1, 1, 10, 0),
        end: luxon.DateTime.local(2025, 1, 1, 12, 0),
        isAllDay: false,
    });
    expect.verifySteps(["write"]);
});

test.tags("desktop");
test(`resource calendar week timegrid to daygrid`, async () => {
    ResourceCalendarAttendance._records = [
        {
            id: 1,
            calendar_id: 1,
            date: "2025-01-01",
            hour_from: 10,
            hour_to: 12,
            duration_hours: 2,
            duration_based: false,
        },
    ];
    onRpc("resource.calendar.attendance", "write", ({ args }) => {
        expect.step("write");
        const [ids, values] = args;
        expect(ids).toEqual([1]);
        expect(values.duration_based).toBe(true);
        expect(values.hour_from).toBe(0);
        expect(values.hour_to).toBe(0);
    });
    const view = await mountView({
        resModel: "resource.calendar.attendance",
        type: "calendar",
    });
    expect(".fc-timegrid-event").toHaveCount(1, {
        message: "The preloaded time-based attendance should appear in timegrid",
    });
    expect(".fc-daygrid-event").toHaveCount(0, {
        message: "No duration_based attendance exists at mount time",
    });

    const calendar = findComponent(view, (c) => c instanceof CalendarController);
    await calendar.model.updateRecord({
        id: 1,
        start: luxon.DateTime.local(2025, 1, 1),
        end: luxon.DateTime.local(2025, 1, 1),
        isAllDay: true,
    });
    expect.verifySteps(["write"]);
});

test.tags("desktop");
test(`resource calendar week simple click on empty slot in timegrid`, async () => {
    onRpc("resource.calendar.attendance", "web_save", ({ args }) => {
        expect.step("create");
        const [record] = args[0];
        expect(record.hour_from).toBe(10);
        expect(record.hour_to).toBe(11);
        expect(record.date).toBe("2025-01-01");
    });
    await mountView({
        resModel: "resource.calendar.attendance",
        type: "calendar",
    });
    await animationFrame();
    await click(".fc-timegrid-slot-lane[data-time='10:00:00']");
    await animationFrame();
    await waitFor(".o_cw_popover");
    expect("div[name=hour_from] input").toHaveValue(10, { message: "Click origin" });
    expect("div[name=hour_to] input").toHaveValue(11, {
        message: "It should create a record of 1 hour by default",
    });
    await click(".popover-footer .btn:contains('Save')");
    await animationFrame();
    expect.verifySteps(["create"]);
});

test.tags("desktop");
test(`resource calendar week move and resize event`, async () => {
    ResourceCalendarAttendance._records = [
        {
            id: 1,
            calendar_id: 1,
            date: "2025-01-01",
            hour_from: 10,
            hour_to: 12,
            duration_hours: 2,
            duration_based: false,
        },
    ];
    onRpc("resource.calendar.attendance", "write", ({ args }) => {
        const [, values] = args;
        expect.step(`write:${values.hour_from}-${values.hour_to}`);
    });
    const view = await mountView({
        resModel: "resource.calendar.attendance",
        type: "calendar",
    });
    const calendar = findComponent(view, (c) => c instanceof CalendarController);

    await calendar.model.updateRecord({
        id: 1,
        start: luxon.DateTime.local(2025, 1, 1, 12, 0),
        end: luxon.DateTime.local(2025, 1, 1, 14, 0),
        isAllDay: false,
    });
    await calendar.model.updateRecord({
        id: 1,
        start: luxon.DateTime.local(2025, 1, 1, 10, 0),
        end: luxon.DateTime.local(2025, 1, 1, 16, 0),
        isAllDay: false,
    });
    expect.verifySteps(["write:12-14", "write:10-16"]);
});

test.tags("desktop");
test(`resource calendar week move recurrent event opens popover with multiple save options`, async () => {
    ResourceCalendarAttendance._records = [
        {
            id: 1,
            calendar_id: 1,
            date: "2025-01-01",
            hour_from: 10,
            hour_to: 12,
            duration_hours: 2,
            duration_based: false,
            recurrency: true,
            recurrency_interval: 1,
            recurrency_type: "weeks",
            recurrency_end_type: "forever",
        },
    ];
    await mountView({
        resModel: "resource.calendar.attendance",
        type: "calendar",
    });
    await animationFrame();
    await moveEventToTime(1, "2025-01-01 14:00:00");
    await animationFrame();
    await waitFor(".o_cw_popover");
    expect(".popover-footer .o-dropdown-caret:contains('Save')").toHaveCount(1, {
        message: "Save should be a dropdown (multiple options) for a recurrent record",
    });
    expect(".popover-footer .btn:contains('Discard')").toHaveCount(1, {
        message: "Discard button should be shown (record is dirty after the drag)",
    });
    await click(".popover-footer .o-dropdown-caret:contains('Save')");
    await animationFrame();
    expect(".o-dropdown-item").toHaveCount(2, {
        message: "Save dropdown should offer multiple options for a recurrent record",
    });
    await click(".popover-footer .btn:contains('Discard')");
    await animationFrame();
});

test.tags("desktop");
test(`resource calendar move recurrent occurrence "This event" sends original date as arg and moved date in changes`, async () => {
    ResourceCalendarAttendance._records = [
        {
            id: 1,
            calendar_id: 1,
            date: "2025-01-01",
            hour_from: 10,
            hour_to: 12,
            duration_hours: 2,
            duration_based: false,
            recurrency: true,
            recurrency_interval: 1,
            recurrency_type: "weeks",
            recurrency_end_type: "forever",
        },
    ];
    onRpc("resource.calendar.attendance", "create_ad_hoc", ({ args }) => {
        expect.step("create_ad_hoc");
        const [ids, occurrenceDate, changes] = args;
        expect(ids).toEqual([1]);
        expect(occurrenceDate).toBe("2025-01-01");
        expect(changes.date).toBe("2025-01-02");
        return 2;
    });
    await mountView({
        resModel: "resource.calendar.attendance",
        type: "calendar",
    });
    await animationFrame();
    await moveEventToTime(1, "2025-01-02 14:00:00");
    await animationFrame();
    await waitFor(".o_cw_popover");
    await click(".popover-footer .o-dropdown-caret:contains('Save')");
    await animationFrame();
    await click(".o-dropdown-item:contains('This event')");
    await animationFrame();
    expect.verifySteps(["create_ad_hoc"]);
});

test.tags("desktop");
test(`resource calendar move recurrent occurrence "This and following" sends original date as arg and moved date in changes`, async () => {
    ResourceCalendarAttendance._records = [
        {
            id: 1,
            calendar_id: 1,
            date: "2024-12-25",
            hour_from: 10,
            hour_to: 12,
            duration_hours: 2,
            duration_based: false,
            recurrency: true,
            recurrency_interval: 1,
            recurrency_type: "weeks",
            recurrency_end_type: "forever",
        },
    ];
    onRpc("resource.calendar", "get_attendances", function () {
        return this.env["resource.calendar.attendance"].search_read([]).map((rec) => ({
            ...rec,
            other_dates: ["2025-01-01"],
        }));
    });
    onRpc("resource.calendar.attendance", "create_new_recurrency", ({ args }) => {
        expect.step("create_new_recurrency");
        const [ids, occurrenceDate, changes] = args;
        expect(ids).toEqual([1]);
        expect(occurrenceDate).toBe("2025-01-01");
        expect(changes.date).toBe("2025-01-03");
        return 2;
    });
    await mountView({
        resModel: "resource.calendar.attendance",
        type: "calendar",
    });
    await animationFrame();
    await moveEventToTime(1, "2025-01-03 14:00:00");
    await animationFrame();
    await waitFor(".o_cw_popover");
    await click(".popover-footer .o-dropdown-caret:contains('Save')");
    await animationFrame();
    await click(".o-dropdown-item:contains('This and following events')");
    await animationFrame();
    expect.verifySteps(["create_new_recurrency"]);
});

test.tags("desktop");
test(`resource calendar click virtual recurrent occurrence (no drag) "This event" still sends clicked date in changes`, async () => {
    ResourceCalendarAttendance._records = [
        {
            id: 1,
            calendar_id: 1,
            date: "2024-12-25",
            hour_from: 10,
            hour_to: 12,
            duration_hours: 2,
            duration_based: false,
            recurrency: true,
            recurrency_interval: 1,
            recurrency_type: "weeks",
            recurrency_end_type: "forever",
        },
    ];
    onRpc("resource.calendar", "get_attendances", function () {
        return this.env["resource.calendar.attendance"].search_read([]).map((rec) => ({
            ...rec,
            other_dates: ["2025-01-01"],
        }));
    });
    onRpc("resource.calendar.attendance", "create_ad_hoc", ({ args }) => {
        expect.step("create_ad_hoc");
        const [ids, occurrenceDate, changes] = args;
        expect(ids).toEqual([1]);
        expect(occurrenceDate).toBe("2025-01-01");
        expect(changes.date).toBe("2025-01-01");
        return 2;
    });
    await mountView({
        resModel: "resource.calendar.attendance",
        type: "calendar",
    });
    await animationFrame();
    await clickEvent(1);
    await waitFor(".o_cw_popover");
    await click(".popover-footer .o-dropdown-caret:contains('Save')");
    await animationFrame();
    await click(".o-dropdown-item:contains('This event')");
    await animationFrame();
    expect.verifySteps(["create_ad_hoc"]);
});

test.tags("desktop");
test(`resource calendar click virtual recurrent occurrence (no drag) "This and following" still sends clicked date in changes`, async () => {
    ResourceCalendarAttendance._records = [
        {
            id: 1,
            calendar_id: 1,
            date: "2024-12-25",
            hour_from: 10,
            hour_to: 12,
            duration_hours: 2,
            duration_based: false,
            recurrency: true,
            recurrency_interval: 1,
            recurrency_type: "weeks",
            recurrency_end_type: "forever",
        },
    ];
    onRpc("resource.calendar", "get_attendances", function () {
        return this.env["resource.calendar.attendance"].search_read([]).map((rec) => ({
            ...rec,
            other_dates: ["2025-01-01"],
        }));
    });
    onRpc("resource.calendar.attendance", "create_new_recurrency", ({ args }) => {
        expect.step("create_new_recurrency");
        const [ids, occurrenceDate, changes] = args;
        expect(ids).toEqual([1]);
        expect(occurrenceDate).toBe("2025-01-01");
        expect(changes.date).toBe("2025-01-01");
        return 2;
    });
    await mountView({
        resModel: "resource.calendar.attendance",
        type: "calendar",
    });
    await animationFrame();
    await clickEvent(1);
    await waitFor(".o_cw_popover");
    await click(".popover-footer .o-dropdown-caret:contains('Save')");
    await animationFrame();
    await click(".o-dropdown-item:contains('This and following events')");
    await animationFrame();
    expect.verifySteps(["create_new_recurrency"]);
});

test.tags("desktop");
test(`resource calendar drag source recurrent event "All events" writes the moved date`, async () => {
    ResourceCalendarAttendance._records = [
        {
            id: 1,
            calendar_id: 1,
            date: "2025-01-01",
            hour_from: 10,
            hour_to: 12,
            duration_hours: 2,
            duration_based: false,
            recurrency: true,
            recurrency_interval: 1,
            recurrency_type: "weeks",
            recurrency_end_type: "forever",
        },
    ];
    onRpc("resource.calendar.attendance", "web_save", ({ args }) => {
        expect.step("web_save");
        const [ids, values] = args;
        expect(ids).toEqual([1]);
        expect(values.date).toBe("2025-01-02");
    });
    await mountView({
        resModel: "resource.calendar.attendance",
        type: "calendar",
    });
    await animationFrame();
    await moveEventToTime(1, "2025-01-02 14:00:00");
    await animationFrame();
    await waitFor(".o_cw_popover");
    await click(".popover-footer .o-dropdown-caret:contains('Save')");
    await animationFrame();
    await click(".o-dropdown-item:contains('All events')");
    await animationFrame();
    expect.verifySteps(["web_save"]);
});

test.tags("desktop");
test(`resource calendar modify virtual occurrence (no drag) "All events" does not write date`, async () => {
    ResourceCalendarAttendance._records = [
        {
            id: 1,
            calendar_id: 1,
            date: "2024-12-25",
            hour_from: 10,
            hour_to: 12,
            duration_hours: 2,
            duration_based: false,
            recurrency: true,
            recurrency_interval: 1,
            recurrency_type: "weeks",
            recurrency_end_type: "forever",
        },
    ];
    onRpc("resource.calendar", "get_attendances", function () {
        return this.env["resource.calendar.attendance"].search_read([]).map((rec) => ({
            ...rec,
            other_dates: ["2025-01-01"],
        }));
    });
    onRpc("resource.calendar.attendance", "web_save", ({ args }) => {
        expect.step("web_save");
        const [ids, values] = args;
        expect(ids).toEqual([1]);
        expect("date" in values).toBe(false, {
            message: "date must not be written for all events if it's not the original one",
        });
    });
    await mountView({
        resModel: "resource.calendar.attendance",
        type: "calendar",
    });
    await animationFrame();
    await clickEvent(1);
    await waitFor(".o_cw_popover");
    await contains("div[name=hour_from] input").edit(9);
    await animationFrame();
    await click(".popover-footer .o-dropdown-caret:contains('Save')");
    await animationFrame();
    await click(".o-dropdown-item:contains('All events')");
    await animationFrame();
    expect.verifySteps(["web_save"]);
});

test.tags("desktop");
test(`resource calendar week resize recurrent event opens popover with multiple save options`, async () => {
    ResourceCalendarAttendance._records = [
        {
            id: 1,
            calendar_id: 1,
            date: "2025-01-01",
            hour_from: 10,
            hour_to: 12,
            duration_hours: 2,
            duration_based: false,
            recurrency: true,
            recurrency_interval: 1,
            recurrency_type: "weeks",
            recurrency_end_type: "forever",
        },
    ];
    await mountView({
        resModel: "resource.calendar.attendance",
        type: "calendar",
    });
    await animationFrame();
    await resizeEventToTime(1, "2025-01-01 16:00:00");
    await animationFrame();
    await waitFor(".o_cw_popover");
    expect(".popover-footer .o-dropdown-caret:contains('Save')").toHaveCount(1, {
        message: "Save should be a dropdown (multiple options) for a recurrent record",
    });
    expect(".popover-footer .btn:contains('Discard')").toHaveCount(1, {
        message: "Discard button should be shown (record is dirty after the drag)",
    });
    await click(".popover-footer .o-dropdown-caret:contains('Save')");
    await animationFrame();
    expect(".o-dropdown-item").toHaveCount(2, {
        message: "Save dropdown should offer multiple options for a recurrent record",
    });
    await click(".popover-footer .btn:contains('Discard')");
    await animationFrame();
});

test.tags("desktop");
test(`resource calendar week select in timegrid`, async () => {
    await mountView({
        resModel: "resource.calendar.attendance",
        type: "calendar",
    });
    await animationFrame();
    await selectTimeRange("2025-01-01 10:00:00", "2025-01-01 12:00:00");
    await animationFrame();
    await waitFor(".o_cw_popover");
    expect("div[name=hour_from] input").toHaveValue(10);
    expect("div[name=hour_to] input").toHaveValue(12);
    await click(".popover-footer .btn:contains('Discard')");
    await animationFrame();
});
