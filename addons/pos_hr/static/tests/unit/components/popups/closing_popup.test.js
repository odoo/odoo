import { test, expect, waitFor } from "@odoo/hoot";
import { contains, mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { Chrome } from "@point_of_sale/app/pos_app";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { removeAllEmployeePin } from "../../utils";
import * as Utils from "../../ui_utils";

definePosModels();

const closingControlData = {
    orders_details: { quantity: 4, amount: 195.45 },
    opening_notes: "",
    default_cash_details: {
        id: 1,
        name: "Cash",
        amount: 123.45,
        opening: 50,
        payment_amount: 63.45,
        moves: [],
        amount_per_employee: [{ id: 3, name: "Employee1", amount: 63.45 }],
        moves_per_employee: [],
    },
    non_cash_payment_methods: [
        {
            id: 2,
            name: "Card",
            type: "bank",
            number: 2,
            amount: 60,
            amount_per_employee: [],
        },
    ],
    is_manager: true,
    amount_authorized_diff: null,
};

test("blind closing respects employee permissions and cash control", async () => {
    removeAllEmployeePin();
    const store = await setupPosEnv();
    store.accessRight.resetCashier();
    store.session.state = "opened";
    store.config.cash_control = true;
    onRpc("pos.session", "get_closing_control_data", () => ({
        ...closingControlData,
        is_manager: store.accessRight.canSeeExpectedCash,
    }));
    await mountWithCleanup(Chrome, { props: { disableLoader: () => {} } });
    const employeeList = [
        ["Administrator", "123.45", true],
        ["Employee1", "0.00", false],
    ];

    for (const [employeeName, expectedCashCount, canSeeExpectedCash] of employeeList) {
        await Utils.openCashierRegister(employeeName);
        await contains(".pos-topheader button[aria-label='Open Menu']").click();
        await contains(".o_pos_burger_menu_buttons button:contains(Close Register)").click();
        await waitFor(".cash-input input");
        expect(".cash-input input").toHaveValue(expectedCashCount);
        expect(".cash-difference").toHaveCount(canSeeExpectedCash ? 1 : 0);
        expect(".total-orders").toHaveCount(canSeeExpectedCash ? 1 : 0);
        expect(".modal-footer button:contains(Close Register)").toHaveCount(1);
        await contains(".modal-footer button:contains(Discard)").click();
        await Utils.lockCashierRegister();
    }

    // Employees with Supervised or Restricted access rights cannot close the register.
    for (const employeeName of ["A Little Guy", "Supervised Employee"]) {
        await Utils.openCashierRegister(employeeName);
        await contains(".pos-topheader button[aria-label='Open Menu']").click();
        await waitFor(".o_pos_burger_menu_buttons");
        expect(".o_pos_burger_menu_buttons button:contains(Close Register)").toHaveCount(0);
        await Utils.lockCashierRegister();
    }
});
