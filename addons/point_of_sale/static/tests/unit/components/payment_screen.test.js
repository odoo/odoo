import { test, animationFrame, expect } from "@odoo/hoot";
import { mountWithCleanup, mockService } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder, expectFormattedPrice } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { queryOne } from "@odoo/hoot-dom";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
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
