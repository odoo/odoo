import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { setupPosEnv, dialogActions } from "../../utils";
import { definePosModels } from "../../data/generate_model_definitions";

definePosModels();

const setupCombo = (store, { upsellItemIds, includedItemIds }) => {
    const models = store.models;
    const upsell = models["product.combo"].get(1);
    upsell.qty_max = 1;
    upsell.combo_item_ids = upsellItemIds.map((id) => models["product.combo.item"].get(id));
    const included = models["product.combo"].get(2);
    included.combo_item_ids = includedItemIds.map((id) => models["product.combo.item"].get(id));
    return models["product.template"].get(7);
};

const lineNames = (order) => order.lines.map((line) => line.product_id.display_name);

test("an upsell choice holding a single product is still offered", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    // Both choices hold a single product: only the included one may be preselected.
    const comboTmpl = setupCombo(store, { upsellItemIds: [1], includedItemIds: [3] });

    await dialogActions(
        () => store.addLineToCurrentOrder({ product_tmpl_id: comboTmpl, qty: 1 }),
        [
            () => {
                expect(".combo-item:contains('Wood chair')").toHaveCount(1);
                expect(".combo-item.selected:contains('Wood chair')").toHaveCount(0);
                expect(".combo-item.selected:contains('Wood desk')").toHaveCount(1);
            },
            () => click(".confirm"),
        ]
    );

    expect(lineNames(order)).toEqual(["Product combo", "Wood desk"]);
    expect(order.priceIncl).toBe(3.75);
});

test("an upsell choice is unselected when its selected product is clicked again", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const comboTmpl = setupCombo(store, { upsellItemIds: [1, 2], includedItemIds: [3, 4] });

    await dialogActions(
        () => store.addLineToCurrentOrder({ product_tmpl_id: comboTmpl, qty: 1 }),
        [
            () => click("#article_product_8"), // Wood chair, upsell
            () => expect(".combo-item.selected:contains('Wood chair')").toHaveCount(1),
            () => click("#article_product_8"),
            () => expect(".combo-item.selected:contains('Wood chair')").toHaveCount(0),
            () => click("#article_product_9"), // Steel chair, same upsell choice
            () => click("#article_product_9"),
            () => expect(".combo-item.selected").toHaveCount(0),
            () => click("#article_product_10"), // Wood desk, included choice
            () => click("#article_product_10"),
            () => expect(".combo-item.selected:contains('Wood desk')").toHaveCount(1),
            () => click(".confirm"),
        ]
    );

    expect(lineNames(order)).toEqual(["Product combo", "Wood desk"]);
    expect(order.priceIncl).toBe(3.75);
});

test("an included choice holding a single product stays preselected", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const comboTmpl = setupCombo(store, { upsellItemIds: [1, 2], includedItemIds: [3] });

    await dialogActions(
        () => store.addLineToCurrentOrder({ product_tmpl_id: comboTmpl, qty: 1 }),
        [
            () => expect(".combo-item.selected:contains('Wood desk')").toHaveCount(1),
            () => click("#article_product_10"),
            () => expect(".combo-item.selected:contains('Wood desk')").toHaveCount(1),
            () => click(".confirm"),
        ]
    );

    expect(lineNames(order)).toEqual(["Product combo", "Wood desk"]);
});
