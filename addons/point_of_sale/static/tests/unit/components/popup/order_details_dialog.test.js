import { test, expect, waitFor } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder, mountPosDialog } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { OrderDetailsDialog } from "@point_of_sale/app/screens/ticket_screen/order_details_dialog/order_details_dialog";

definePosModels();

test("OrderDetailsDialog opens without currency error", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);

    const cashPaymentMethod = store.models["pos.payment.method"].get(1);
    order.addPaymentline(cashPaymentMethod);

    const dialog = await mountPosDialog(OrderDetailsDialog, {
        order,
        editPayment: () => {},
        close: () => {},
    });
    await waitFor(".o_dialog");

    expect(".o_dialog").toHaveCount(1);
    expect(".modal-header").toHaveText("Order Details: " + order.tracking_number);
    expect(typeof dialog.formatCurrency(order.amount_total)).toEqual("string");
});
