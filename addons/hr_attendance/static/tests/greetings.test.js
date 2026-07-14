import { beforeEach, expect, test } from "@odoo/hoot";
import { BreakDurationDialog } from "@hr_attendance/components/break_duration_dialog/break_duration_dialog";
import { KioskGreetings } from "@hr_attendance/components/greetings/greetings";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import {
    assignDialogTestEnv,
    contains,
    makeTestApp,
    mountWithCleanup,
} from "@web/../tests/web_test_helpers";

defineMailModels();

beforeEach(async () => {
    assignDialogTestEnv();
    await makeTestApp();
});

function getEmployeeData(attendance, breakManagementEnabled = false) {
    return {
        attendance,
        break_management_enabled: breakManagementEnabled,
        display_overtime: false,
        employee_avatar: "",
        employee_name: "Mitchell Admin",
        hours_today: 2,
        is_employee_single_checkin: false,
        kiosk_delay: 60_000,
    };
}

test("check-in greeting displays the status and returns to the kiosk", async () => {
    await mountWithCleanup(KioskGreetings, {
        props: {
            employeeData: getEmployeeData({
                check_in: "2026-07-21 09:30:00",
                check_out: false,
            }),
            kioskReturn: () => expect.step("return"),
        },
    });

    expect(".o_hr_attendance_kiosk_card").toHaveText(/Welcome/);
    expect(".o_hr_attendance_kiosk_card").toHaveText(/Checked in at/);
    expect("button").not.toHaveText("Add my break times");
    await contains(".o_hr_kiosk_mode_bottom button").click();

    expect.verifySteps(["return"]);
});

test("break duration dialog validates and submits whole minutes", async () => {
    await mountWithCleanup(BreakDurationDialog, {
        props: {
            employeeName: "Mitchell Admin",
            onConfirm: (minutes) => expect.step(`confirmed ${minutes}`),
            close: () => expect.step("closed"),
        },
        noMainContainer: true,
    });

    expect("label[for='o_break_duration_minutes']").toHaveCount(1);
    await contains("#o_break_duration_minutes").edit("-1", { instantly: true });
    await contains(".modal-footer .btn-primary").click();

    expect.verifySteps([]);
    expect(".modal").toHaveCount(1);

    await contains("#o_break_duration_minutes").edit("10");
    await contains(".modal-footer .btn-primary").click();

    expect.verifySteps(["confirmed 10", "closed"]);
});

test("checkout greeting can continue to break entry", async () => {
    await mountWithCleanup(KioskGreetings, {
        props: {
            employeeData: getEmployeeData(
                {
                    check_in: "2026-07-21 09:30:00",
                    check_out: "2026-07-21 11:30:00",
                },
                true
            ),
            kioskContinueBreak: () => expect.step("continue break"),
            kioskReturn: () => expect.step("unexpected return"),
        },
    });

    expect(".o_hr_attendance_kiosk_card").toHaveText(/Goodbye/);
    expect(".o_hr_attendance_kiosk_card").toHaveText(/Checked out at/);
    await contains("button", { text: "Add my break times" }).click();

    expect.verifySteps(["continue break"]);
});
