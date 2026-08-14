import { test, expect, animationFrame } from "@odoo/hoot";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ClosePosPopup } from "@point_of_sale/app/components/popups/closing_popup/closing_popup";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

const props = {
    orders_details: { quantity: 0, amount: 0 },
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
    non_cash_payment_methods: [],
    is_manager: false,
    amount_authorized_diff: null,
    close: () => {},
};

const expectCashCard = (selector) =>
    expect(`.payment-method-card:has(span:contains(Cash)) ${selector}`);
const expectCashTransaction = (label, amount) =>
    expectCashCard(
        `.accordion-content div:contains(${label} $ ${amount.toFixed(2)})`
    ).toBeDisplayed();

test("Closing popup per-employee payment breakdown", async () => {
    const store = await setupPosEnv();
    await mountWithCleanup(ClosePosPopup, { props });

    await contains(".accordion-header:contains(Transactions)").click();
    expectCashTransaction("Test-P", 21);
    expectCashTransaction("The Other Employee", 19);

    store.config.module_pos_hr = false;
    await animationFrame();
    expectCashTransaction("Payments", 40);
});
