import { test, expect } from "@odoo/hoot";
import { animationFrame, click, waitFor } from "@odoo/hoot-dom";
import { mountWithCleanup, mockService } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosStockModels } from "../data/generate_model_definitions";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";

definePosStockModels();

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
    await comp.onClickValidate();
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
    await comp.onClickValidate();
    expect(order.picking_type_id.has_stock_reports_to_print).toBeEmpty();
});

async function scheduleOrder(choice) {
    await click(".button:contains('Schedule for later')");
    await waitFor(".modal");
    await click(`.modal button:contains('${choice}')`);
    await click(".modal button:contains('Confirm')");
    await animationFrame();
}

test("Schedule an order for pickup later", async () => {
    const store = await setupPosEnv();
    store.config.ship_later = true;
    const order = await getFilledOrder(store);
    order.setPartner(store.models["res.partner"].get(3)); // no address
    order.addPaymentline(store.models["pos.payment.method"].getFirst());
    await mountWithCleanup(PaymentScreen, { props: { orderUuid: order.uuid } });
    const validation = new OrderPaymentValidation({ pos: store, orderUuid: order.uuid });

    await scheduleOrder("Pick up later");
    expect(order.pickup_later).toBe(true);
    expect(await validation.isOrderValid(false)).toBe(true);

    await scheduleOrder("Ship later");
    expect(order.pickup_later).toBe(false);
    expect(await validation.isOrderValid(false)).toBe(false);
    await waitFor(".modal:contains('Incorrect address for shipping')");
});
