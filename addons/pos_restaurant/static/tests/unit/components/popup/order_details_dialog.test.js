import { test, expect, waitFor, queryOne } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder, mountPosDialog } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { OrderDetailsDialog } from "@point_of_sale/app/screens/ticket_screen/order_details_dialog/order_details_dialog";

const { DateTime } = luxon;

definePosModels();

test("order details dialog shows clock and duration for table order", async () => {
    const store = await setupPosEnv();
    const table = store.models["restaurant.table"].get(4);
    const order = await getFilledOrder(store, { table_id: table });
    order.create_date = DateTime.now().minus({ minutes: 5 });
    await mountPosDialog(OrderDetailsDialog, {
        order,
        editPayment: () => {},
        close: () => {},
    });
    await waitFor(".o_dialog");
    expect(".modal-content .fa-clock-o").toHaveCount(1);
    expect(queryOne(".modal-content .position-absolute.start-50 span").textContent.trim()).toBe(
        "5'"
    );
});
