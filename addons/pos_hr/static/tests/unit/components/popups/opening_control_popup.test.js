import { test, expect, waitFor } from "@odoo/hoot";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { Chrome } from "@point_of_sale/app/pos_app";
import * as Utils from "../../ui_utils";
import { removeAllEmployeePin } from "../../utils";

definePosModels();

test("blind opening respects employee permissions and previous balances", async () => {
    removeAllEmployeePin();
    const store = await setupPosEnv();
    store.accessRight.resetCashier();
    store.session.state = "opening_control";
    store.config._last_opening_balance = 123.45;
    await mountWithCleanup(Chrome, { props: { disableLoader: () => {} } });
    const employeeList = [
        // Name, expected opening amount, can Open Register
        ["Administrator", "123.45", true],
        ["Employee1", "0.00", true],
        ["A Little Guy", "0.00", false],
        ["Supervised Employee", "0.00", false],
    ];

    for (const [emplName, expectAmt, canOpen] of employeeList) {
        await Utils.openCashierRegister(emplName);
        await waitFor(".opening-cash-section input");
        expect(".opening-cash-section input").toHaveValue(expectAmt);

        expect(".modal-footer button:contains(Open Register)").toHaveCount(canOpen ? 1 : 0);
        await contains(".modal-footer button:contains(Discard)").click();
    }
});
