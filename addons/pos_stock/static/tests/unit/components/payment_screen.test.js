import { test, expect } from "@odoo/hoot";
import { click, waitFor } from "@odoo/hoot-dom";
import { mountWithCleanup, mockService, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosStockModels } from "../data/generate_model_definitions";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
const { DateTime } = luxon;

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

test("Pickup later flow schedules, validates, and prioritizes a paid order", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const noAddressPartner = store.models["res.partner"].get(3);
    order.partner_id = noAddressPartner;
    order.addPaymentline(store.models["pos.payment.method"].getFirst());
    const paymentScreen = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });

    await paymentScreen.toggleShippingDatePicker();
    await waitFor(".modal");
    await click(".modal button:contains('Pick up later')");
    await click(".modal button:contains('Confirm')");

    expect(order.pickup_later).toBe(true);
    expect(order.shipping_date.toISODate()).toBe(DateTime.now().toISODate());

    const validation = new OrderPaymentValidation({ pos: store, orderUuid: order.uuid });
    const dialogTitles = [];
    patchWithCleanup(store.dialog, {
        add(_component, props) {
            dialogTitles.push(props.title);
        },
    });
    expect(await validation.isOrderValid(false)).toBe(true);
    expect(dialogTitles).not.toInclude("Incorrect address for shipping");

    order.partner_id = false;
    expect(validation.shouldAskForPartner()).toBe(true);
    order.partner_id = noAddressPartner;

    await paymentScreen.toggleShippingDatePicker();
    await waitFor(".modal");
    await click(".modal button:contains('Ship later')");
    await click(".modal button:contains('Confirm')");
    expect(order.pickup_later).toBe(false);
    expect(await validation.isOrderValid(false)).toBe(false);
    expect(dialogTitles).toInclude("Incorrect address for shipping");

    const today = DateTime.now().startOf("day");
    order.pickup_later = true;
    order.state = "paid";
    const regularOrder = await getFilledOrder(store);
    regularOrder.state = "paid";
    regularOrder.date_order = today;
    order.date_order = today.minus({ days: 3 });
    const ticketScreen = await mountWithCleanup(TicketScreen);
    ticketScreen.state.filter = "SYNCED";
    const sortedOrders = ticketScreen.getFilteredOrderList();
    expect(sortedOrders[0]).toBe(order);
    expect(sortedOrders).toHaveLength(2);
    expect(sortedOrders[1]).toBe(regularOrder);
});
