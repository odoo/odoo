import { test, expect, animationFrame } from "@odoo/hoot";
import { mountWithCleanup, patchWithCleanup, mockService } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder, expectFormattedPrice } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { queryOne } from "@odoo/hoot-dom";
import { Deferred } from "@odoo/hoot-mock";
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

test("Print stock report on validation", async () => {
    mockService("action", {
        doAction: async (action) => {
            expect(action.type).toBe("ir.actions.report");
            expect(action.report_name).toBe("stock.report_return_document");
        },
    });
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    order.picking_type_id.has_stock_reports_to_print = true;

    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });
    const firstPm = store.models["pos.payment.method"].getFirst();
    await comp.addNewPaymentLine(firstPm);
    await comp.validateOrder();
});

test("Do not print stock report if not configured", async () => {
    mockService("action", {
        doAction: async () => {
            throw new Error("Action service should not be called");
        },
    });
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);

    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });
    const firstPm = store.models["pos.payment.method"].getFirst();
    await comp.addNewPaymentLine(firstPm);
    await comp.validateOrder();
    expect(order.picking_type_id.has_stock_reports_to_print).toBeEmpty();
});

// Selecting a QR code payment method opens its popup, resolved by the test.
function mockQrPopup(store) {
    const popups = [];
    patchWithCleanup(store, {
        showQR(payment) {
            payment.setPaymentStatus("waiting");
            const popup = new Deferred();
            popups.push(popup);
            return popup;
        },
    });
    return popups;
}

test("Tip can be paid with another method once the QR code popup is closed", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const qrPm = store.models["pos.payment.method"].get(2);
    const cashPm = store.models["pos.payment.method"].get(1);
    qrPm.payment_method_type = "qr_code";
    const popups = mockQrPopup(store);
    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });
    expect(await comp.addNewPaymentLine(qrPm)).toBe(true);
    expect(order.payment_ids[0].payment_status).toBe("waiting");
    expect(order.electronicPaymentInProgress()).toBe(true);

    popups[0].resolve(false);
    await animationFrame();
    expect(order.payment_ids[0].payment_status).toBe("retry");
    expect(order.electronicPaymentInProgress()).toBe(false);
    expect(await comp.addNewPaymentLine(cashPm)).toBe(true);
    expect(order.payment_ids).toHaveLength(2);
    // The cancelled QR code payment still reserves the whole amount due.
    expect(order.payment_ids[1].getAmount()).toBe(0);
    expect(order.isPaid()).toBe(false);
});

test("Split an order between a cancelled QR code payment and another method", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const qrPm = store.models["pos.payment.method"].get(2);
    const cashPm = store.models["pos.payment.method"].get(1);
    qrPm.payment_method_type = "qr_code";
    const popups = mockQrPopup(store);
    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });
    await comp.addNewPaymentLine(qrPm);
    popups[0].resolve(false);
    await animationFrame();
    order.payment_ids[0].setAmount(10);
    expect(await comp.addNewPaymentLine(cashPm)).toBe(true);
    expect(order.payment_ids[1].getAmount()).toBe(7.85);
    expect(order.isPaid()).toBe(false);

    order.payment_ids[0].setPaymentStatus("done");
    expect(order.isPaid()).toBe(true);
});

test("No second QR code payment for an amount already covered by a QR code", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const qrPm = store.models["pos.payment.method"].get(2);
    qrPm.payment_method_type = "qr_code";
    const popups = mockQrPopup(store);
    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });
    await comp.addNewPaymentLine(qrPm);
    popups[0].resolve(false);
    await animationFrame();
    expect(await comp.addNewPaymentLine(qrPm)).toBe(false);
    expect(order.payment_ids).toHaveLength(1);

    // The QR code payment only covers part of the amount due.
    order.payment_ids[0].setAmount(10);
    expect(await comp.addNewPaymentLine(qrPm)).toBe(true);
    expect(order.payment_ids[1].getAmount()).toBe(7.85);
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
