import { test, animationFrame, expect } from "@odoo/hoot";
import { mountWithCleanup, mockService } from "@web/../tests/web_test_helpers";
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
