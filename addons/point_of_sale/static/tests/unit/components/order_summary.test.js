import { test, expect, describe } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { setupPosEnv, getFilledOrder } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

describe("order_summary.js", () => {
    test("getNewLine", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const orderSummary = await mountWithCleanup(OrderSummary, {});
        order.getSelectedOrderline().uiState.savedQuantity = 5;
        const newLine = orderSummary.getNewLine();
        expect(newLine.order_id.id).toBe(order.id);
        expect(newLine.qty).toBe(0);
    });
});
