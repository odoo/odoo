import { test, expect } from "@odoo/hoot";
import { tick, waitFor, animationFrame } from "@odoo/hoot-dom";
import { mountWithCleanup, contains } from "@web/../tests/web_test_helpers";
import { click } from "@mail/../tests/mail_test_helpers";
import { setupPosEnv, createAttribute, createAttributeValue, createAttributeLine } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { ProductConfiguratorPopup } from "@point_of_sale/app/components/popups/product_configurator_popup/product_configurator_popup";
import { ComboConfiguratorPopup } from "@point_of_sale/app/components/popups/combo_configurator_popup/combo_configurator_popup";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { createTax } from "../accounting/utils";

definePosModels();

const createConfigurableChair = (store) => {
    const color = createAttribute(store, "Color", "color");
    const material = createAttribute(store, "Material", "select");
    const fabric = createAttribute(store, "Fabrics", "radio");
    const options = createAttribute(store, "Options", "multi");

    const blue = createAttributeValue(store, color, "Blue", { id: 9801 });
    const wood = createAttributeValue(store, material, "Wood", { id: 9802 });
    const other = createAttributeValue(store, fabric, "Other", { id: 9803, isCustom: true });
    const cushion = createAttributeValue(store, options, "Cushion", { id: 9804 });
    const headrest = createAttributeValue(store, options, "Headrest", { id: 9805 });

    const template = store.models["product.template"].get(5);
    template.update({
        attribute_line_ids: [
            createAttributeLine(store, color, [blue]),
            createAttributeLine(store, material, [wood]),
            createAttributeLine(store, fabric, [other]),
            createAttributeLine(store, options, [cushion, headrest]),
        ],
        name: "Configurable Chair",
        display_name: "Configurable Chair",
    });

    return {
        template,
        values: { blue, wood, other, cushion, headrest },
        payload: {
            attribute_value_ids: [blue.id, wood.id, other.id, cushion.id, headrest.id],
            attribute_custom_values: { [other.id]: "Azerty" },
            price_extra: 0,
            qty: 1,
        },
    };
};

const createSimpleComboItem = (store, id, name) => {
    const productTmpl = store.models["product.template"].create({
        id,
        name,
        display_name: name,
        available_in_pos: true,
        active: true,
        type: "consu",
        uom_id: store.models["uom.uom"].get(1),
        tracking: "none",
        taxes_id: [],
        product_variant_ids: [],
        attribute_line_ids: [],
        combo_ids: [],
        pos_categ_ids: [store.models["pos.category"].get(1)],
    });
    const product = store.models["product.product"].create({
        id,
        name,
        product_tmpl_id: productTmpl,
        display_name: name,
        lst_price: 10,
        standard_price: 0,
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [],
        product_template_variant_value_ids: [],
        product_tag_ids: [],
        pos_categ_ids: [1],
    });
    return store.models["product.combo.item"].create({
        id: id + 100,
        combo_id: false,
        product_id: product,
        extra_price: 0,
    });
};

const createComboProduct = (store, configurableProduct) => {
    const product2 = createSimpleComboItem(store, 9821, "Combo Product 2");
    const configurableChair = store.models["product.combo.item"].create({
        id: 9822,
        combo_id: false,
        product_id: configurableProduct.template.product_variant_ids[0],
        extra_price: 0,
    });
    const product6 = createSimpleComboItem(store, 9823, "Combo Product 6");
    const combo1 = store.models["product.combo"].create({
        id: 9861,
        name: "Combo 1",
        combo_item_ids: [product2],
        base_price: 10,
        qty_free: 1,
        qty_max: 1,
        is_upsell: false,
        sequence: 1,
    });
    const combo2 = store.models["product.combo"].create({
        id: 9862,
        name: "Combo 2",
        combo_item_ids: [configurableChair],
        base_price: 10,
        qty_free: 1,
        qty_max: 2,
        is_upsell: false,
        sequence: 2,
    });
    const combo3 = store.models["product.combo"].create({
        id: 9863,
        name: "Combo 3",
        combo_item_ids: [product6],
        base_price: 10,
        qty_free: 1,
        qty_max: 1,
        is_upsell: false,
        sequence: 3,
    });
    product2.combo_id = combo1;
    configurableChair.combo_id = combo2;
    product6.combo_id = combo3;

    const comboVariant = store.models["product.product"].create({
        id: 9864,
        name: "Office Combo",
        product_tmpl_id: store.models["product.template"].get(7),
        display_name: "Office Combo",
        lst_price: 30,
        standard_price: 0,
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [],
        product_template_variant_value_ids: [],
        product_tag_ids: [],
        pos_categ_ids: [1],
    });
    const comboTemplate = store.models["product.template"].create({
        id: 9865,
        name: "Office Combo",
        display_name: "Office Combo",
        available_in_pos: true,
        active: true,
        type: "combo",
        uom_id: store.models["uom.uom"].get(1),
        tracking: "none",
        taxes_id: [],
        product_variant_ids: [comboVariant],
        attribute_line_ids: [],
        combo_ids: [combo1, combo2, combo3],
        pos_categ_ids: [store.models["pos.category"].get(1)],
    });
    comboVariant.product_tmpl_id = comboTemplate;

    return {
        template: comboTemplate,
        items: { product2, configurableChair, product6 },
    };
};

const expectConfiguredChairLine = (line) => {
    expect(line.getFullProductName()).toBe(
        "Configurable Chair (Blue, Wood, Fabrics: Other: Azerty, Cushion, Headrest)"
    );
    expect(line.selectedAttributes[line.attribute_value_ids[0].attribute_id.id].selected.name).toBe(
        "Blue"
    );
    expect(line.custom_attribute_value_ids[0].custom_product_template_attribute_value_id.name).toBe(
        "Other"
    );
    expect(line.custom_attribute_value_ids[0].custom_value).toBe("Azerty");
};

test("test_custom_attribute_alone_displayed: custom attribute alone displayed", async () => {
    const store = await setupPosEnv();
    const attribute = createAttribute(store, "Custom", "radio");
    const customValue = createAttributeValue(store, attribute, "Custom", { isCustom: true });
    const product = store.models["product.template"].get(5);
    product.update({
        attribute_line_ids: [createAttributeLine(store, attribute, [customValue])],
    });

    expect(product.needToConfigure()).toBe(true);
    expect(product.attribute_line_ids[0].product_template_value_ids[0].is_custom).toBe(true);
});

test("test_combo_variant_mix: combo variant mix uses selected variant and attributes", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const colorAttribute = createAttribute(store, "Color", "color");
    const sizeAttribute = createAttribute(store, "Size", "radio", "always");

    const blue = createAttributeValue(store, colorAttribute, "Blue", { id: 9501 });
    const small = createAttributeValue(store, sizeAttribute, "Small", { id: 9502 });
    const large = createAttributeValue(store, sizeAttribute, "Large", { id: 9503 });

    const variantSmall = store.models["product.product"].create({
        id: 9510,
        product_tmpl_id: store.models["product.template"].get(5),
        display_name: "Test Product (Small)",
        lst_price: 10,
        standard_price: 0,
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [small],
        product_template_variant_value_ids: [small],
        product_tag_ids: [],
        pos_categ_ids: [1],
    });
    const variantLarge = store.models["product.product"].create({
        id: 9511,
        product_tmpl_id: store.models["product.template"].get(5),
        display_name: "Test Product (Large)",
        lst_price: 10,
        standard_price: 0,
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [large],
        product_template_variant_value_ids: [large],
        product_tag_ids: [],
        pos_categ_ids: [1],
    });

    store.models["product.template"].create({
        id: 9520,
        name: "Test Product",
        display_name: "Test Product",
        available_in_pos: true,
        active: true,
        type: "consu",
        uom_id: store.models["uom.uom"].get(1),
        tracking: "none",
        taxes_id: [],
        product_variant_ids: [variantSmall, variantLarge],
        combo_ids: [],
        pos_categ_ids: [store.models["pos.category"].get(1)],
        attribute_line_ids: [
            createAttributeLine(store, colorAttribute, [blue]),
            createAttributeLine(store, sizeAttribute, [small, large]),
        ],
    });

    const combo = store.models["product.combo"].create({
        id: 9530,
        name: "Test Combo",
        base_price: 20,
        qty_free: 1,
        qty_max: 1,
        is_upsell: false,
        combo_item_ids: [
            store.models["product.combo.item"].create({
                id: 9531,
                combo_id: false,
                product_id: variantSmall,
                extra_price: 0,
            }),
            store.models["product.combo.item"].create({
                id: 9532,
                combo_id: false,
                product_id: variantLarge,
                extra_price: 0,
            }),
        ],
    });
    combo.combo_item_ids.forEach((item) => {
        item.combo_id = combo;
    });

    const comboProductTemplate = store.models["product.template"].create({
        id: 9540,
        name: "Test Product Combo",
        display_name: "Test Product Combo",
        available_in_pos: true,
        active: true,
        type: "combo",
        uom_id: store.models["uom.uom"].get(1),
        tracking: "none",
        taxes_id: [],
        product_variant_ids: [store.models["product.product"].get(7)],
        combo_ids: [combo],
        pos_categ_ids: [store.models["pos.category"].get(1)],
        attribute_line_ids: [],
    });

    await store.addLineToOrder(
        {
            product_tmpl_id: comboProductTemplate,
            qty: 1,
            payload: [
                [
                    {
                        combo_item_id: combo.combo_item_ids[1],
                        qty: 1,
                        configuration: {
                            attribute_value_ids: [blue.id, large.id],
                            attribute_custom_values: {},
                        },
                    },
                ],
            ],
        },
        order
    );

    const comboLine = order.lines.find((l) => l.combo_parent_id);
    expect(Boolean(comboLine)).toBe(true);
    expect(comboLine.product_id.id).toBe(variantLarge.id);
    expect(comboLine.attribute_value_ids.map((v) => v.name).sort()).toEqual(["Blue", "Large"]);
});

test("test_line_configurators_product: line configurators product", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const configurableProduct = createConfigurableChair(store);

    const line = await store.addLineToOrder(
        {
            product_tmpl_id: configurableProduct.template,
            payload: configurableProduct.payload,
            qty: 1,
        },
        order
    );

    expectConfiguredChairLine(line);

    const popup = await mountWithCleanup(ProductConfiguratorPopup, {
        props: {
            productTemplate: configurableProduct.template,
            line,
            getPayload: () => {},
            close: () => {},
        },
    });
    const selectedAttributes = popup.state.attributes;
    expect(selectedAttributes[configurableProduct.values.blue.attribute_id.id].selected.name).toBe(
        "Blue"
    );
    expect(selectedAttributes[configurableProduct.values.wood.attribute_id.id].selected.name).toBe(
        "Wood"
    );
    expect(selectedAttributes[configurableProduct.values.other.attribute_id.id].selected.name).toBe(
        "Other"
    );
    expect(selectedAttributes[configurableProduct.values.other.attribute_id.id].custom_value).toBe(
        "Azerty"
    );
    expect(
        selectedAttributes[configurableProduct.values.cushion.attribute_id.id].selected.map(
            (value) => value.name
        )
    ).toEqual(["Cushion", "Headrest"]);
});

test("test_line_configurators_combo: line configurators combo", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const configurableProduct = createConfigurableChair(store);
    const comboProduct = createComboProduct(store, configurableProduct);

    const parentLine = await store.addLineToOrder(
        {
            product_tmpl_id: comboProduct.template,
            qty: 1,
            payload: [
                [
                    { combo_item_id: comboProduct.items.product2, qty: 1 },
                    {
                        combo_item_id: comboProduct.items.configurableChair,
                        qty: 1,
                        configuration: {
                            attribute_value_ids: configurableProduct.payload.attribute_value_ids,
                            attribute_custom_values:
                                configurableProduct.payload.attribute_custom_values,
                        },
                    },
                    { combo_item_id: comboProduct.items.product6, qty: 1 },
                ],
            ],
        },
        order
    );

    const childLines = parentLine.getAllLinesInCombo().filter((line) => line.combo_item_id);
    expect(childLines.map((line) => line.product_id.name)).toEqual([
        "Combo Product 6",
        "Configurable Chair",
        "Combo Product 2",
    ]);
    const configuredComboLine = childLines.find(
        (line) => line.product_id.name === "Configurable Chair"
    );
    expectConfiguredChairLine(configuredComboLine);

    const popup = await mountWithCleanup(ComboConfiguratorPopup, {
        props: {
            productTemplate: comboProduct.template,
            line: parentLine,
            getPayload: () => {},
            close: () => {},
        },
    });
    expect(
        popup.state.qty[comboProduct.items.product2.combo_id.id][comboProduct.items.product2.id]
    ).toBe(1);
    expect(
        popup.state.qty[comboProduct.items.configurableChair.combo_id.id][
            comboProduct.items.configurableChair.id
        ]
    ).toBe(1);
    expect(
        popup.state.qty[comboProduct.items.product6.combo_id.id][comboProduct.items.product6.id]
    ).toBe(1);
    expect(
        popup.state.configuration[comboProduct.items.configurableChair.id].attribute_value_ids
    ).toEqual(configurableProduct.payload.attribute_value_ids);
    expect(
        popup.state.configuration[comboProduct.items.configurableChair.id].attribute_custom_values
    ).toEqual(configurableProduct.payload.attribute_custom_values);
});

test("configurator auto payload computes no variant extra", async () => {
    const store = await setupPosEnv();
    const alwaysAttr = createAttribute(store, "Size", "radio", "always");
    const noVariantAttr = createAttribute(store, "Flavor", "radio", "no_variant");

    const sizeSmall = createAttributeValue(store, alwaysAttr, "Small", { id: 9701, priceExtra: 5 });
    const flavorSugar = createAttributeValue(store, noVariantAttr, "Sugar", {
        id: 9702,
        priceExtra: 2,
    });

    const product = store.models["product.template"].get(5);
    product.update({
        attribute_line_ids: [
            createAttributeLine(store, alwaysAttr, [sizeSmall]),
            createAttributeLine(store, noVariantAttr, [flavorSugar]),
        ],
    });

    const payload = await store.openConfigurator(product);
    expect(payload.attribute_value_ids.sort((a, b) => a - b)).toEqual([9701, 9702]);
    expect(payload.price_extra).toBe(2);
    expect(payload.quantity).toBe(1);
});

test("configurator preset variant keeps matching always values", async () => {
    const store = await setupPosEnv();
    const alwaysAttr = createAttribute(store, "Size", "radio", "always");
    const noVariantAttr = createAttribute(store, "Flavor", "radio", "no_variant");
    const sizeSmall = createAttributeValue(store, alwaysAttr, "Small", { id: 9710 });
    const sizeLarge = createAttributeValue(store, alwaysAttr, "Large", { id: 9711 });
    const colorBlue = createAttributeValue(store, noVariantAttr, "Blue", {
        id: 9712,
        priceExtra: 1,
    });

    const variantLarge = store.models["product.product"].create({
        id: 9713,
        product_tmpl_id: store.models["product.template"].get(5),
        display_name: "Tee (Large)",
        lst_price: 10,
        standard_price: 0,
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [sizeLarge],
        product_template_variant_value_ids: [sizeLarge],
        product_tag_ids: [],
        pos_categ_ids: [1],
    });

    const product = store.models["product.template"].create({
        id: 9714,
        name: "Tee",
        display_name: "Tee",
        available_in_pos: true,
        active: true,
        type: "consu",
        uom_id: store.models["uom.uom"].get(1),
        tracking: "none",
        taxes_id: [],
        product_variant_ids: [variantLarge],
        attribute_line_ids: [
            createAttributeLine(store, alwaysAttr, [sizeSmall, sizeLarge]),
            createAttributeLine(store, noVariantAttr, [colorBlue]),
        ],
        combo_ids: [],
        pos_categ_ids: [store.models["pos.category"].get(1)],
    });

    const payload = await store.openConfigurator(product, { presetVariant: variantLarge });
    expect(payload.attribute_value_ids.sort((a, b) => a - b)).toEqual([9711, 9712]);
    expect(payload.price_extra).toBe(1);
});

test("handle configurable product builds custom attribute commands", async () => {
    const store = await setupPosEnv();
    const alwaysAttr = createAttribute(store, "Size", "radio", "always");
    const customAttr = createAttribute(store, "Custom", "radio");
    const sizeLarge = createAttributeValue(store, alwaysAttr, "Large", { id: 9720 });
    const customValue = createAttributeValue(store, customAttr, "Custom", {
        id: 9721,
        isCustom: true,
    });

    const variantLarge = store.models["product.product"].create({
        id: 9722,
        product_tmpl_id: store.models["product.template"].get(5),
        display_name: "Cup (Large)",
        lst_price: 10,
        standard_price: 0,
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [sizeLarge],
        product_template_variant_value_ids: [sizeLarge],
        product_tag_ids: [],
        pos_categ_ids: [1],
    });

    const product = store.models["product.template"].create({
        id: 9723,
        name: "Cup",
        display_name: "Cup",
        available_in_pos: true,
        active: true,
        type: "consu",
        uom_id: store.models["uom.uom"].get(1),
        tracking: "none",
        taxes_id: [],
        product_variant_ids: [variantLarge],
        attribute_line_ids: [
            createAttributeLine(store, alwaysAttr, [sizeLarge]),
            createAttributeLine(store, customAttr, [customValue]),
        ],
        combo_ids: [],
        pos_categ_ids: [store.models["pos.category"].get(1)],
    });

    const values = {
        product_tmpl_id: product,
        product_id: product.product_variant_ids[0],
        qty: 1,
        price_extra: 0,
        payload: {
            attribute_value_ids: [9720, 9721],
            attribute_custom_values: { 9721: "Happy Birthday" },
            price_extra: 3,
            qty: 2,
        },
    };

    const result = await store.handleConfigurableProduct(values, product, {}, true);
    expect(result).toBe(undefined);
    expect(values.product_id.id).toBe(variantLarge.id);
    expect(values.qty).toBe(2);
    expect(values.price_extra).toBe(3);
    expect(values.attribute_value_ids).toHaveLength(2);
    expect(values.custom_attribute_value_ids).toHaveLength(1);
    expect(values.custom_attribute_value_ids[0][1].custom_value).toBe("Happy Birthday");
});

test("single non-custom choice is not configurable", async () => {
    const store = await setupPosEnv();
    const attr = createAttribute(store, "Single", "radio");
    const onlyValue = createAttributeValue(store, attr, "Default", { id: 9730 });
    const product = store.models["product.template"].get(5);
    product.update({
        attribute_line_ids: [createAttributeLine(store, attr, [onlyValue])],
    });

    expect(product.isConfigurable()).toBe(undefined);
    expect(product.needToConfigure()).toBe(undefined);
});

test("test_attribute_order: attributes keep the configured display order", async () => {
    const store = await setupPosEnv();
    store.session.state = "opened";
    const order = store.addNewOrder();
    const category = store.models["pos.category"].get(1);
    const attribute1 = createAttribute(store, "Attribute 1", "radio");
    const attribute2 = createAttribute(store, "Attribute 2", "radio");
    const attribute3 = createAttribute(store, "Attribute 3", "radio");
    const value1 = createAttributeValue(store, attribute1, "Value 1");
    const value2 = createAttributeValue(store, attribute2, "Value 2");
    const value3 = createAttributeValue(store, attribute3, "Value 3");
    const value4 = createAttributeValue(store, attribute3, "Value 4");
    const product = store.models["product.template"].create({
        id: 9900,
        name: "Product Test",
        display_name: "Product Test",
        available_in_pos: true,
        active: true,
        type: "consu",
        uom_id: store.models["uom.uom"].get(1),
        tracking: "none",
        taxes_id: [],
        product_variant_ids: [],
        attribute_line_ids: [
            createAttributeLine(store, attribute1, [value1]),
            createAttributeLine(store, attribute2, [value2]),
            createAttributeLine(store, attribute3, [value3, value4]),
        ],
        combo_ids: [],
        pos_categ_ids: [category],
    });
    const variant = store.models["product.product"].create({
        id: 9901,
        name: "Product Test",
        display_name: "Product Test",
        product_tmpl_id: product,
        lst_price: 10,
        standard_price: 0,
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [],
        product_template_variant_value_ids: [],
        product_tag_ids: [],
        pos_categ_ids: [category.id],
    });
    product.product_variant_ids = [variant];

    await mountWithCleanup(ProductScreen, {
        props: { orderUuid: order.uuid },
    });

    await contains('.product-sortable[data-product-id="9900"]').click();
    await waitFor(".modal");
    await click(".modal label", { text: "Value 1" });
    await click(".modal label", { text: "Value 2" });
    await click(".modal label", { text: "Value 3" });
    await click(".modal .btn-primary", { text: "Add" });
    await tick();

    expect(order.lines).toHaveLength(1);
    expect(order.lines[0].getFullProductName()).toBe("Product Test (Value 1, Value 2, Value 3)");
});

test("test_product_configurator_price: popup price reacts to selected attributes", async () => {
    const store = await setupPosEnv();
    store.session.state = "opened";
    const order = store.addNewOrder();
    order.setPricelist(false);
    const tax10 = createTax(store, "Tax 10%", 10, false);
    const category = store.models["pos.category"].get(1);
    const product = store.models["product.template"].create({
        id: 9910,
        name: "Configurable Product",
        display_name: "Configurable Product",
        available_in_pos: true,
        active: true,
        type: "consu",
        uom_id: store.models["uom.uom"].get(1),
        tracking: "none",
        taxes_id: [tax10],
        product_variant_ids: [],
        attribute_line_ids: [],
        combo_ids: [],
        pos_categ_ids: [category],
    });
    const sizeAttribute = createAttribute(store, "Size", "radio", "always");
    const colorAttribute = createAttribute(store, "Color", "radio");
    const small = createAttributeValue(store, sizeAttribute, "Small", { id: 9911 });
    const large = createAttributeValue(store, sizeAttribute, "Large", { id: 9912 });
    const red = createAttributeValue(store, colorAttribute, "Red", {
        id: 9913,
        priceExtra: 2,
    });
    const blue = createAttributeValue(store, colorAttribute, "Blue", {
        id: 9914,
        priceExtra: 3,
    });
    const smallVariant = store.models["product.product"].create({
        id: 9915,
        name: "Configurable Product",
        display_name: "Configurable Product",
        product_tmpl_id: product,
        lst_price: 10,
        standard_price: 0,
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [small],
        product_template_variant_value_ids: [small],
        product_tag_ids: [],
        pos_categ_ids: [category.id],
    });
    const largeVariant = store.models["product.product"].create({
        id: 9916,
        name: "Configurable Product",
        display_name: "Configurable Product",
        product_tmpl_id: product,
        lst_price: 11,
        standard_price: 0,
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [large],
        product_template_variant_value_ids: [large],
        product_tag_ids: [],
        pos_categ_ids: [category.id],
    });
    product.update({
        product_variant_ids: [smallVariant, largeVariant],
        attribute_line_ids: [
            createAttributeLine(store, sizeAttribute, [small, large]),
            createAttributeLine(store, colorAttribute, [red, blue]),
        ],
    });

    await mountWithCleanup(ProductScreen, {
        props: { orderUuid: order.uuid },
    });

    await contains('.product-sortable[data-product-id="9910"]').click();
    await waitFor(".modal");
    await animationFrame();
    expect(document.querySelector(".modal-title").textContent.includes("13.20")).toBe(true);
    await click(".modal label", { text: "Large" });
    await animationFrame();
    expect(document.querySelector(".modal-title").textContent.includes("14.30")).toBe(true);
    await click(".modal label", { text: "Blue" });
    await animationFrame();
    expect(document.querySelector(".modal-title").textContent.includes("15.40")).toBe(true);
    await click(".modal .btn-primary", { text: "Add" });
    await animationFrame();

    expect(order.priceIncl).toBe(15.4);
});
