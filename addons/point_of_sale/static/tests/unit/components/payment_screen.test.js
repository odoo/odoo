import { test, expect, animationFrame } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";
import { setupPosEnv, getFilledOrder, expectFormattedPrice, addTestTerminals } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { queryOne } from "@odoo/hoot-dom";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { localization } from "@web/core/l10n/localization";

definePosModels();

test("Change always incl", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const firstPm = store.models["pos.payment.method"].getFirst();
    order.config.iface_tax_included = "total";
    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });
    await comp.addNewPaymentLine(firstPm);
    order.payment_ids[0].setAmount(1000);
    await animationFrame();
    const total = queryOne(".amount");
    expectFormattedPrice(total.attributes.amount.value, "$ -405.00");
    order.config.iface_tax_included = "subtotal";
    await animationFrame();
    const subtotal = queryOne(".amount");
    expectFormattedPrice(subtotal.attributes.amount.value, "$ -405.00");
});

test("addTip startingValue uses locale decimal separator on overpayment", async () => {
    const store = await setupPosEnv();
    store.config.iface_tipproduct = true;
    patch(localization, { decimalPoint: ",", thousandsSep: "." });

    const order = await getFilledOrder(store);
    const cashPm = store.models["pos.payment.method"].get(1);
    const { data: paymentLine } = order.addPaymentline(cashPm);
    paymentLine.setAmount(1000);
    expect(Math.abs(order.change)).toBe(405);

    let capturedStartingValue;
    const screen = {
        pos: store,
        currentOrder: order,
        env: { services: { localization } },
        dialog: {
            add: (_, props) => {
                capturedStartingValue = props.startingValue;
            },
        },
    };
    await PaymentScreen.prototype.addTip.call(screen);

    const tipAmount = PaymentScreen.prototype.computeNewTip.call(screen, {
        value: capturedStartingValue,
        type: "fixed",
    });
    expect(tipAmount).toBe(405);
});

test("showPaymentMethod", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const customerAccount = store.models["pos.payment.method"].get(3);
    const card = store.models["pos.payment.method"].get(2);
    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });

    expect(comp.showPaymentMethod(customerAccount)).toBe(true);
    expect(comp.showPaymentMethod(card)).toBe(true);

    // Pay later methods need the access right
    patch(store.accessRight, {
        get canAccessPaymentMethod() {
            return false;
        },
    });
    expect(comp.showPaymentMethod(customerAccount)).toBe(false);
    expect(comp.showPaymentMethod(card)).toBe(true);

    // The payment method must be available for the order
    order.is_refund = true;
    card.payment_interface = { supports_refunds: false };
    expect(comp.showPaymentMethod(card)).toBe(false);
});

test("displayedPaymentMethods", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const [terminal1, terminal2] = addTestTerminals(store);
    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });

    // Without default, a single provider button replaces the grouped methods
    const displayed = comp.displayedPaymentMethods;
    expect(displayed.map((pm) => pm.name)).toEqual(["Cash", "Card", "Test Provider"]);
    const providerButton = displayed[2];
    expect(providerButton.isProvider).toBe(true);
    expect(providerButton.provider).toBe("test_terminal");
    expect(providerButton.paymentMethod).toBe(terminal1);
    expect(".paymentmethod:contains('Test Provider')").toHaveCount(1);
    expect(".paymentmethod:contains('Test Terminal')").toHaveCount(0);

    // With a default, only the default method of the provider is displayed
    store.paymentMethods.setDefault("test_terminal", terminal2.id);
    expect(comp.displayedPaymentMethods.map((pm) => pm.name)).toEqual([
        "Cash",
        "Card",
        "Test Terminal 2",
    ]);
    expect(comp.displayedPaymentMethods[2]).toBe(terminal2);
    await animationFrame();
    expect(".paymentmethod:contains('Test Terminal 2')").toHaveCount(1);
    expect(".paymentmethod:contains('Test Terminal 1')").toHaveCount(0);
    expect(".paymentmethod:contains('Test Provider')").toHaveCount(0);
});

test("onClickProvider", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const [, terminal2] = addTestTerminals(store);
    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });

    let selectedId;
    patch(store.paymentMethods, {
        async selectDefaults(providers) {
            expect(providers).toEqual(["test_terminal"]);
            if (selectedId === undefined) {
                return false;
            }
            this.setDefault("test_terminal", selectedId);
            return true;
        },
    });

    // Cancelled: no payment line
    await comp.onClickProvider("test_terminal");
    expect(order.payment_ids).toHaveLength(0);

    // Confirmed without default: no payment line
    selectedId = false;
    await comp.onClickProvider("test_terminal");
    expect(order.payment_ids).toHaveLength(0);

    // Confirmed with a default: a payment line is added with it
    selectedId = terminal2.id;
    await comp.onClickProvider("test_terminal");
    expect(order.payment_ids).toHaveLength(1);
    expect(order.payment_ids[0].payment_method_id).toBe(terminal2);
});
