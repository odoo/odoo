import { expect, test } from "@odoo/hoot";
import { ActivityMenu } from "@hr_attendance/components/attendance_menu/attendance_menu";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import {
    mockService,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

defineMailModels();

const EMPLOYEE = {
    id: 1,
    hours_today: 4,
    hours_previously_today: 0,
    last_attendance_worked_hours: 4,
    last_check_in: "2026-01-01 08:00:00",
    attendance_state: "checked_in",
    display_systray: true,
    device_tracking_enabled: true,
};

/** Seed the systray with an employee, the way the lazy session does. */
function mockEmployee(overrides = {}) {
    const employee = { ...EMPLOYEE, ...overrides };
    mockService("lazy_session", {
        getValue(key, callback) {
            callback?.(employee);
            return Promise.resolve(employee);
        },
    });
    return employee;
}

/** Capture what the component asks the dialog service to show. */
function captureConfirmation() {
    const captured = {};
    mockService("dialog", {
        add(_component, props) {
            expect.step("asked");
            Object.assign(captured, props);
            return () => {};
        },
    });
    return captured;
}

test.tags("desktop");
test("location refused while tracking: ask before recording the attendance", async () => {
    mockEmployee();
    const dialog = captureConfirmation();
    patchWithCleanup(navigator, {
        geolocation: {
            getCurrentPosition(_onSuccess, onError) {
                onError({ code: 1, message: "User denied Geolocation" });
            },
        },
    });
    onRpc("/hr_attendance/systray_check_in_out", () => {
        expect.step("checked in/out");
        return EMPLOYEE;
    });

    const menu = await mountWithCleanup(ActivityMenu);
    await menu.signInOut();
    expect.verifySteps(["asked"], {
        message: "nothing is recorded until the employee agrees",
    });

    await dialog.confirm();
    expect.verifySteps(["checked in/out"]);
});

test.tags("desktop");
test("no geolocation at all while tracking: ask too", async () => {
    mockEmployee();
    const dialog = captureConfirmation();
    patchWithCleanup(navigator, { geolocation: undefined });
    onRpc("/hr_attendance/systray_check_in_out", () => {
        expect.step("checked in/out");
        return EMPLOYEE;
    });

    const menu = await mountWithCleanup(ActivityMenu);
    await menu.signInOut();
    expect.verifySteps(["asked"]);

    await dialog.confirm();
    expect.verifySteps(["checked in/out"]);
});

test.tags("desktop");
test("tracking off: no question, the attendance is recorded straight away", async () => {
    mockEmployee({ device_tracking_enabled: false });
    captureConfirmation();
    onRpc("/hr_attendance/systray_check_in_out", () => {
        expect.step("checked in/out");
        return { ...EMPLOYEE, device_tracking_enabled: false };
    });

    const menu = await mountWithCleanup(ActivityMenu);
    await menu.signInOut();
    expect.verifySteps(["checked in/out"]);
});
