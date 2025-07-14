import { describe, expect, test } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

const { DateTime } = luxon;

definePosModels();

describe("pos_discount pos_order_line.js", () => {
    test("isDiscountLine", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = await getFilledOrder(store);
        const product = models["product.template"].get(151);
        const date = DateTime.now();
        const orderline = await store.addLineToOrder(
            {
                product_tmpl_id: product,
                qty: 1,
                price_unit: order.amount_total * -0.1,
                write_date: date,
                create_date: date,
            },
            order
        );
        expect(orderline.isDiscountLine).toBe(true);
        expect(store.isDiscountLineSelected).toBe(true);
    });
});
