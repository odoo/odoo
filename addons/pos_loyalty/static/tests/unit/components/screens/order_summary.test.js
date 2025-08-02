import { describe, test, expect, beforeEach } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

let store;
let models;
let order;

beforeEach(async () => {
    store = await setupPosEnv();
    models = store.models;
    order = store.addNewOrder();
});

describe("order_summary.js", () => {
    test("_updateGiftCardOrderline should update gift card orderline with new code and points", async () => {
        const template = models["product.template"].get(1);
        const product = models["product.product"].get(1);
        const program = models["loyalty.program"].get(3);
        const card = models["loyalty.card"].get(1);

        await store.addLineToOrder(
            {
                product_tmpl_id: template,
                qty: 2,
                price_unit: 10,
            },
            order
        );

        const points = product.lst_price;

        order.uiState.couponPointChanges[card.id] = {
            coupon_id: card.id,
            program_id: program.id,
            product_id: product.id,
            points: points,
            manual: false,
        };

        const component = await mountWithCleanup(OrderSummary, {});

        await component._updateGiftCardOrderline("ABC123", points);

        const updatedLine = order.getSelectedOrderline();

        expect(updatedLine.gift_code).toBe("ABC123");
        expect(updatedLine.product_id.id).toBe(product.id);
        expect(updatedLine.getQuantity()).toBe(1);
        expect(order.uiState.couponPointChanges[card.id]).toBe(undefined);
    });
});
