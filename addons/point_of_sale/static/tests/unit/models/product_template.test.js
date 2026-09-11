import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { normalize } from "@web/core/l10n/utils";

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

test("product template searchString includes single-value attribute value names", async () => {
    const store = await setupPosEnv();
    const productTmpl = store.models["product.template"].create({
        id: 9993,
        name: "Template Single Value",
        attribute_line_ids: [
            store.models["product.template.attribute.line"].create({
                id: 9994,
                product_template_value_ids: [
                    store.models["product.template.attribute.value"].create({
                        id: 9995,
                        name: "SingleAttrValueName",
                    }),
                ],
            }),
        ],
    });
    expect(productTmpl.searchString).toMatch("singleattrvaluename");
});

test("product template searchString is invalidated when an attribute value is updated", async () => {
    const store = await setupPosEnv();
    const productTmpl = store.models["product.template"].get(51);
    const ptav = productTmpl.attribute_line_ids[0].product_template_value_ids[0];

    expect(productTmpl.searchString).toMatch(normalize(ptav.name));

    store.models.connectNewData({
        "product.template.attribute.value": [
            {
                id: ptav.id,
                name: "RenamedAttrValue",
                attribute_id: ptav.attribute_id.id,
                attribute_line_id: ptav.attribute_line_id?.id,
            },
        ],
    });

    expect(productTmpl.searchString).toMatch("renamedattrvalue");
});
