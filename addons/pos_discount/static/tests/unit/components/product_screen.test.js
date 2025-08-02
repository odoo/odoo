import { describe, expect, test } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

const { DateTime } = luxon;

definePosModels();

describe("pos_discount product_screen.js", () => {
    test("getNumpadButtons", async () => {
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
        const productScreen = await mountWithCleanup(ProductScreen, {
            props: { orderUuid: order.uuid },
        });
        store.selectOrderLine(order, orderline);
        const receivedButtonsDisableStatue = productScreen
            .getNumpadButtons()
            .filter((button) => ["quantity", "discount"].includes(button.value))
            .map((button) => button.disabled);

        expect(store.isDiscountLineSelected).toBe(true);
        expect(receivedButtonsDisableStatue).toEqual([true, true]);
    });
});
