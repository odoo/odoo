import { test, expect, animationFrame, waitFor } from "@odoo/hoot";
import { contains, mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { ClosePosPopup } from "@point_of_sale/app/components/popups/closing_popup/closing_popup";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as Utils from "../../ui_utils";

definePosModels();

const closingControlData = {
    orders_details: { quantity: 4, amount: 195.45 },
    opening_notes: "",
    default_cash_details: {
        id: 1,
        name: "Cash",
        moves: [],
        amount: 60,
        opening: 20,
        payment_amount: 40,
        amount_per_employee: [
            { id: 21, name: "Test-P", amount: 21 },
            { id: 22, name: "The Other Employee", amount: 19 },
        ],
        editable: true,
        is_default_cash: true,
    },
    non_cash_payment_methods: [
        {
            id: 2,
            name: "Card",
            number: 2,
            amount: 60,
            amount_per_employee: [],
            editable: true,
        },
    ],
    is_manager: true,
    amount_authorized_diff: null,
};

const expectCashCard = (selector) =>
    expect(`.payment-method-card:has(span:contains(Cash)) ${selector}`);
const expectCashTransaction = (label, amount) =>
    expectCashCard(
        `.accordion-content div:contains(${label} $ ${amount.toFixed(2)})`
    ).toBeDisplayed();

test("Closing popup per-employee payment breakdown", async () => {
    const store = await setupPosEnv();
    await mountWithCleanup(ClosePosPopup, {
        props: { ...closingControlData, close: () => {} },
    });

    await contains(".accordion-header:contains(Transactions)").click();
    expectCashTransaction("Test-P", 21);
    expectCashTransaction("The Other Employee", 19);

    store.config.module_pos_hr = false;
    await animationFrame();
    expectCashTransaction("Payments", 40);
});

test("blind closing hides expected cash but preserves non-cash amounts", async () => {
    const store = await Utils.setupAndMountPosHrApp({ cash_control: true });
    store.session.state = "opened";
    onRpc("pos.session", "get_closing_control_data", () => ({
        ...closingControlData,
        is_manager: store.accessRight.canSeeExpectedCash,
    }));
    const employeeList = [
        { employeeName: "Administrator", pin: "1234", canSeeExpectedCash: true },
        { employeeName: "Employee1", pin: false, canSeeExpectedCash: false },
    ];

    for (const { employeeName, canSeeExpectedCash, pin } of employeeList) {
        await Utils.login(employeeName, pin);
        await Utils.openMenu();
        await Utils.clickMenuOption("Close Register");
        await waitFor(".cash-input input");
        expect(".cash-input input").toHaveValue(canSeeExpectedCash ? "60.00" : "0.00");
        expect(".cash-input input[readonly]").toHaveCount(0);
        expectCashCard("> div:first-child > div").toHaveCount(canSeeExpectedCash ? 1 : 0);
        expect(".cash-summary").toHaveCount(canSeeExpectedCash ? 1 : 0);
        expect(".total-orders").toHaveCount(canSeeExpectedCash ? 1 : 0);
        expect(".payment-method-card:has(span:contains(Card)) input").toHaveValue("60.00");
        expect(".payment-method-card:has(span:contains(Card)) > div:first-child > div").toHaveText(
            "$ 60.00"
        );
        expect(".modal-footer button:contains(Daily Sale)").toHaveCount(canSeeExpectedCash ? 1 : 0);

        await contains(".cash-input input").edit("65");
        await animationFrame();
        expect(".cash-input input").toHaveValue("65");
        expectCashCard(".amount-difference").toHaveCount(canSeeExpectedCash ? 1 : 0);
        if (canSeeExpectedCash) {
            await contains(".accordion-header:contains(Transactions)").click();
            expectCashTransaction("Test-P", 21);
            expectCashTransaction("The Other Employee", 19);
        }
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
