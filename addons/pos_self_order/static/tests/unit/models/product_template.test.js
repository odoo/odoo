import { test, expect } from "@odoo/hoot";
import { setupSelfPosEnv } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

test("product with single 'is_custom' attr", async () => {
    const store = await setupSelfPosEnv();
    const product = store.models["product.template"].get(51);
    product.attribute_line_ids = [product.attribute_line_ids[1]];
    const ptv = product.attribute_line_ids[0].product_template_value_ids;
    expect(ptv.length).toBe(1);
    expect(ptv[0].is_custom).toBe(true);

    store.config.self_ordering_mode = "mobile";
    expect(Boolean(product.isConfigurableForSelfOrder)).toBe(true);

    store.config.self_ordering_mode = "kiosk";
    expect(Boolean(product.isConfigurableForSelfOrder)).toBe(false);
});

test("product with single 'multi' display_type attr with single choice is configurable in both modes", async () => {
    const store = await setupSelfPosEnv();
    const product = store.models["product.template"].get(52);
    const line = product.attribute_line_ids[0];
    const ptv = line.product_template_value_ids;
    expect(ptv.length).toBe(1);
    expect(ptv[0].is_custom).toBe(false);
    expect(line.attribute_id.display_type).toBe("multi");

    store.config.self_ordering_mode = "kiosk";
    expect(Boolean(product.isConfigurableForSelfOrder)).toBe(true);

    store.config.self_ordering_mode = "mobile";
    expect(Boolean(product.isConfigurableForSelfOrder)).toBe(true);
});

test("showComboSelectionPage", async () => {
    const store = await setupSelfPosEnv();
    const models = store.models;
    const product = models["product.template"].get(7);
    const combo = models["product.combo"].get(2);
    product.combo_ids = [2];

    const defaultReturnValue = { show: true, selectedCombos: [] };
    expect(product.showComboSelectionPage()).toMatchObject(defaultReturnValue);
    // only One choice
    models["product.combo.item"].get(3).delete();
    const showCombo = product.showComboSelectionPage();
    expect(showCombo.show).toBe(false);
    expect(showCombo.selectedCombos).toHaveLength(1);
    expect(showCombo.selectedCombos[0].combo_item_id.id).toBe(4);
    // qty_max is more than one
    combo.qty_max = 3;
    expect(product.showComboSelectionPage()).toMatchObject(defaultReturnValue);
});
