import { test, expect, animationFrame } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";
import {
    setupPosEnv,
    getFilledOrder,
    expectFormattedPrice,
    addTestTerminals,
    createPaymentLine,
} from "../utils";
import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { definePosModels } from "../data/generate_model_definitions";
import { queryOne } from "@odoo/hoot-dom";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { localization } from "@web/core/l10n/localization";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";

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

test("deletePaymentLine", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const cash = store.models["pos.payment.method"].get(1);
    const [terminal] = addTestTerminals(store, 1);
    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });

    let cancelSuccess;
    const cancelledLines = [];
    patch(PosPayment.prototype, {
        async cancelPayment() {
            cancelledLines.push(this.uuid);
            return cancelSuccess;
        },
    });
    const deleteLine = async (line) => {
        comp.deletePaymentLine(line.uuid);
        await animationFrame();
        return !order.payment_ids.includes(line);
    };

    // Not cancellable: removed at once
    const cashLine = createPaymentLine(store, order, cash);
    expect(cashLine.isCancellable).toBe(false);
    expect(await deleteLine(cashLine)).toBe(true);
    expect(cancelledLines).toHaveLength(0);

    // Cancellable: removed only when the cancel succeeds
    const waitingLine = createPaymentLine(store, order, terminal, {
        payment_status: "waiting_card",
    });
    expect(waitingLine.isCancellable).toBe(true);
    cancelSuccess = false;
    expect(await deleteLine(waitingLine)).toBe(false);
    expect(cancelledLines).toEqual([waitingLine.uuid]);

    cancelSuccess = true;
    expect(await deleteLine(waitingLine)).toBe(true);
    expect(cancelledLines).toEqual([waitingLine.uuid, waitingLine.uuid]);
});

test("onNewTip", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });
    const paymentline = createPaymentLine(store, order, card);

    const tips = [];
    const notifications = [];
    patch(store, {
        async setTip(tipAmount) {
            tips.push(tipAmount);
        },
    });
    patch(comp, {
        computeNewTip: ({ value }) => value,
    });
    patch(comp.notification, {
        add: (message) => notifications.push(message),
    });

    // No value: nothing happens
    await comp.onNewTip({ newValue: undefined, type: "fixed", currentTipAmount: 0, change: 0 });
    expect(tips).toEqual([]);

    // No selected line: the tip is only set on the order
    await comp.onNewTip({ newValue: 2, type: "fixed", currentTipAmount: 0, change: 0 });
    expect(tips).toEqual([2]);
    expect(paymentline.getAmount()).toBe(10);

    // Same tip as before: the selected line is left alone
    order.selectPaymentline(paymentline);
    await comp.onNewTip({ newValue: 2, type: "fixed", currentTipAmount: 2, change: 0 });
    expect(tips).toEqual([2, 2]);
    expect(paymentline.getAmount()).toBe(10);

    // Line not editable: the cashier is notified and the line is left alone
    paymentline.payment_status = "waiting_card";
    await comp.onNewTip({ newValue: 3, type: "fixed", currentTipAmount: 2, change: 0 });
    expect(tips).toEqual([2, 2, 3]);
    expect(notifications).toHaveLength(1);
    expect(paymentline.getAmount()).toBe(10);

    // No change: the tip difference is added to the line
    paymentline.payment_status = null;
    await comp.onNewTip({ newValue: 2, type: "fixed", currentTipAmount: undefined, change: 0 });
    expect(paymentline.getAmount()).toBe(12);

    // Editable status of a payment interface: the tip difference is added to the line
    paymentline.payment_status = "retry";
    await comp.onNewTip({ newValue: 5, type: "fixed", currentTipAmount: 2, change: -1 });
    expect(paymentline.getAmount()).toBe(15);

    // Change covers part of the tip: only the rest is added to the line
    await comp.onNewTip({ newValue: 9, type: "fixed", currentTipAmount: 5, change: 1 });
    expect(paymentline.getAmount()).toBe(18);

    // Change covers the whole tip: the line is left alone
    await comp.onNewTip({ newValue: 10, type: "fixed", currentTipAmount: 9, change: 3 });
    expect(paymentline.getAmount()).toBe(18);
    expect(notifications).toHaveLength(1);
});

test("Caba pay later always invoice", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const existingPartner = store.models["res.partner"].get(3);
    order.partner_id = existingPartner;
    const customerAccount = store.models["pos.payment.method"].get(3);
    const tax = store.models["account.tax"].get(1);
    tax.update({ tax_exigibility: "on_payment" });
    order.config.iface_tax_included = "total";
    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });
    expect(order.isToInvoice()).toBe(false);
    await comp.addNewPaymentLine(customerAccount);
    expect(order.isToInvoice()).toBe(true);

    const validation = new OrderPaymentValidation({ pos: store, orderUuid: order.uuid });
    comp.toggleIsToInvoice();
    expect(order.isToInvoice()).toBe(false);
    const res = await validation.isOrderValid();
    expect(res).toBe(false);

    const validation2 = new OrderPaymentValidation({ pos: store, orderUuid: order.uuid });
    comp.toggleIsToInvoice();
    expect(order.isToInvoice()).toBe(true);
    const res2 = await validation2.isOrderValid();
    expect(res2).toBe(true);
});
