import { contains } from "@web/../tests/web_test_helpers";
import { ResourceCalendarAttendance } from "../mock_server/mock_models/resource_calendar_attendance";
import {
    animationFrame,
    beforeEach,
    click,
    drag,
    expect,
    mockDate,
    test,
} from "@web/../lib/hoot/hoot";
import { mountView } from "@web/../tests/_framework/view_test_helpers";
import {
    clickEvent,
    findEvent,
    moveEventToAllDaySlot,
    moveEventToTime,
    resizeEventToTime,
    selectTimeRange,
} from "@web/../tests/views/calendar/calendar_test_helpers";
import { defineResourceModels } from "../resource_test_helpers";

defineResourceModels();
beforeEach(async () => {
    mockDate("2025-01-01 10:00:00");
});

test.tags("desktop");
test(`resource calendar week multi select creation`, async () => {
    await mountView({
        resModel: "resource.calendar.attendance",
        type: "calendar",
    });
    const { drop, moveTo } = await drag(".fc-day[data-date='2025-01-01'] .fc-daygrid-day-events");
    await moveTo(".fc-day[data-date='2025-01-03'] .fc-daygrid-day-events");
    await animationFrame();
    await drop();
    await animationFrame();
    await click(".o_multi_selection_buttons .btn:contains(Add)");
    await animationFrame();
    await contains("div[name=duration_hours] input").fill(2);
    await animationFrame();
    await click(".o_multi_create_popover .popover-footer .btn:contains(Add)");
    await animationFrame();
    expect(".fc-daygrid-event").toHaveCount(3);

    await clickEvent(1);
    await animationFrame();
    expect("div[name=duration_hours] input").toHaveValue(2, {
        message: "An attendance with a duration_hours of 2 hours should be created",
    });
    expect("div[name=hour_from] input").toHaveValue(0, {
        message: "As the attendance is duration_based (allDay) hour_from should be 0",
    });
    expect("div[name=hour_to] input").toHaveValue(0, {
        message: "As the attendance is duration_based (allDay) hour_to should be 0",
    });
});

test.tags("desktop");
test(`resource calendar week daygrid to timegrid`, async () => {
    ResourceCalendarAttendance._records.push({
        id: 1,
        calendar_id: 1,
        date: "2025-01-01",
        duration_hours: 2,
        duration_based: true,
    });
    await mountView({
        resModel: "resource.calendar.attendance",
        type: "calendar",
    });
    expect(".fc-timegrid-event").toHaveCount(0, {
        message: "No not duration_based attendance exists",
    });
    expect(".fc-daygrid-event").toHaveCount(1, {
        message: "The attendance duration_based should appears",
    });

    await moveEventToTime(1, "2025-01-01 10:00:00");
    await animationFrame();
    await clickEvent(1);
    await animationFrame();
    expect("div[name=duration_hours] input").toHaveValue(2, {
        message: "The duration_hours of the event should stay the same",
    });
    expect("div[name=hour_from] input").toHaveValue(10, {
        message: "As the attendance is moved to the timegrid, hour_from should be set",
    });
    expect("div[name=hour_to] input").toHaveValue(12, {
        message: "As the attendance is moved to the timegrid, hour_to should be set",
    });

    expect(".fc-timegrid-event").toHaveCount(1, {
        message: "The attendance should be in the timegrid after moving",
    });
    expect(".fc-daygrid-event").toHaveCount(0, {
        message: "No attendance should be in the daygrid after moving",
    });
});

test.tags("desktop");
test(`resource calendar week timegrid to daygrid`, async () => {
    ResourceCalendarAttendance._records.push({
        id: 1,
        calendar_id: 1,
        date: "2025-01-01",
        hour_from: 10,
        hour_to: 12,
        duration_hours: 2,
        duration_based: false,
    });
    await mountView({
        resModel: "resource.calendar.attendance",
        type: "calendar",
    });

    await moveEventToAllDaySlot(1, "2025-01-01");
    await animationFrame();
    await clickEvent(1);
    await animationFrame();
    expect("div[name=duration_hours] input").toHaveValue(2, {
        message: "The duration_hours of the event should stay the same",
    });
    expect("div[name=hour_from] input").toHaveValue(0, {
        message: "As the attendance is moved to the daygrid, hour_from should not be set",
    });
    expect("div[name=hour_to] input").toHaveValue(0, {
        message: "As the attendance is moved to the daygrid, hour_to should not be set",
    });

    expect(".fc-timegrid-event").toHaveCount(0, {
        message: "No attendance should be in the timegrid after moving",
    });
    expect(".fc-daygrid-event").toHaveCount(1, {
        message: "The attendance should be in the daygrid after moving",
    });
});

test.tags("desktop");
test(`resource calendar week simple click on empty slot in timegrid`, async () => {
    await mountView({
        resModel: "resource.calendar.attendance",
        type: "calendar",
    });
    await click(".fc-timegrid-slot-lane[data-time='10:00:00']");
    await animationFrame();
    expect("div[name=hour_from] input").toHaveValue(10, { message: "Click origin" });
    expect("div[name=hour_to] input").toHaveValue(11, {
        message: "It should create a record of 1 hour by default",
    });
    await click(".popover-footer .btn:contains('Save')");
    await animationFrame();
    expect(findEvent(1)).toBeDisplayed({ message: "The attendance should be saved" });
});

test.tags("desktop");
test(`resource calendar week move and resize event`, async () => {
    ResourceCalendarAttendance._records.push({
        id: 1,
        calendar_id: 1,
        date: "2025-01-01",
        hour_from: 10,
        hour_to: 12,
        duration_based: false,
    });
    await mountView({
        resModel: "resource.calendar.attendance",
        type: "calendar",
    });
    await moveEventToTime(1, "2025-01-01 12:00:00");
    await resizeEventToTime(1, "2025-01-01 16:00:00");
    await clickEvent(1);
    await animationFrame();
    expect("div[name=hour_from] input").toHaveValue(12);
    expect("div[name=hour_to] input").toHaveValue(16);
});

test.tags("desktop");
test(`resource calendar week select in timegrid`, async () => {
    await mountView({
        resModel: "resource.calendar.attendance",
        type: "calendar",
    });
    await selectTimeRange("2025-01-01 10:00:00", "2025-01-01 12:00:00");
    await animationFrame();
    expect("div[name=hour_from] input").toHaveValue(10);
    expect("div[name=hour_to] input").toHaveValue(12);
});
