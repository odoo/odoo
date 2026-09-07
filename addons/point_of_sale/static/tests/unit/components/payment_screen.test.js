import { test, expect, animationFrame } from "@odoo/hoot";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder, expectFormattedPrice } from "../utils";
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
    order.payment_ids[0].setAmount(20);
    await animationFrame();
    const total = queryOne(".amount");
    expectFormattedPrice(total.attributes.amount.value, "$ -2.15");
    order.config.iface_tax_included = "subtotal";
    await animationFrame();
    const subtotal = queryOne(".amount");
    expectFormattedPrice(subtotal.attributes.amount.value, "$ -2.15");
});

test("showPaymentMethod", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const card = store.models["pos.payment.method"].get(2);
    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });

    // Cashier Minimal
    store.cashier._role = "minimal";
    card.type = "pay_later";
    expect(comp.showPaymentMethod(card)).toBe(false);

    card.type = "cash";
    expect(comp.showPaymentMethod(card)).toBe(true);

    // Cashier Admin
    store.cashier._role = "admin";
    card.type = "pay_later";
    expect(comp.showPaymentMethod(card)).toBe(true);

    card.type = "cash";
    expect(comp.showPaymentMethod(card)).toBe(true);

    // Is Refund + no payment interface
    order.is_refund = true;
    expect(comp.showPaymentMethod(card)).toBe(true);

    // Is Refund + payment interface not supporting refunds
    card.payment_interface = { supports_refunds: false };
    expect(comp.showPaymentMethod(card)).toBe(false);

    // Is Refund + payment interface supporting refunds
    card.payment_interface = { supports_refunds: true };
    expect(comp.showPaymentMethod(card)).toBe(true);
});

test("addTip startingValue uses locale decimal separator on overpayment", async () => {
    const store = await setupPosEnv();
    store.config.iface_tipproduct = true;
    patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: "." });

    const order = await getFilledOrder(store);
    const cashPm = store.models["pos.payment.method"].get(1);
    const { data: paymentLine } = order.addPaymentline(cashPm);
    paymentLine.setAmount(22);
    expect(Math.abs(order.change)).toBe(4.15);

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
    expect(tipAmount).toBe(4.15);
});

const getPaidOrder = async (store, { invoiced = false } = {}) => {
    const order = await getFilledOrder(store);
    if (invoiced) {
        order.setToInvoice(true);
    }
    order.state = "paid";
    return order;
};

const getRefundOrderFor = (store, originalOrder) => {
    const refund = store.addNewOrder();
    refund.is_refund = true;
    refund.refunded_order_id = originalOrder;
    return refund;
};

test("invoice button stays enabled for a refund whose original order was not invoiced", async () => {
    const store = await setupPosEnv();
    const originalOrder = await getPaidOrder(store, { invoiced: false });
    const refundOrder = getRefundOrderFor(store, originalOrder);

    await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: refundOrder.uuid },
    });
    await animationFrame();

    expect(refundOrder.refunded_order_id?.id).toBe(originalOrder.id);
    expect(refundOrder.isToInvoice()).toBe(false);

    const invoiceBtn = queryOne(".js_invoice");
    expect(invoiceBtn.disabled).toBe(false);
});

test("invoice button is enabled for normal orders", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);

    await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });
    await animationFrame();

    const invoiceBtn = queryOne(".js_invoice");
    expect(invoiceBtn.disabled).toBe(false);
});
