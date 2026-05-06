import { test, expect, describe } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { definePosSelfModels } from "../../../data/generate_model_definitions";
import { setupPoSEnvForSelfOrder } from "../../../utils";
import { OrderDetailsDialog } from "@point_of_sale/app/screens/ticket_screen/order_details_dialog/order_details_dialog";

definePosSelfModels();

describe("order_details_dialog.js", () => {
    test("getTableInfo returns order.table_id when present", async () => {
        const store = await setupPoSEnvForSelfOrder();
        const table = store.models["restaurant.table"].getFirst();
        const order = store.addNewOrder({ table_id: table });
        const orderDetailsDialog = await mountWithCleanup(OrderDetailsDialog, {
            props: { order, close: () => {}, editPayment: () => {} },
        });

        expect(orderDetailsDialog.getTableInfo()?.id).toBe(table.id);
    });

    test("getTableInfo returns self_ordering_table_id when table_id is falsy", async () => {
        const store = await setupPoSEnvForSelfOrder();
        const table = store.models["restaurant.table"].getFirst();
        const order = store.addNewOrder({ self_ordering_table_id: table, table_id: false });
        const orderDetailsDialog = await mountWithCleanup(OrderDetailsDialog, {
            props: { order, close: () => {}, editPayment: () => {} },
        });

        expect(orderDetailsDialog.getTableInfo()?.id).toBe(table.id);
    });

    test("getTableInfo returns false when neither table_id nor self_ordering_table_id", async () => {
        const store = await setupPoSEnvForSelfOrder();
        const order = store.addNewOrder({ table_id: false, self_ordering_table_id: false });
        const orderDetailsDialog = await mountWithCleanup(OrderDetailsDialog, {
            props: { order, close: () => {}, editPayment: () => {} },
        });

        expect(orderDetailsDialog.getTableInfo()?.id).toBe(undefined);
    });
});
