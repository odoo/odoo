import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { expectFormattedPrice, setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

test("orderline.js", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product = store.models["product.template"].get(5);
    const line = await store.addLineToOrder(
        {
            product_tmpl_id: product,
            qty: 3,
            note: '[{"text":"Test 1","colorIndex":0},{"text":"Test 2","colorIndex":0}]',
        },
        order
    );

    const comp = await mountWithCleanup(Orderline, {
        props: { line },
    });
    const lineData = comp.lineScreenValues;
    expect(comp.line.id).toEqual(line.id);
    expectFormattedPrice(comp.line.currencyDisplayPrice, "$ 10.35");
    expect(lineData.internalNote).toEqual([
        {
            text: "Test 1",
            colorIndex: 0,
        },
        {
            text: "Test 2",
            colorIndex: 0,
        },
    ]);
});
