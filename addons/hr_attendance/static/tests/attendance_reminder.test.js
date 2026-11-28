import { beforeEach, expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame, mockDate } from "@odoo/hoot-mock";
import { ActivityMenu } from "@hr_attendance/components/attendance_menu/attendance_menu";
import { defineHrModels } from "@hr/../tests/hr_test_helpers";
import { contains, mockService, mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { user } from "@web/core/user";

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
    expect(".o_hr_reminder_popover button").not.toBeFocused();
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

test("clicking the systray closes the reminder", async () => {
    onRpc("/hr_attendance/attendance_user_data", () => ({
        id: 1,
        attendance_state: "checked_out",
        today_attendance_ids: [],
    }));
    await mountWithCleanup(ActivityMenu);
    await advanceTime(120000);
    await animationFrame();
    expect(".o_hr_reminder_popover").toHaveCount(1);

    await contains("button:has(i[aria-label='Attendance'])").click();
    expect(".o_hr_reminder_popover").toHaveCount(0);
    expect(".o_wrap_btn_sign_out button").toHaveText("Check in");
    await mountWithCleanup(ActivityMenu);
    await advanceTime(120000);
    await animationFrame();
    expect(".o_hr_reminder_popover").toHaveCount(0);
});

test("the close button dismisses the reminder for today without opening the menu", async () => {
    await mountWithCleanup(ActivityMenu);
    await advanceTime(120000);
    await animationFrame();
    await contains(".o_hr_reminder_popover button[aria-label='Close']").click();
    expect(".o_hr_reminder_popover").toHaveCount(0);
    expect(".o-dropdown--menu").toHaveCount(0);
    await mountWithCleanup(ActivityMenu);
    await advanceTime(120000);
    await animationFrame();
    expect(".o_hr_reminder_popover").toHaveCount(0);
});

test("no reminder while the attendance menu is open", async () => {
    onRpc("/hr_attendance/attendance_user_data", () => ({
        id: 1,
        attendance_state: "checked_out",
        today_attendance_ids: [],
    }));
    await mountWithCleanup(ActivityMenu);
    await contains("button:has(i[aria-label='Attendance'])").click();
    await advanceTime(120000);
    await animationFrame();
    expect(".o_hr_reminder_popover").toHaveCount(0);
});

test("closing the reminder in another tab closes it here", async () => {
    await mountWithCleanup(ActivityMenu);
    await advanceTime(120000);
    await animationFrame();
    const key = `hr.reminder.${user.userId}`;

    window.dispatchEvent(new StorageEvent("storage", { key, newValue: null }));
    await advanceTime(120000);
    await animationFrame();
    expect(".o_hr_reminder_popover").toHaveCount(1);

    window.dispatchEvent(new StorageEvent("storage", { key, newValue: "2026-09-20" }));
    await animationFrame();
    expect(".o_hr_reminder_popover").toHaveCount(0);
});

test("checking out in another tab shows the reminder here too", async () => {
    const key = `hr.reminder.${user.userId}`;
    localStorage.setItem(key, "2026-09-20");
    await mountWithCleanup(ActivityMenu);
    await advanceTime(120000);
    await animationFrame();
    expect(".o_hr_reminder_popover").toHaveCount(0);

    localStorage.removeItem(key);
    await advanceTime(119000);
    expect(".o_hr_reminder_popover").toHaveCount(0);
    await advanceTime(1000);
    await animationFrame();
    expect(".o_hr_reminder_popover").toHaveCount(1);
});

test("checking in prevents the reminder in the other tabs", async () => {
    onRpc("/hr_attendance/attendance_user_data", () => ({
        id: 1,
        attendance_state: "checked_out",
        today_attendance_ids: [],
    }));
    onRpc("/hr_attendance/systray_check_in_out", () => ({
        id: 1,
        attendance_state: "checked_in",
        today_attendance_ids: [],
    }));
    await mountWithCleanup(ActivityMenu);
    await contains("button:has(i[aria-label='Attendance'])").click();
    await contains(".o_wrap_btn_sign_out button").click();

    await mountWithCleanup(ActivityMenu);
    await advanceTime(120000);
    await animationFrame();
    expect(".o_hr_reminder_popover").toHaveCount(0);
});

test("checking out shows the reminder again 2 minutes later", async () => {
    let attendanceState = "checked_out";
    const getEmployee = () => ({
        id: 1,
        attendance_state: attendanceState,
        today_attendance_ids: [],
    });
    onRpc("/hr_attendance/attendance_user_data", getEmployee);
    onRpc("/hr_attendance/systray_check_in_out", () => {
        attendanceState = attendanceState === "checked_in" ? "checked_out" : "checked_in";
        return getEmployee();
    });
    await mountWithCleanup(ActivityMenu);
    await advanceTime(120000);
    await animationFrame();
    await contains(".o_hr_reminder_popover button").click();
    await contains(".o_wrap_btn_sign_out button").click();

    await contains("button:has(i[aria-label='Attendance'])").click();
    await contains(".o_wrap_btn_sign_out button").click();
    await advanceTime(119000);
    expect(".o_hr_reminder_popover").toHaveCount(0);
    await advanceTime(1000);
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
