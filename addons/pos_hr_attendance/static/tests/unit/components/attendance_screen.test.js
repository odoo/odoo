import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import {
    contains,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { session } from "@web/session";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { mountPosApp, scanBarcode } from "@point_of_sale/../tests/unit/ui_utils";
import { AttendanceScreen } from "@pos_hr_attendance/app/screens/attendance_screen/attendance_screen";
import { KIOSK_INFO } from "@pos_hr_attendance/../tests/unit/data/pos_config.data";

definePosModels();

test("shows the attendance kiosk and loads its info once per session", async () => {
    let calls = 0;
    onRpc("pos.config", "get_attendance_kiosk_info", () => {
        calls++;
        return KIOSK_INFO;
    });
    await setupPosEnv();
    await mountWithCleanup(AttendanceScreen);
    await mountWithCleanup(AttendanceScreen);

    expect(".o_attendance_background").toHaveCount(2);
    expect(".o_hr_kiosk_mode_bottom button:first").toHaveText("Identify Manually");
    expect(calls).toBe(1);
});

test.tags("desktop");
test("attendance tab in the navbar opens the attendance screen", async () => {
    const store = await setupPosEnv();
    await mountPosApp(store);

    await contains(".attendance-button").click();
    await animationFrame();

    expect(store.router.currentScreen()).toBe("AttendanceScreen");
    expect(".attendance-button").toHaveClass("active");
    expect(".orders-button").not.toHaveClass("active");
});

test("scanning a badge on the attendance screen does not switch the cashier", async () => {
    patchWithCleanup(session, { nomenclature_id: 1 });
    onRpc("/hr_attendance/attendance_barcode_scanned", () => ({}));
    const store = await setupPosEnv();
    store.setCashier(store.models["hr.employee"].get(2));
    await mountPosApp(store);
    store.navigate("AttendanceScreen");
    await animationFrame();

    await scanBarcode("041333");

    expect(store.accessRight.loggedCashier.name).toBe("Administrator");
});
