import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

test("combo price remains consistent when recomputing prices", async () => {
    const store = await setupPosEnv();
    const pricelistA = store.models["product.pricelist"].get(1);
    const pricelist90 = store.models["product.pricelist"].get(3);

    const template = store.models["product.template"].get(7);
    const comboItem1 = store.models["product.combo.item"].get(1);
    const comboItem3 = store.models["product.combo.item"].get(3);

    const order = store.addNewOrder();
    order.setPricelist(pricelistA);

    await store.addLineToOrder(
        {
            product_tmpl_id: template,
            payload: [
                [{ combo_item_id: comboItem1, qty: 1 }],
                [{ combo_item_id: comboItem3, qty: 1 }],
            ],
            qty: 2,
        },
        order
    );

    const comboParentLine = order.lines.find(
        (l) => l.product_id.product_tmpl_id.id === template.id
    );

    expect(comboParentLine.getQuantity()).toBe(2);
    expect(comboParentLine.price_unit).toBe(0);

    const childLines = order.lines.filter((l) => l.combo_parent_id?.uuid === comboParentLine.uuid);
    expect(childLines).toHaveLength(2);

    const item1Line = childLines.find((l) => l.combo_item_id.id === 1);
    const item3Line = childLines.find((l) => l.combo_item_id.id === 3);

    expect(item1Line.getQuantity()).toBe(2);
    expect(item1Line.price_unit).toBe(3);

    expect(item3Line.getQuantity()).toBe(2);
    expect(item3Line.price_unit).toBe(200);

    // Total = (0*2) + (3*2) + (200*2) = 0 + 6 + 400 = 406.
    // Tax 25% -> 406 * 1.25 = 507.5.
    expect(order.priceIncl).toBe(507.5);

    order.setPricelist(pricelist90);

    expect(comboParentLine.price_unit).toBe(0);
    expect(item1Line.price_unit).toBe(100);

    expect(item3Line.price_unit).toBeGreaterThan(0);

    expect(order.priceIncl).not.toBe(507.5);
    expect(order.priceIncl).toBeGreaterThan(0);
});
