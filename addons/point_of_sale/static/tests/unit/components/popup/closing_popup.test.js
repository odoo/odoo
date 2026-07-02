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
        type: "cash",
        amount: 0,
        cash_breakdown: {
            statement_amount: 0,
            payment_amount: 0,
            opening: 0,
        },
    },
    non_cash_payment_methods: [],
    is_manager: false,
    amount_authorized_diff: null,
    close: () => {},
    ...overrides,
});

test("cash payment info are at always on right side of bottom row", async () => {
    const store = await setupPosEnv();

    const paymentMethods = [
        { id: 10, name: "Card A", type: "bank", editable: true, amount: 12 },
        { id: 11, name: "Card B", type: "bank", editable: true, amount: 20 },
        { id: 12, name: "Cash B", type: "cash", editable: true, amount: 5 },
        { id: 13, name: "Later", type: "pay_later", editable: false, amount: 7 },
    ];

    const popup = await mountWithCleanup(ClosePosPopup, {
        props: getProps({ non_cash_payment_methods: paymentMethods }),
    });
    expect(popup.paymentMethods).toHaveLength(5);
    expect(popup.paymentMethods.map((pm) => pm.id)).toMatchObject([13, 10, 11, 12, 1]);

    paymentMethods.pop();
    popup.props = getProps({ non_cash_payment_methods: paymentMethods });

    expect(popup.paymentMethods).toHaveLength(4);
    const result = store.ui.isSmall ? [10, 11, 12, 1] : [10, 11, 1, 12];
    expect(popup.paymentMethods.map((pm) => pm.id)).toMatchObject(result);
});

test("cashTransactionSummary", async () => {
    await setupPosEnv();
    const props = getProps();
    props.default_cash_details.cash_breakdown = {
        statement_amount: 100,
        payment_amount: 200,
        opening: 300,
    };
    const popup = await mountWithCleanup(ClosePosPopup, { props });
    expect(popup.cashTransactionSummary).toMatchObject({
        total: 300,
        list: [
            {
                id: 0,
                name: "Cash in/out",
                amount: 100,
            },
            {
                id: 1,
                name: "Payments",
                amount: 200,
            },
        ],
    });
});
