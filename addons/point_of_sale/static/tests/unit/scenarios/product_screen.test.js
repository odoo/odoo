import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { localization as l10n } from "@web/core/l10n/localization";
import {
    setupPosEnv,
    createAttributeLine,
    createAttributeValue,
    expectFormattedPrice,
    createAttribute,
} from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { CategorySelector } from "@point_of_sale/app/components/category_selector/category_selector";

definePosModels();

test("MultiProductOptionsTour: multi product options shows all values", async () => {
    const store = await setupPosEnv();
    const attribute = createAttribute(store, "Multi", "multi");
    const value1 = createAttributeValue(store, attribute, "Value 1");
    const value2 = createAttributeValue(store, attribute, "Value 2");
    const line = createAttributeLine(store, attribute, [value1, value2]);

    const product = store.models["product.template"].create({
        name: "Product A",
        available_in_pos: true,
        active: true,
        type: "consu",
        uom_id: store.models["uom.uom"].get(1),
        tracking: "none",
        taxes_id: [],
        product_variant_ids: [store.models["product.product"].get(5)],
        attribute_line_ids: [line],
        combo_ids: [],
        pos_categ_ids: [store.models["pos.category"].get(1)],
    });

    expect(Object.keys(product.isConfigurable()).length > 0).toBe(true);
    expect(product.needToConfigure()).toBe(true);
    expect(product.attribute_line_ids[0].product_template_value_ids.map((v) => v.name)).toEqual([
        "Value 1",
        "Value 2",
    ]);
});

test("DecimalCommaOrderlinePrice: decimal comma orderline price format", async () => {
    const store = await setupPosEnv();
    l10n.decimalPoint = ",";
    l10n.thousandsSep = ".";
    store.addNewOrder();
    const line = await store.addLineToCurrentOrder(
        {
            product_tmpl_id: store.models["product.template"].get(5),
            qty: 5,
            price_unit: 1453.53,
            tax_ids: [],
        },
        {},
        false
    );
    expect(line.displayPrice).toBe(7267.65);
    expectFormattedPrice(line.currencyDisplayPrice, "$\u00a07.267,65");
});

test("PosCategoriesOrder: pos categories keep sequence and hierarchy", async () => {
    const store = await setupPosEnv();
    const component = await mountWithCleanup(CategorySelector, {
        props: {},
    });
    expect(component.getCategoriesAndSub().map((c) => c.name)).toEqual([
        "Category 1",
        "Category 2",
        "Food",
    ]);
    store.setSelectedCategory(1);
    expect(component.getCategoriesAndSub().map((c) => c.name)).toEqual([
        "Category 1",
        "Category 2",
        "Food",
    ]);
    store.setSelectedCategory(3);
    expect(component.getCategoriesAndSub().map((c) => c.name)).toEqual([
        "Category 1",
        "Category 2",
        "Food",
        "Burger",
        "Pizza",
    ]);
});
