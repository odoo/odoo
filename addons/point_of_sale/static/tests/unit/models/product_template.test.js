import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

test("product with single 'is_custom' attr is configurable", async () => {
    const store = await setupPosEnv();
    const product = store.models["product.template"].get(51);
    product.attribute_line_ids = [product.attribute_line_ids[1]];
    const ptv = product.attribute_line_ids[0].product_template_value_ids;
    expect(ptv.length).toBe(1);
    expect(ptv[0].is_custom).toBe(true);
    expect(!!product.isConfigurable()).toBe(true);
});

test("product with single 'multi' display_type attr with single choice is configurable", async () => {
    const store = await setupPosEnv();
    const product = store.models["product.template"].get(52);
    const line = product.attribute_line_ids[0];
    const ptv = line.product_template_value_ids;
    expect(ptv.length).toBe(1);
    expect(ptv[0].is_custom).toBe(false);
    expect(line.attribute_id.display_type).toBe("multi");
    expect(!!product.isConfigurable()).toBe(true);
});

test("variant lookup includes single-value attribute lines", async () => {
    const store = await setupPosEnv();
    // "Single attribute": its only variant attribute line has a single value ("Male").
    const product = store.models["product.template"].get(152);
    const variant = store.models["product.product"].get(153);
    variant.update({ product_tmpl_id: product });
    const value = store.models["product.template.attribute.value"].get(12);

    expect(product.getVariantForCombination([value])).toBe(variant);
});
