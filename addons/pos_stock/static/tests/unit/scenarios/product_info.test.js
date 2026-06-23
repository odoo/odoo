import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosStockModels } from "@pos_stock/../tests/unit/data/generate_model_definitions";

definePosStockModels();

test("test_product_info_product_inventory: product info returns variant inventory quantities", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    const variant1 = store.models["product.product"].create({
        id: 901,
        product_tmpl_id: store.models["product.template"].get(5),
        display_name: "Inventory Product 1",
        barcode: "product_variant_0",
        lst_price: 10,
        standard_price: 1,
        product_template_attribute_value_ids: [],
        product_template_variant_value_ids: [],
        product_tag_ids: [],
        pos_categ_ids: [1],
    });
    const variant2 = store.models["product.product"].create({
        id: 902,
        product_tmpl_id: store.models["product.template"].get(5),
        display_name: "Inventory Product 2",
        barcode: "product_variant_1",
        lst_price: 10,
        standard_price: 1,
        product_template_attribute_value_ids: [],
        product_template_variant_value_ids: [],
        product_tag_ids: [],
        pos_categ_ids: [1],
    });

    const template = store.models["product.template"].create({
        id: 901,
        name: "Inventory Product",
        display_name: "Inventory Product",
        available_in_pos: true,
        active: true,
        type: "consu",
        is_storable: true,
        uom_id: store.models["uom.uom"].get(1),
        tracking: "none",
        taxes_id: [],
        combo_ids: [],
        attribute_line_ids: [],
        pos_categ_ids: [store.models["pos.category"].get(1)],
        product_variant_ids: [variant1, variant2],
    });

    const originalCall = store.data.call.bind(store.data);
    store.data.call = async (model, method, args) => {
        if (model === "product.template" && method === "get_product_info_pos") {
            const variantId = args[4];
            const qty = variantId === 901 ? 100 : 200;
            return { variants: [{ id: variantId, qty_available: qty }] };
        }
        return await originalCall(model, method, args);
    };

    const info1 = await store.getProductInfo(template, 1, 0, variant1);
    const info2 = await store.getProductInfo(template, 1, 0, variant2);

    expect(info1.productInfo.variants[0].qty_available).toBe(100);
    expect(info2.productInfo.variants[0].qty_available).toBe(200);
});
