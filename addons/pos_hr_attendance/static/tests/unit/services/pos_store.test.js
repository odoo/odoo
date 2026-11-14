import { expect, test } from "@odoo/hoot";
import { onRpc } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("refreshAttendanceStates marks checked-in employees", async () => {
    const store = await setupPosEnv();
    await store.refreshAttendanceStates();

    expect(store.isEmployeeCheckedIn(store.models["hr.employee"].get(3))).toBe(true);
    expect(store.isEmployeeCheckedIn(store.models["hr.employee"].get(2))).toBe(false);
});

test("refreshAttendanceStates keeps the last known states when the call fails", async () => {
    const store = await setupPosEnv();
    await store.refreshAttendanceStates();
    onRpc("hr.employee", "get_pos_attendance_states", () => {
        throw new Error("offline");
    });
    await store.refreshAttendanceStates();

    expect(store.isEmployeeCheckedIn(store.models["hr.employee"].get(3))).toBe(true);
});
