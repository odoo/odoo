import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
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
