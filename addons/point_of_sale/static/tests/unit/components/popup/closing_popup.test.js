import { test, expect, animationFrame } from "@odoo/hoot";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ClosePosPopup } from "@point_of_sale/app/components/popups/closing_popup/closing_popup";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

// Utils
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
        editable: true,
        is_default_cash: true,
    },
    non_cash_payment_methods: [],
    is_manager: false,
    amount_authorized_diff: null,
    close: () => {},
    ...overrides,
});

const expectPaymentCard = (name, selector = "") =>
    expect(`.payment-method-card:has(span:contains(${name})) ${selector}`);

const expectDifference = (name, difference, className, amount) => {
    expectPaymentCard(name, ".amount-difference").toHaveText(`($ ${difference}.00)`);
    expectPaymentCard(name, ".amount-difference").toHaveClass(className);
    expectPaymentCard(name, "> div:first-child span:last-child").toHaveText(`$ ${amount}.00`);
};

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

    paymentMethods.pop();
    popup.props = getProps({ non_cash_payment_methods: paymentMethods });

    expect(popup.paymentMethods).toHaveLength(4);
    const result = store.ui.isSmall ? [10, 11, 12, 1] : [10, 11, 1, 12];
    expect(popup.paymentMethods.map((pm) => pm.id)).toMatchObject(result);
});

test("cashTransactionSummary", async () => {
    await setupPosEnv();

    const props = getProps();
    props.default_cash_details = {
        ...props.default_cash_details,
        statement_amount: 100,
        moves: [
            { name: "Session-01-Who-care's", amount: 75 },
            { name: "Session-01-I'll-not-say", amount: 25 },
        ],
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
                subTransactions: [
                    { id: 0, name: "Session-01-Who-care's", amount: 75 },
                    { id: 1, name: "Session-01-I'll-not-say", amount: 25 },
                ],
            },
            {
                id: 1,
                name: "Payments",
                amount: 200,
            },
        ],
    });
});

test("Closing Popup Ui", async () => {
    const store = await setupPosEnv();
    const props = getProps({
        non_cash_payment_methods: [
            { id: 10, name: "Card", type: "bank", editable: true, amount: 12 },
            { id: 13, name: "Later", type: "pay_later", editable: false, amount: 7 },
        ],
        opening_notes: "Very gracefful Opening Note",
        orders_details: { quantity: 4, amount: 40 },
    });
    props.default_cash_details = {
        ...props.default_cash_details,
        amount: 50,
        opening: 20,
        moves: [
            { name: "Money-Comes", amount: 5 },
            { name: "Money-Goes", amount: -15 },
        ],
        payment_amount: 40,
    };
    await mountWithCleanup(ClosePosPopup, { props });

    // Header
    expect(".total-orders").toHaveText("4 Orders: $ 40.00");
    expect(".payment-method-card").toHaveCount(3);
    ["Cash", "Card", "Later"].forEach((name) => expectPaymentCard(name).toBeDisplayed());

    // Cash card
    !store.ui.isSmall && expectPaymentCard("Cash", "input").toBeFocused();
    expectPaymentCard("Cash", "input").toHaveValue(50);
    expectPaymentCard("Cash", "button[data-icon='payments']").toBeDisplayed();
    expectPaymentCard("Cash", ".cash-summary").toBeDisplayed();
    expectPaymentCard("Cash", ".cash-summary:contains(Opening $ 20.00)").toBeDisplayed();

    // Transaction breakdown
    expectPaymentCard("Cash", ".accordion-header:contains(Transactions)").toBeDisplayed();
    await contains(".accordion-header:contains(Transactions)").click();
    expectPaymentCard(
        "Cash",
        ".accordion-content div:contains(Cash in/out $ -10.00)"
    ).toBeDisplayed();
    expectPaymentCard("Cash", ".accordion-content div:contains(Payments $ 40.00)").toBeDisplayed();

    await contains(".accordion-header:contains(Cash in/out)").click();
    expectPaymentCard(
        "Cash",
        ".accordion-content div:contains(Money-Comes $ 5.00)"
    ).toBeDisplayed();
    expectPaymentCard(
        "Cash",
        ".accordion-content div:contains(Money-Goes $ -15.00)"
    ).toBeDisplayed();

    // Non-cash payment methods
    expectPaymentCard("Card", "input").toHaveValue(12);
    expectPaymentCard("Later", "input").toHaveValue(7);
    expectPaymentCard("Later", "input").toHaveAttribute("readonly", "");

    // Notes
    expect(".opening-notes").toHaveValue("Very gracefful Opening Note");
    expect(".closing-notes").toHaveValue("");

    // Clearing the card payment.
    await contains(
        ".payment-method-card:has(span:contains(Card)) .input-container i[data-icon='close']"
    ).click();
    await animationFrame();

    expectDifference("Card", "-12", "text-danger", "12");

    // Changing the cash amount.
    await contains(".payment-method-card:has(span:contains(Cash)) input").edit("70");
    await animationFrame();

    expectDifference("Cash", "20", "text-success", "50");
});
