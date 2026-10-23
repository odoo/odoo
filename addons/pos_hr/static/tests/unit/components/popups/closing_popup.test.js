import { test, expect, waitFor } from "@odoo/hoot";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
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
    const store = await Utils.setupAndMountPosHrApp({ cash_control: true });
    store.session.state = "opened";
    onRpc("pos.session", "get_closing_control_data", () => ({
        ...closingControlData,
        is_manager: store.accessRight.canSeeExpectedCash,
    }));
    const employeeList = [
        { employeeName: "Administrator", pin: "1234", expectedCashCount: "123.45" },
        { employeeName: "Employee1", pin: false, expectedCashCount: "0.00" },
    ];

    for (const { employeeName, expectedCashCount, pin } of employeeList) {
        await Utils.login(employeeName, pin);
        await Utils.openMenu();
        await Utils.clickMenuOption("Close Register");
        await waitFor(".cash-input input");
        expect(".cash-input input").toHaveValue(expectedCashCount);

        const canSeeExpectedCash = expectedCashCount === "0.00" ? 0 : 1;
        expect(".cash-difference").toHaveCount(canSeeExpectedCash);
        expect(".total-orders").toHaveCount(canSeeExpectedCash);
        expect(".modal-footer button:contains(Close Register)").toHaveCount(1);
        await contains(".modal-footer button:contains(Discard)").click();
        await Utils.clickLockButton();
    }

    // Employees with Supervised or Restricted access rights cannot close the register.
    for (const employeeName of ["A Little Guy", "Supervised Employee"]) {
        await Utils.login(employeeName);
        await Utils.openMenu();
        expect(Utils.hasMenuOption("Close Register")).toBe(false);
        await Utils.closeMenu();
        await Utils.clickLockButton();
    }
});
