import { test, expect, waitFor } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as Utils from "../../ui_utils";

definePosModels();

test("blind opening respects employee permissions and previous balances", async () => {
    const store = await Utils.setupAndMountPosHrApp({ cash_control: true });
    store.session.state = "opening_control";
    store.config._last_opening_balance = 123.45;
    const employeeList = [
        // Name, PIN, expected opening amount, can Open Register
        ["Administrator", "1234", "123.45", true],
        ["Employee1", false, "0.00", true],
        ["A Little Guy", false, "0.00", false],
        ["Supervised Employee", false, "0.00", false],
    ];

    for (const [emplName, pin, expectAmt, canOpen] of employeeList) {
        await Utils.login(emplName, pin);
        await waitFor(".opening-cash-section input");
        expect(".opening-cash-section input").toHaveValue(expectAmt);

        expect(".modal-footer button:contains(Open Register)").toHaveCount(canOpen ? 1 : 0);
        await contains(".modal-footer button:contains(Discard)").click();
    }
});
