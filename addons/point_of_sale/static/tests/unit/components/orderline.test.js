import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { setupPosEnv } from "../utils";
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

    expect(comp.line.id).toEqual(line.id);
    expect(comp.taxGroup).toBeEmpty();
    expect(comp.formatCurrency(comp.line.price_subtotal_incl)).toBe("$\u00a010.35");
    expect(comp.getInternalNotes()).toEqual([
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
