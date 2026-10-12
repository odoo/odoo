import { describe, expect, test } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { OrderDetailsDialog } from "@point_of_sale/app/screens/ticket_screen/order_details_dialog/order_details_dialog";

definePosModels();

describe("order_details_dialog.js", () => {
    test("getTableInfo returns order.table_id when present", async () => {
        const store = await setupPosEnv();
        const table = store.models["restaurant.table"].get(2);
        const order = store.addNewOrder({ table_id: table });
        const orderDetailsDialog = await mountWithCleanup(OrderDetailsDialog, {
            props: { order, close: () => {}, editPayment: () => {} },
        });

        expect(orderDetailsDialog.getTableInfo()?.id).toBe(2);
    });

    test("getTableInfo returns false when order has no table", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder({ table_id: false });
        const orderDetailsDialog = await mountWithCleanup(OrderDetailsDialog, {
            props: { order, close: () => {}, editPayment: () => {} },
        });

        expect(orderDetailsDialog.getTableInfo()?.id).toBe(undefined);
    });
});
