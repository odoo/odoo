import { animationFrame, expect, test } from "@odoo/hoot";
import { Component, signal, xml } from "@odoo/owl";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels, models, mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { AttendanceCalendarOverview } from "@hr_attendance/components/attendance_calendar/attendance_calendar_overview";

class HrEmployee extends models.ServerModel {
    _name = "hr.employee";
}

defineModels([HrEmployee]);
defineMailModels();

test("worked hours display updates when dateRange prop changes", async () => {
    const dateRange = signal({ start: "2024-01-01", end: "2024-01-31" });

    onRpc("get_attendace_data_by_employee", ({ args }) => {
        expect.step(`load:${args[1]}`);
        return { 1: { worked_hours: args[1] === "2024-01-01" ? 8 : 16, overtime_hours: 0 } };
    });

    class Container extends Component {
        static components = { AttendanceCalendarOverview };
        static template = xml`<AttendanceCalendarOverview dateRange="this.dateRange()"/>`;
        setup() {
            this.dateRange = dateRange;
        }
    }

    await mountWithCleanup(Container, {
        componentEnv: {
            searchModel: { context: { active_id: 1 } },
        },
    });
    await animationFrame();
    expect.verifySteps(["load:2024-01-01"]);
    const [workedEl1, overtimeEl1] = document.querySelectorAll(".o_attendance_info_number");
    expect(workedEl1).toHaveText("8h");
    expect(overtimeEl1).toHaveText("0h");

    dateRange.set({ start: "2024-02-01", end: "2024-02-29" });
    await animationFrame();
    expect.verifySteps(["load:2024-02-01"]);
    const [workedEl2, overtimeEl2] = document.querySelectorAll(".o_attendance_info_number");
    expect(workedEl2).toHaveText("16h");
    expect(overtimeEl2).toHaveText("0h");
});
