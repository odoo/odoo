import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ClosePosPopup } from "@point_of_sale/app/components/popups/closing_popup/closing_popup";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

const getProps = (overrides = {}) => ({
    orders_details: { quantity: 0, amount: 0 },
    opening_notes: "",
    default_cash_details: {
        id: 1,
        name: "Cash",
        amount: 0,
        opening: 0,
        moves: [],
        payment_amount: 0,
    },
    non_cash_payment_methods: [],
    is_manager: false,
    amount_authorized_diff: null,
    close: () => {},
    ...overrides,
});

test("payment method helpers", async () => {
    await setupPosEnv();

    const paymentMethods = [
        { id: 10, name: "Card A", type: "bank", number: 1, amount: 12 },
        { id: 11, name: "Card B", type: "bank", number: 0, amount: 20 },
        { id: 12, name: "Cash B", type: "cash", number: 1, amount: 5 },
        { id: 13, name: "Later", type: "pay_later", number: 1, amount: 7 },
    ];

    const popup = await mountWithCleanup(ClosePosPopup, {
        props: getProps({ non_cash_payment_methods: paymentMethods }),
    });

    expect(popup.validPms.map((pm) => pm.id)).toEqual([10, 12]);
    expect(popup.isTheLastPM(paymentMethods[0])).toBe(false);
    expect(popup.isTheLastPM(paymentMethods[2])).toBe(true);
    expect(popup.isOnePmUsed()).toBe(false);

    const popupWithoutValid = await mountWithCleanup(ClosePosPopup, {
        props: getProps({
            non_cash_payment_methods: [
                { id: 20, name: "Loyalty", type: "pay_later", number: 0, amount: 3 },
            ],
        }),
    });

    expect(popupWithoutValid.validPms).toEqual([]);
    expect(popupWithoutValid.isOnePmUsed()).toBe(true);
});
