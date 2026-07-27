import { expect, test } from "@odoo/hoot";
import { animationFrame, waitFor, press } from "@odoo/hoot-dom";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { session } from "@web/session";
import {
    setupAndMountPosApp,
    createAttribute,
    createAttributeValue,
    createAttributeLine,
    createTestProduct,
    createConfigurableChair,
    createComboProductWithAttribute,
    expectConfiguredChairLine,
} from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as Utils from "@point_of_sale/../tests/unit/ui_utils";

definePosModels();

test("test_line_configurators_product: line configurators product", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    createConfigurableChair(store);
    await animationFrame();

    await Utils.clickDisplayedProduct("Configurable Chair");
    await waitFor(".modal");

    await Utils.pickColor("Blue");
    await Utils.pickSelect("Wood");
    await Utils.pickRadio("Other");
    await Utils.fillCustomAttribute("Azerty");
    await Utils.pickMulti("Cushion");
    await Utils.pickMulti("Headrest");

    await contains(".modal .btn-primary").click();
    await animationFrame();

    const order = store.getOrder();
    expect(order.lines).toHaveLength(1);
    expectConfiguredChairLine(order.lines[0]);

    await Utils.ensurePane("left");
    await Utils.longPressOrderline("Configurable Chair");
    await waitFor(".modal");
    await contains(".modal .btn-secondary").click();
    await animationFrame();

    expectConfiguredChairLine(order.lines[0]);

    await Utils.longPressOrderline("Configurable Chair");
    await waitFor(".modal");

    expect(Utils.isColorSelected("Blue")).toBe(true);
    expect(Utils.getSelectValue()).toBe("Wood");
    expect(Utils.isRadioSelected("Other")).toBe(true);
    expect(Utils.getCustomAttributeValue()).toBe("Azerty");
    expect(Utils.isMultiSelected("Cushion")).toBe(true);
    expect(Utils.isMultiSelected("Headrest")).toBe(true);

    await contains(".modal .btn-primary").click();
    await animationFrame();
});

test("test_line_configurators_combo: line configurators combo", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    createConfigurableChair(store);
    createComboProductWithAttribute(store, {
        template: store.models["product.template"].get(5),
        values: {},
        payload: {
            attribute_value_ids: [9801, 9802, 9803, 9804, 9805],
            attribute_custom_values: { 9803: "Azerty" },
            price_extra: 0,
            qty: 1,
        },
    });
    await animationFrame();

    await Utils.clickDisplayedProduct("Office Combo Test");
    await waitFor(".modal");

    await Utils.selectComboItem("Combo Product 2");

    await Utils.selectComboItem("TEST");
    await waitFor('.modal label[data-color="Blue"], .modal label[title="Blue"]');
    await Utils.pickColor("Blue");
    await Utils.pickSelect("Wood");
    await Utils.pickRadio("Other");
    await Utils.fillCustomAttribute("Azerty");
    await Utils.pickMulti("Cushion");
    await Utils.pickMulti("Headrest");
    await contains(".modal .btn-primary:eq(1)").click();
    await animationFrame();

    await Utils.selectComboItem("TEST");
    await Utils.selectComboItem("Combo Product 6");
    await Utils.confirmCombo();

    const order = store.getOrder();
    const parentLine = order.lines.find((l) => l.combo_line_ids?.length);
    expect(parentLine).not.toBe(null);
    const childLines = parentLine.getAllLinesInCombo().filter((line) => line.combo_item_id);
    const configuredLine = childLines.find((l) => l.product_id.name === "Configurable Chair");
    expectConfiguredChairLine(configuredLine);

    await Utils.ensurePane("left");
    await Utils.longPressOrderline("Office Combo");
    await waitFor(".modal");

    expect(Utils.isComboItemSelected("Combo Product 2")).toBe(true);
    expect(Utils.isComboItemSelected("Configurable Chair")).toBe(true);
    expect(Utils.isComboItemSelected("Combo Product 6")).toBe(true);

    await contains(
        '.modal footer button:contains("Add to Order"), .modal footer button.confirm'
    ).click();
    await animationFrame();

    const parentLine2 = order.lines.find((l) => l.combo_line_ids?.length);
    expect(parentLine2).not.toBe(null);
    const childLines2 = parentLine2.getAllLinesInCombo().filter((line) => line.combo_item_id);
    const configuredLine2 = childLines2.find((l) => l.product_id.name === "Configurable Chair");
    expectConfiguredChairLine(configuredLine2);

    await Utils.longPressOrderline("Office Combo");
    await waitFor(".modal");

    const chairItem = [...document.querySelectorAll(".modal label.combo-item .product-name")].find(
        (el) => el.textContent.includes("TEST")
    );
    await contains(chairItem).click();
    await animationFrame();

    await contains(".modal .btn-primary").click();
    await animationFrame();

    const parentLine3 = order.lines.find((l) => l.combo_line_ids?.length);
    const childLines3 = parentLine3.getAllLinesInCombo().filter((line) => line.combo_item_id);
    const configuredLine3 = childLines3.find((l) => l.product_id.name === "Configurable Chair");
    expectConfiguredChairLine(configuredLine3);

    await Utils.longPressOrderline("Office Combo");
    await waitFor(".modal");
    await Utils.cancelDialog();
    await animationFrame();

    await Utils.longPressOrderline("Office Combo");
    await waitFor(".modal");
    expect(Utils.isComboItemSelected("Configurable Chair")).toBe(true);

    await contains(
        '.modal footer button:contains("Add to Order"), .modal footer button.confirm'
    ).click();
    await animationFrame();
});

test("MultiProductOptionsTour: multi product options shows all values", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    const attribute = createAttribute(store, "Multi", "multi");
    const value1 = createAttributeValue(store, attribute, "Value 1");
    const value2 = createAttributeValue(store, attribute, "Value 2");
    const attrLine = createAttributeLine(store, attribute, [value1, value2]);

    const product = store.models["product.template"].get(5);
    product.update({
        attribute_line_ids: [attrLine],
        name: "Product A",
        display_name: "Product A",
        taxes_id: [],
    });
    await animationFrame();

    await Utils.clickDisplayedProduct("Product A");
    await waitFor(".modal");

    await waitFor('.form-check-label:contains("Value 1")');
    await waitFor('.form-check-label:contains("Value 2")');

    await contains(".modal .btn-primary").click();
    await animationFrame();
});

test("test_attribute_order: attributes keep the configured display order", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    const attribute1 = createAttribute(store, "Attribute 1", "radio");
    const attribute2 = createAttribute(store, "Attribute 2", "radio");
    const attribute3 = createAttribute(store, "Attribute 3", "radio");
    const value1 = createAttributeValue(store, attribute1, "Value 1");
    const value2 = createAttributeValue(store, attribute2, "Value 2");
    const value3 = createAttributeValue(store, attribute3, "Value 3");
    const value4 = createAttributeValue(store, attribute3, "Value 4");

    createTestProduct(store, {
        id: 9900,
        name: "Product Test",
        price: 10,
        attributes: [
            createAttributeLine(store, attribute1, [value1]),
            createAttributeLine(store, attribute2, [value2]),
            createAttributeLine(store, attribute3, [value3, value4]),
        ],
    });
    await animationFrame();

    await Utils.clickDisplayedProduct("Product Test");
    await waitFor(".modal");

    await contains('.modal label:contains("Value 1")').click();
    await animationFrame();
    await contains('.modal label:contains("Value 2")').click();
    await animationFrame();
    await contains('.modal label:contains("Value 3")').click();
    await animationFrame();

    await contains(".modal .btn-primary").click();
    await animationFrame();

    const order = store.getOrder();
    expect(order.lines).toHaveLength(1);
    expect(order.lines[0].getFullProductName()).toBe("Product Test (Value 1, Value 2, Value 3)");
});

test("test_custom_attribute_alone_displayed: custom attribute shows configurator", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    const attribute = createAttribute(store, "Custom", "radio");
    const customValue = createAttributeValue(store, attribute, "Custom", {
        id: 9810,
        isCustom: true,
    });
    const attrLine = createAttributeLine(store, attribute, [customValue]);

    const product = store.models["product.template"].get(5);
    product.update({
        attribute_line_ids: [attrLine],
        name: "Only Custom",
        display_name: "Only Custom",
        taxes_id: [],
    });
    await animationFrame();

    await Utils.clickDisplayedProduct("Only Custom");
    await waitFor(".modal");

    await Utils.fillCustomAttribute("Filling");

    await Utils.confirmConfigurator();
    await animationFrame();

    expect(
        Utils.hasOrderline({ productName: "Only Custom", attributeLine: "Custom: Custom: Filling" })
    ).toBe(true);
});

test("ProductConfiguratorTour: full product configurator flow", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    createConfigurableChair(store);
    await animationFrame();
    await Utils.clickDisplayedProduct("Configurable Chair");
    await waitFor(".modal");

    expect(Utils.getSelectValue()).toBe("Wood");
    expect(Utils.isRadioSelected("Leather")).toBe(true);

    await press("Escape");
    await animationFrame();
    const order = store.getOrder();
    expect(order.lines).toHaveLength(0);

    await Utils.clickDisplayedProduct("Configurable Chair");
    await waitFor(".modal");
    await Utils.pickRadio("Other");
    await Utils.fillCustomAttribute("Custom Fabric");
    await Utils.pickMulti("Cushion");
    await Utils.pickMulti("Headrest");

    expect(Utils.getSelectValue()).toBe("Wood");
    expect(Utils.isRadioSelected("Other")).toBe(true);
    expect(Utils.getCustomAttributeValue()).toBe("Custom Fabric");
    expect(Utils.isMultiSelected("Cushion")).toBe(true);
    expect(Utils.isMultiSelected("Headrest")).toBe(true);

    await Utils.confirmConfigurator();
    expect(order.lines).toHaveLength(1);
    expect(Utils.hasOrderline({ productName: "Configurable Chair", quantity: "1" })).toBe(true);

    await Utils.clickDisplayedProduct("Configurable Chair");
    await waitFor(".modal");
    await Utils.pickRadio("Other");
    await Utils.fillCustomAttribute("Custom Fabric");
    await Utils.pickMulti("Cushion");
    await Utils.pickMulti("Headrest");
    await Utils.confirmConfigurator();
    expect(order.lines).toHaveLength(1);
    expect(Utils.hasOrderline({ productName: "Configurable Chair", quantity: "2" })).toBe(true);

    await Utils.clickDisplayedProduct("Configurable Chair");
    await waitFor(".modal");
    await Utils.pickColor("Blue");
    await Utils.confirmConfigurator();
    expect(order.lines).toHaveLength(2);
    expect(
        Utils.hasOrderline({
            productName: "Configurable Chair",
            quantity: "1",
            attributeLine: "Blue, Wood, Leather",
        })
    ).toBe(true);

    await Utils.ensurePane("left");
    await Utils.longPressOrderline("Configurable Chair");
    await waitFor(".modal");

    expect(Utils.getSelectValue()).toBe("Wood");
    expect(Utils.isRadioSelected("Other")).toBe(true);
    expect(Utils.getCustomAttributeValue()).toBe("Custom Fabric");
    expect(Utils.isMultiSelected("Cushion")).toBe(true);
    expect(Utils.isMultiSelected("Headrest")).toBe(true);

    await Utils.pickColor("Blue");
    await Utils.fillCustomAttribute("Azerty");
    await Utils.cancelDialog();

    expect(Utils.hasOrderline({ productName: "Configurable Chair", quantity: "2" })).toBe(true);
});

test("test_optional_product: optional product popup and add to cart", async () => {
    patchWithCleanup(session, { nomenclature_id: 1 });
    const store = await setupAndMountPosApp({ use_pricelist: false });

    const { template: smallShelfTmpl } = createTestProduct(store, {
        id: 9950,
        name: "Small Shelf",
        price: 5,
        image_128:
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/x+AAwAB/QHuSElHLgAAAABJRU5ErkJggg==",
    });
    createTestProduct(store, {
        id: 9951,
        name: "Desk Pad",
        price: 1.98,
        pos_optional_product_ids: [smallShelfTmpl],
        barcode: "123456789",
    });

    const order = store.getOrder();

    await animationFrame();

    await Utils.clickDisplayedProduct("Desk Pad");
    await waitFor(".modal");

    await Utils.cancelDialog();
    await animationFrame();

    expect(order.lines).toHaveLength(1);
    expect(order.lines[0].product_id.name).toBe("Desk Pad");
    expect(order.lines[0].qty).toBe(1);

    await Utils.clickDisplayedProduct("Desk Pad");
    await waitFor(".modal");

    let optionalLine = document.querySelector(".optional-product-line .product-name");
    expect(optionalLine.textContent).toInclude("Small Shelf");

    const img = document.querySelector(".optional-product-line img.product-img");
    expect(img).not.toBe(null);

    await contains('.optional-product-line .cart-buttons button:contains("+ Add")').click();
    await animationFrame();
    await contains('.modal-footer button:contains("Add")').click();
    await animationFrame();

    expect(order.lines).toHaveLength(2);
    expect(Utils.hasOrderline({ productName: "Desk Pad", quantity: "2" })).toBe(true);

    await Utils.scanBarcode("123456789");
    await waitFor(".modal");
    optionalLine = document.querySelector(".optional-product-line .product-name");
    expect(optionalLine.textContent).toInclude("Small Shelf");

    await contains('.optional-product-line .cart-buttons button:contains("+ Add")').click();
    await animationFrame();
    await contains('.modal-footer button:contains("Add")').click();
    await animationFrame();

    expect(order.lines).toHaveLength(2);
    expect(Utils.hasOrderline({ productName: "Desk Pad", quantity: "3" })).toBe(true);
});

test("test_optional_product_image_not_display: optional product hides image when config off", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false, show_product_images: false });

    const { template: smallShelfTmpl } = createTestProduct(store, {
        id: 9960,
        name: "Small Shelf",
        price: 5,
        image_128:
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/x+AAwAB/QHuSElHLgAAAABJRU5ErkJggg==",
    });

    createTestProduct(store, {
        id: 9961,
        name: "Desk Pad",
        price: 1.98,
        pos_optional_product_ids: [smallShelfTmpl],
    });

    await animationFrame();
    await Utils.clickDisplayedProduct("Desk Pad");
    await waitFor(".modal");

    const img = document.querySelector(".optional-product-line img.product-img");
    expect(img).toBe(null);
});
