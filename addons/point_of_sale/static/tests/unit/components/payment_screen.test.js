import { test, animationFrame, expect } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-mock";
import { mountWithCleanup, mockService, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { session } from "@web/session";
import { setupPosEnv, getFilledOrder, expectFormattedPrice } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { queryOne } from "@odoo/hoot-dom";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

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

test("Tip can be paid with another method while a QR code payment is pending", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const qrPm = store.models["pos.payment.method"].get(2);
    const cashPm = store.models["pos.payment.method"].get(1);
    qrPm.payment_method_type = "qr_code";
    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });
    expect(await comp.addNewPaymentLine(qrPm)).toBe(true);
    expect(order.payment_ids[0].payment_status).toBe("pending");
    expect(await comp.addNewPaymentLine(cashPm)).toBe(true);
    expect(order.payment_ids).toHaveLength(2);
    // The pending QR code payment already reserves the whole amount due.
    expect(order.payment_ids[1].getAmount()).toBe(0);
    expect(order.isPaid()).toBe(false);

    order.payment_ids[0].setPaymentStatus("waiting");
    expect(order.electronicPaymentInProgress()).toBe(true);
});

test("Split an order between a pending QR code payment and another method", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const qrPm = store.models["pos.payment.method"].get(2);
    const cashPm = store.models["pos.payment.method"].get(1);
    qrPm.payment_method_type = "qr_code";
    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });
    await comp.addNewPaymentLine(qrPm);
    order.payment_ids[0].setAmount(10);
    await comp.addNewPaymentLine(cashPm);
    expect(order.payment_ids[1].getAmount()).toBe(7.85);
    expect(order.isPaid()).toBe(false);

    order.payment_ids[0].setPaymentStatus("done");
    expect(order.isPaid()).toBe(true);
});

test("A cancelled QR code payment does not block another payment method", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const qrPm = store.models["pos.payment.method"].get(2);
    const cashPm = store.models["pos.payment.method"].get(1);
    qrPm.payment_method_type = "qr_code";
    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });
    await comp.addNewPaymentLine(qrPm);
    order.payment_ids[0].setAmount(10);
    // The QR code popup was closed without confirming the payment.
    order.payment_ids[0].handlePaymentResponse(false);
    expect(order.payment_ids[0].payment_status).toBe("retry");
    expect(order.electronicPaymentInProgress()).toBe(false);
    expect(await comp.addNewPaymentLine(cashPm)).toBe(true);
    expect(order.payment_ids[1].getAmount()).toBe(7.85);
    expect(order.isPaid()).toBe(false);
});

test("No second QR code payment for an amount already covered by a QR code", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const qrPm = store.models["pos.payment.method"].get(2);
    qrPm.payment_method_type = "qr_code";
    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });
    await comp.addNewPaymentLine(qrPm);
    order.payment_ids[0].handlePaymentResponse(false);
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

test("validating during a barcode scan does not use the scanned digits as amount", async () => {
    // The buffer only filters fast key sequences outside of test mode.
    patchWithCleanup(session, { test_mode: false });
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const cardPm = store.models["pos.payment.method"].get(2);
    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });
    await comp.addNewPaymentLine(cardPm);
    const amountDue = order.totalDue;

    // Validate is clicked while the scanner is still typing the barcode.
    for (const key of "6224") {
        window.dispatchEvent(new KeyboardEvent("keyup", { key }));
        await advanceTime(3);
    }
    await comp.validateOrder();

    expect(order.payment_ids).toHaveLength(1);
    expect(order.payment_ids[0].getAmount()).toBe(amountDue);
});

test("fast numpad clicks are kept when validating", async () => {
    patchWithCleanup(session, { test_mode: false });
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const cashPm = store.models["pos.payment.method"].get(1);
    const comp = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });
    await comp.addNewPaymentLine(cashPm);

    for (const key of "500") {
        comp.numberBuffer.sendKey(key);
        await advanceTime(3);
    }
    await comp.validateOrder();

    expect(order.payment_ids[0].getAmount()).toBe(500);
});
