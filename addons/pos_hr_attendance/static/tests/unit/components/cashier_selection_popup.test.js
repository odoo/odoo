import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { CashierSelectionPopup } from "@pos_hr/app/components/popups/cashier_selection_popup/cashier_selection_popup";

definePosModels();

test("shows the checked-in badge for checked-in employees only", async () => {
    const store = await setupPosEnv();
    await mountWithCleanup(CashierSelectionPopup, {
        props: {
            close: () => {},
            getPayload: () => {},
            employees: store.models["hr.employee"].getAll(),
        },
    });
    await animationFrame();

    expect(".checked-in-badge").toHaveCount(1);
    expect(".cashier-selection-item:has(.checked-in-badge)").toHaveText(/Employee1/);
});

test("shows no checked-in badge when the attendance states cannot be loaded", async () => {
    onRpc("hr.employee", "get_pos_attendance_states", () => {
        throw new Error("offline");
    });
    const store = await setupPosEnv();
    await mountWithCleanup(CashierSelectionPopup, {
        props: {
            close: () => {},
            getPayload: () => {},
            employees: store.models["hr.employee"].getAll(),
        },
    });
    await animationFrame();

    expect(".checked-in-badge").toHaveCount(0);
});
