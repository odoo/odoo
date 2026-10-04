import { beforeEach, expect, test } from "@odoo/hoot";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { contains, mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";

import { ActivityMenu } from "@hr_attendance/components/attendance_menu/attendance_menu";
import { registry } from "@web/core/registry";

defineMailModels();

const attendanceData = {
    id: 1,
    name: "John Doe",
    hours_today: 0,
    today_attendance_ids: [
        {
            id: 1,
            check_in: "2026-08-16 10:00:00",
            check_out: false,
            worked_hours: 0,
        },
    ],
    last_attendance_worked_hours: 0,
    attendance_state: "checked_in",
    display_systray: true,
    device_tracking_enabled: false,
};

beforeEach(() => {
    registry.category("services").add(
        "lazy_session",
        {
            start() {
                return {
                    getValue(key, callback) {
                        callback(key === "attendance_user_data" ? attendanceData : undefined);
                    },
                };
            },
        },
        { force: true }
    );
});

test("attendance data is refreshed each time the dropdown opens", async () => {
    let refreshedDuration = 0.25;
    onRpc("/hr_attendance/attendance_user_data", () => {
        expect.step("attendance_user_data");
        return {
            ...attendanceData,
            hours_today: refreshedDuration,
            last_attendance_worked_hours: refreshedDuration,
        };
    });

    await mountWithCleanup(ActivityMenu);

    await contains("button.o-dropdown").click();
    expect(".o_att_today_wrap tr:first-child td:last-child").toHaveText("0h15");
    expect.verifySteps(["attendance_user_data"]);

    await contains("button.o-dropdown").click();
    refreshedDuration = 0.5;
    await contains("button.o-dropdown").click();
    expect(".o_att_today_wrap tr:first-child td:last-child").toHaveText("0h30");
    expect.verifySteps(["attendance_user_data"]);
});
