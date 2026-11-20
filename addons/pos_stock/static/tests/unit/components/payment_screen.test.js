import { test, expect } from "@odoo/hoot";
import { animationFrame, click, waitFor } from "@odoo/hoot-dom";
import { mountWithCleanup, mockService, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosStockModels } from "../data/generate_model_definitions";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { DatePickerPopup } from "@pos_stock/app/components/popups/date_picker_popup/date_picker_popup";

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

async function scheduleOrder({ pickup }) {
    await click(".o_schedule_later_button");
    await waitFor(".modal");
    await click(pickup ? ".modal .o_pickup_later_button" : ".modal .o_ship_later_button");
    await click(".modal .btn:contains('Confirm')");
    await animationFrame();
}

test("Pick up later does not require a customer address", async () => {
    const store = await setupPosEnv();
    store.config.ship_later = true;
    const order = await getFilledOrder(store);
    order.partner_id = store.models["res.partner"].get(3); // no address
    order.addPaymentline(store.models["pos.payment.method"].getFirst());
    await mountWithCleanup(PaymentScreen, { props: { orderUuid: order.uuid } });
    const dialogTitles = [];
    patchWithCleanup(store.dialog, {
        add(component, props) {
            if (component === DatePickerPopup) {
                return super.add(...arguments);
            }
            dialogTitles.push(props.title);
        },
    });
    const validation = new OrderPaymentValidation({ pos: store, orderUuid: order.uuid });

    await scheduleOrder({ pickup: true });
    expect(order.pickup_later).toBe(true);
    expect(order.shipping_date.toISODate()).toBe(DateTime.now().toISODate());
    expect(".o_schedule_later_button.highlight:contains('Schedule for later')").toHaveCount(1);
    expect(await validation.isOrderValid(false)).toBe(true);
    expect(dialogTitles).toEqual([]);

    await scheduleOrder({ pickup: false });
    expect(order.pickup_later).toBe(false);
    expect(await validation.isOrderValid(false)).toBe(false);
    expect(dialogTitles).toEqual(["Incorrect address for shipping"]);
});

test("Paid orders due for pickup are listed first", async () => {
    const store = await setupPosEnv();
    const today = DateTime.now().startOf("day");
    const makePaidOrder = async (date, values = {}) => {
        const order = await getFilledOrder(store);
        Object.assign(order, { state: "paid", date_order: date, ...values });
        return order;
    };
    const pickupToday = await makePaidOrder(today.minus({ days: 4 }), {
        pickup_later: true,
        shipping_date: today,
    });
    const pickupYesterday = await makePaidOrder(today.minus({ days: 3 }), {
        pickup_later: true,
        shipping_date: today.minus({ days: 1 }),
    });
    const pickupTomorrow = await makePaidOrder(today.minus({ days: 2 }), {
        pickup_later: true,
        shipping_date: today.plus({ days: 1 }),
    });
    const shipToday = await makePaidOrder(today.minus({ days: 1 }), { shipping_date: today });
    const regular = await makePaidOrder(today);

    const ticketScreen = await mountWithCleanup(TicketScreen);
    ticketScreen.state.filter = "SYNCED";

    // Due pickups (today and overdue) first, each group keeps the date order
    expect(ticketScreen.getFilteredOrderList()).toEqual([
        pickupYesterday,
        pickupToday,
        regular,
        shipToday,
        pickupTomorrow,
    ]);
});
