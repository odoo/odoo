import { EventBus } from "@odoo/owl";
import { beforeEach, expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame, tick } from "@odoo/hoot-mock";
import { defineMailModels, startServer } from "@mail/../tests/mail_test_helpers";
import {
    contains,
    getService,
    mockService,
    mountWithCleanup,
    onRpc,
    serverState,
} from "@web/../tests/web_test_helpers";
import { WebClient } from "@web/webclient/webclient";

let employeeData;

defineMailModels();

beforeEach(async () => {
    await startServer();
    employeeData = {
        id: serverState.userId,
        name: "Mitchell Admin",
        display_systray: true,
        attendance_state: "checked_out",
        attendance_based: true,
        working_now: true,
        hours_today: 0,
        today_attendance_ids: [],
        last_attendance_worked_hours: 0,
    };

    mockService("lazy_session", {
        getValue(key, callback) {
            callback(key === "attendance_user_data" ? employeeData : undefined);
        },
    });
    mockService("presence", {
        bus: new EventBus(),
        isOdooFocused: () => true,
    });

    onRpc("/hr_attendance/attendance_user_data", () => employeeData);
});

test.tags("desktop");
test("Attendance-based checked-out users get a sticky attendance reminder after activity", async () => {
    await mountWithCleanup(WebClient);

    getService("presence").bus.trigger("presence");
    await advanceTime(2 * 60 * 1000 + 1);
    await animationFrame();

    expect(".o_attendance_reminder_popover").toHaveText(/Don't forget to check in/);
    await contains("div.o_menu_systray").click();
    await tick();
    expect(".o_attendance_reminder_popover").toHaveText(/Don't forget to check in/);
    await contains(".o_attendance_reminder_popover button").click();
    await tick();
    expect(".o_attendance_reminder_popover").toHaveCount(0);
});

test.tags("desktop");
test("Attendance reminder is skipped when the employee is not attendance-based", async () => {
    employeeData.attendance_based = false;
    await mountWithCleanup(WebClient);

    getService("presence").bus.trigger("presence");
    await advanceTime(2 * 60 * 1000 + 1);
    await tick();

    expect(".o_attendance_reminder_popover").toHaveCount(0);
});

test.tags("desktop");
test("Attendance reminder is skipped when the employee is off-hours", async () => {
    employeeData.working_now = false;
    await mountWithCleanup(WebClient);

    getService("presence").bus.trigger("presence");
    await advanceTime(2 * 60 * 1000 + 1);
    await tick();

    expect(".o_attendance_reminder_popover").toHaveCount(0);
});

test.tags("desktop");
test("Attendance reminder refreshes the employee state before opening", async () => {
    await mountWithCleanup(WebClient);

    getService("presence").bus.trigger("presence");
    employeeData.attendance_state = "checked_in";
    await advanceTime(2 * 60 * 1000 + 1);
    await tick();

    expect(".o_attendance_reminder_popover").toHaveCount(0);
});

test.tags("desktop");
test("Attendance reminder is shown only once per page session", async () => {
    await mountWithCleanup(WebClient);

    getService("presence").bus.trigger("presence");
    await advanceTime(2 * 60 * 1000 + 1);
    await animationFrame();

    expect(".o_attendance_reminder_popover").toHaveText(/Don't forget to check in/);
    await contains(".o_attendance_reminder_popover button").click();
    await tick();
    expect(".o_attendance_reminder_popover").toHaveCount(0);

    getService("presence").bus.trigger("presence");
    await advanceTime(2 * 60 * 1000 + 1);
    await tick();

    expect(".o_attendance_reminder_popover").toHaveCount(0);
});
