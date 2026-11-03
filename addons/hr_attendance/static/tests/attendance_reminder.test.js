import { beforeEach, expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame, mockDate } from "@odoo/hoot-mock";
import { ActivityMenu } from "@hr_attendance/components/attendance_menu/attendance_menu";
import { defineHrModels } from "@hr/../tests/hr_test_helpers";
import { contains, mockService, mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";

defineHrModels();

const sessionData = {};

beforeEach(() => {
    mockDate("2026-09-20 09:00:00");
    Object.assign(sessionData, {
        attendance_check_in_ability: true,
        attendance_state: "checked_out",
        attendance_based: true,
    });
    mockService("lazy_session", () => ({
        getValue: (key, callback) => callback(sessionData[key]),
    }));
});

test("clicking the reminder opens attendance and dismisses it for today", async () => {
    onRpc("/hr_attendance/attendance_user_data", () => ({
        id: 1,
        attendance_state: "checked_out",
        today_attendance_ids: [],
    }));
    await mountWithCleanup(ActivityMenu);
    await advanceTime(119000);
    expect(".o_hr_reminder_popover").toHaveCount(0);
    await advanceTime(1000);
    await animationFrame();
    expect(".o_hr_reminder_popover span").toHaveText(
        "Looks like you're working. Don't forget to check in."
    );
    await advanceTime(60000);
    expect(".o_hr_reminder_popover").toHaveCount(1);

    await contains(".o_hr_reminder_popover button").click();
    expect(".o_hr_reminder_popover").toHaveCount(0);
    expect(".o_wrap_btn_sign_out button").toHaveText("Check in");
    await mountWithCleanup(ActivityMenu);
    await advanceTime(120000);
    await animationFrame();
    expect(".o_hr_reminder_popover").toHaveCount(0);

    mockDate("2026-09-21 09:00:00");
    await mountWithCleanup(ActivityMenu);
    await advanceTime(120000);
    await animationFrame();
    expect(".o_hr_reminder_popover span").toHaveText(
        "Looks like you're working. Don't forget to check in."
    );
});

test("no reminder for checked-in or non-attendance-based employees", async () => {
    for (const data of [
        { attendance_based: false, attendance_state: "checked_out" },
        { attendance_based: true, attendance_state: "checked_in" },
    ]) {
        Object.assign(sessionData, data);
        await mountWithCleanup(ActivityMenu);
        await advanceTime(120000);
        await animationFrame();
        expect(".o_hr_reminder_popover").toHaveCount(0);
    }
});
