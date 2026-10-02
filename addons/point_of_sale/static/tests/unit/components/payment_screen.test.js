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
