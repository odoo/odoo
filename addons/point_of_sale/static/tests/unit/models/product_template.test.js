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
