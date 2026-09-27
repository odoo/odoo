import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
definePosModels();

test("groups upsell suggestions and keeps only free combo values", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    await store.addLineToOrder({ product_tmpl_id: 8 }, order);
    await store.addLineToOrder({ product_tmpl_id: 10 }, order);

    const comboSuggestion = store.comboSuggestion;
    const potentialCombos = comboSuggestion.getPotentialCombos(order);

    expect(potentialCombos).toHaveLength(1);
    expect(potentialCombos[0].upsell).toBe(true);
    expect(potentialCombos[0].product.id).toBe(7);
    expect(
        comboSuggestion
            .getComboValuesFromCombination(potentialCombos[0].combinations[0])
            .map((item) => item.combo_item_id.id)
    ).toEqual([1, 3]);
});

test("builds combo payloads for direct non-upsell combos", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const comboProduct = store.models["product.product"].get(7);
    const combo1 = store.models["product.combo"].get(1);
    combo1.is_upsell = false;
    combo1.qty_free = combo1.qty_max = 1;

    await store.addLineToOrder({ product_tmpl_id: 8 }, order);
    await store.addLineToOrder({ product_tmpl_id: 10 }, order);

    const comboSuggestion = store.comboSuggestion;
    const matchingCombo = comboSuggestion.getApplicableProductCombo(order, "combinations")[0];

    expect(matchingCombo.product.id).toBe(comboProduct.id);
    expect(matchingCombo.combinationsQty).toBe(1);
    expect(
        comboSuggestion
            .getComboValuesFromCombination(matchingCombo.combinations[0])
            .map((item) => item.combo_item_id.id)
    ).toEqual([1, 3]);
});
