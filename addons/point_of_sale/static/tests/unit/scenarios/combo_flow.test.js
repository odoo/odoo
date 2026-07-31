import { expect, test } from "@odoo/hoot";
import { animationFrame, waitFor, queryAll } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { contains } from "@web/../tests/web_test_helpers";
import {
    setupAndMountPosApp,
    createAttribute,
    createAttributeValue,
    createAttributeLine,
    createTestProduct,
    createComboSetup,
    createPosTestTax,
    createFiscalPosition,
} from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as Utils from "@point_of_sale/../tests/unit/ui_utils";

definePosModels();

test("test_combo_variant_mix: combo with variant and no_variant attributes", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    const category = store.models["pos.category"].get(1);
    const colorAttribute = createAttribute(store, "Color", "radio");
    const sizeAttribute = createAttribute(store, "Size", "radio", "always");

    const red = createAttributeValue(store, colorAttribute, "Red", { id: 9501 });
    const blue = createAttributeValue(store, colorAttribute, "Blue", { id: 9502 });
    const small = createAttributeValue(store, sizeAttribute, "Small", { id: 9503 });
    const large = createAttributeValue(store, sizeAttribute, "Large", { id: 9504 });

    const { template: productTmpl } = createTestProduct(store, {
        id: 9510,
        name: "Test Product",
        price: 10,
        attributes: [
            createAttributeLine(store, colorAttribute, [red, blue]),
            createAttributeLine(store, sizeAttribute, [small, large]),
        ],
    });
    const variantSmall = store.models["product.product"].create({
        id: 9511,
        name: "Test Product",
        display_name: "Test Product (Small)",
        product_tmpl_id: productTmpl,
        lst_price: 10,
        standard_price: 0,
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [small],
        product_template_variant_value_ids: [small],
        product_tag_ids: [],
        pos_categ_ids: [category],
    });
    const variantLarge = store.models["product.product"].create({
        id: 9512,
        name: "Test Product",
        display_name: "Test Product (Large)",
        product_tmpl_id: productTmpl,
        lst_price: 10,
        standard_price: 0,
        barcode: false,
        default_code: false,
        product_template_attribute_value_ids: [large],
        product_template_variant_value_ids: [large],
        product_tag_ids: [],
        pos_categ_ids: [category],
    });
    productTmpl.product_variant_ids = [variantSmall, variantLarge];

    const comboItemSmall = store.models["product.combo.item"].create({
        id: 9521,
        combo_id: false,
        product_id: variantSmall,
        extra_price: 0,
    });
    const comboItemLarge = store.models["product.combo.item"].create({
        id: 9522,
        combo_id: false,
        product_id: variantLarge,
        extra_price: 0,
    });
    const combo = store.models["product.combo"].create({
        id: 9530,
        name: "Test Combo",
        combo_item_ids: [comboItemSmall, comboItemLarge],
        base_price: 20,
        qty_free: 1,
        qty_max: 1,
        is_upsell: false,
        sequence: 1,
    });
    comboItemSmall.combo_id = combo;
    comboItemLarge.combo_id = combo;

    const { template: comboProductTmpl } = createTestProduct(store, {
        id: 9540,
        name: "Test Product Combo",
        price: 20,
        type: "combo",
    });
    comboProductTmpl.combo_ids = [combo];
    await animationFrame();

    await Utils.clickDisplayedProduct("Test Product Combo");
    await waitFor(".modal");

    await Utils.selectComboItem("Test Product (Large)");
    await waitFor('.modal label:contains("Blue")');
    await contains('.modal label:contains("Blue")').click();
    await animationFrame();
    await contains(".modal .btn-primary:eq(1)").click();
    await animationFrame();

    await Utils.confirmCombo();

    const order = store.getOrder();
    const comboLine = order.lines.find((l) => l.combo_parent_id);
    expect(comboLine).not.toBe(null);
    expect(comboLine.product_id.id).toBe(variantLarge.id);
    expect(comboLine.attribute_value_ids.map((v) => v.name).sort()).toEqual(["Blue", "Large"]);
});

test.timeout(10000);
test("test_convert_orderlines_to_combo: convert orderlines to combo and break", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    createComboSetup(store, {
        id: 8030,
        name: "Office Combo",
        price: 50,
        combos: [
            {
                name: "First Combo",
                items: [
                    { name: "Combo Product 2", price: 11 },
                    { name: "Combo Product 1", price: 30 },
                ],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
            {
                name: "Second Combo",
                items: [{ name: "Combo Product 4", price: 20 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
            {
                name: "Third Combo",
                items: [{ name: "Combo Product 6", price: 30 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
        ],
    });
    store.comboSuggestion.productCombos = store.comboSuggestion._getProductCombos();
    await animationFrame();

    await Utils.clickDisplayedProduct("Combo Product 2");
    await Utils.clickDisplayedProduct("Combo Product 4");
    await Utils.clickDisplayedProduct("Combo Product 6");

    const order = store.getOrder();
    expect(order.lines).toHaveLength(3);

    await Utils.ensurePane("left");
    await waitFor(".combo-proposition");
    await contains(".combo-proposition button.btn").click();
    await animationFrame();

    expect(Utils.hasOrderline({ productName: "Office Combo", quantity: "1" })).toBe(true);
    await Utils.clickControlButton("Break Combo");

    expect(Utils.hasOrderline({ productName: "Combo Product 2", quantity: "1" })).toBe(true);
    expect(Utils.hasOrderline({ productName: "Combo Product 4", quantity: "1" })).toBe(true);
    expect(Utils.hasOrderline({ productName: "Combo Product 6", quantity: "1" })).toBe(true);
    expect(Utils.doesNotHaveOrderline({ productName: "Office Combo" })).toBe(true);

    const colorAttr = createAttribute(store, "Color", "color");
    const blueVal = createAttributeValue(store, colorAttr, "Blue", { id: 8050 });
    const redVal = createAttributeValue(store, colorAttr, "Red", { id: 8051 });
    const { variant: sp9 } = createTestProduct(store, {
        id: 8043,
        name: "Second Product 9",
        price: 50,
        attributes: [createAttributeLine(store, colorAttr, [blueVal, redVal])],
    });

    const secondCombo = createComboSetup(store, {
        id: 8080,
        name: "Second Combo Product",
        price: 50,
        combos: [
            {
                name: "S First",
                items: [{ name: "Second Product 2", price: 11 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
            {
                name: "S Second",
                items: [{ name: "Second Product 4", price: 20 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
        ],
    });
    // Add the configurable product as a combo item in a third combo
    const sci3 = store.models["product.combo.item"].create({
        id: 8063,
        combo_id: false,
        product_id: sp9,
        extra_price: 0,
    });
    const sCombo3 = store.models["product.combo"].create({
        id: 8073,
        name: "S Third",
        combo_item_ids: [sci3],
        base_price: 10,
        qty_free: 1,
        qty_max: 1,
        is_upsell: false,
        sequence: 3,
    });
    sci3.combo_id = sCombo3;
    secondCombo.template.combo_ids = [...secondCombo.combos, sCombo3];
    store.comboSuggestion.productCombos = store.comboSuggestion._getProductCombos();
    await animationFrame();

    await Utils.clickDisplayedProduct("Second Product 2");
    await Utils.clickDisplayedProduct("Second Product 4");
    await Utils.clickDisplayedProduct("Second Product 9");

    await waitFor(".modal");
    await Utils.pickColor("Blue");
    await Utils.confirmConfigurator();

    await Utils.ensurePane("left");
    await waitFor(".combo-proposition");
    await contains(".combo-proposition button.btn").click();
    await animationFrame();

    await contains(".modal .apply-combo-btn").click();
    await animationFrame();
    await contains(".modal .apply-combo-btn").click();
    await animationFrame();

    expect(Utils.hasOrderline({ productName: "Second Combo Product", quantity: "1" })).toBe(true);
    expect(Utils.hasOrderline({ productName: "Second Product 9", attributeLine: "Blue" })).toBe(
        true
    );

    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Card");
    await Utils.clickValidatePayment();
});

test("test_convert_orderlines_to_combo_with_upsell: combo suggestion shows prices", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    let order = store.getOrder();

    createComboSetup(store, {
        id: 8130,
        name: "Office Combo",
        price: 50,
        combos: [
            {
                name: "First Combo",
                items: [
                    { name: "Combo Product 2", price: 15 },
                    { name: "Second Product 2", price: 1 },
                ],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
            {
                name: "Second Combo",
                items: [
                    { name: "Combo Product 4", price: 25 },
                    { name: "Second Product 4", price: 2 },
                ],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
            {
                name: "Third Combo",
                items: [
                    { name: "Combo Product 6", price: 35 },
                    { name: "Second Product 6", price: 3 },
                ],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
        ],
    });
    store.comboSuggestion.productCombos = store.comboSuggestion._getProductCombos();
    await animationFrame();

    await Utils.clickDisplayedProduct("Combo Product 2");
    await Utils.clickDisplayedProduct("Combo Product 4");
    await Utils.clickDisplayedProduct("Combo Product 6");
    await Utils.clickDisplayedProduct("Second Product 2");
    await Utils.clickDisplayedProduct("Second Product 4");
    await Utils.clickDisplayedProduct("Second Product 6");

    order = store.getOrder();
    expect(order.lines).toHaveLength(6);

    await Utils.ensurePane("left");
    await waitFor(".combo-proposition");
    await contains(".combo-proposition button.btn").click();
    await animationFrame();

    await waitFor(".modal");

    const comboItems = queryAll(".modal-body .combo-item");
    expect(comboItems.length).toBe(2);

    expect(comboItems[0].textContent).toInclude("Office Combo");
    expect(comboItems[0].textContent).toInclude("50.00");
    expect(comboItems[0].textContent).toInclude("25.00");
    expect(comboItems[0].textContent).toInclude("Save");

    expect(comboItems[1].textContent).toInclude("Office Combo");
    expect(comboItems[1].textContent).toInclude("50.00");
    expect(comboItems[1].textContent).toInclude("44.00");
    expect(comboItems[1].textContent).toInclude("Add");
});

test("ProductComboMaxFreeQtyTour: combo max free qty and upsell pricing", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    createComboSetup(store, {
        id: 7030,
        name: "Office Combo",
        price: 40,
        combos: [
            {
                name: "Desk Accessories",
                items: [{ name: "Combo Product 3", price: 16, extraPrice: 2 }],
                basePrice: 10,
                qtyFree: 2,
                qtyMax: 2,
                sequence: 1,
            },
            {
                name: "Desks",
                items: [
                    { name: "Combo Product 4", price: 20 },
                    { name: "Combo Product 5", price: 25, extraPrice: 2 },
                ],
                basePrice: 10,
                qtyFree: 2,
                qtyMax: 5,
                sequence: 2,
            },
            {
                name: "Chairs",
                items: [
                    { name: "Combo Product 6", price: 30 },
                    { name: "Combo Product 7", price: 32 },
                ],
                basePrice: 30,
                qtyFree: 2,
                qtyMax: 5,
                sequence: 3,
            },
        ],
    });

    const order = store.getOrder();

    await animationFrame();

    await Utils.clickDisplayedProduct("Office Combo");
    await waitFor(".modal");

    await waitFor('.modal div.h3:contains("42.00")');

    await Utils.selectComboItem("Combo Product 3");
    await waitFor('.modal div.h3:contains("44.00")');

    await Utils.selectComboItem("Combo Product 5");
    await Utils.selectComboItem("Combo Product 4");

    await Utils.selectComboItem("Combo Product 6");
    await waitFor('.modal div.h3:contains("46.00")');

    await contains(
        '.modal article:has(.product-name:contains("Combo Product 6")) button[name="pos_quantity_button_plus"]'
    ).click();
    await animationFrame();

    await contains(".modal footer button.confirm").click();
    await animationFrame();

    expect(order.lines).toHaveLength(6);
    const comboParent = order.lines.find((l) => l.product_id.name === "Office Combo");
    expect(comboParent).not.toBe(null);
});

test("ProductComboChangeFP: changing fiscal position doesn't change combo price", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    const tax10 = createPosTestTax(store, {
        id: 500,
        name: "Tax 10%",
        amount: 10,
        priceInclude: true,
    });
    const fp = createFiscalPosition(store, { id: 500, name: "test fp", taxMap: { 500: [501] } });
    createPosTestTax(store, {
        id: 501,
        name: "Tax 5%",
        amount: 5,
        priceInclude: true,
        fiscalPositionIds: [fp],
        originalTaxIds: [tax10],
    });

    const { template: comboTmpl, products } = createComboSetup(store, {
        id: 7600,
        name: "Office Combo",
        price: 50,
        combos: [
            {
                name: "Combo 1",
                items: [
                    { name: "Combo Product 2", price: 11 },
                    { name: "Combo Product 3", price: 16, extraPrice: 2 },
                ],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
            {
                name: "Combo 2",
                items: [{ name: "Combo Product 4", price: 20 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
            {
                name: "Combo 3",
                items: [{ name: "Combo Product 6", price: 30 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
        ],
    });

    comboTmpl.taxes_id = [tax10];
    products.forEach((p) => {
        p.template.taxes_id = [tax10];
    });

    store.config.tax_regime_selection = true;
    store.config.fiscal_position_ids = [fp];
    await animationFrame();

    await Utils.clickDisplayedProduct("Office Combo");
    await waitFor(".modal");
    await Utils.selectComboItem("Combo Product 2");
    await Utils.selectComboItem("Combo Product 4");
    await Utils.selectComboItem("Combo Product 6");
    await Utils.confirmCombo();

    expect(Utils.getOrderTotal()).toInclude("50.00");
    expect(Utils.getOrderTax()).toInclude("4.55");
    await Utils.selectFiscalPosition("test fp");
    expect(Utils.getOrderTax()).toInclude("2.37");
    expect(Utils.getOrderTotal()).toInclude("50.00");
});

test("ProductComboChangePricelist: changing pricelist updates combo price", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    createComboSetup(store, {
        id: 7700,
        name: "Office Combo",
        price: 50,
        combos: [
            {
                name: "Combo 1",
                items: [{ name: "Combo Product 2", price: 11 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
            {
                name: "Combo 2",
                items: [{ name: "Combo Product 4", price: 20 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
            {
                name: "Combo 3",
                items: [{ name: "Combo Product 6", price: 30 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
        ],
    });

    const salePricelist = store.models["product.pricelist"].create({
        id: 20,
        name: "sale 10%",
        display_name: "sale 10% (USD)",
        item_ids: [],
    });
    const plItem = store.models["product.pricelist.item"].create({
        id: 20,
        pricelist_id: salePricelist.id,
        compute_price: "discount",
        price_discount: 10,
        base: "list_price",
        min_quantity: 0,
    });
    salePricelist.item_ids = [plItem];
    store.config.available_pricelist_ids = [...store.config.available_pricelist_ids, salePricelist];
    store.config.use_pricelist = true;
    await animationFrame();

    await Utils.clickDisplayedProduct("Office Combo");
    expect(Utils.hasOrderline({ productName: "Combo Product 2", quantity: "1" })).toBe(true);
    expect(Utils.hasOrderline({ productName: "Combo Product 4", quantity: "1" })).toBe(true);
    expect(Utils.hasOrderline({ productName: "Combo Product 6", quantity: "1" })).toBe(true);
    expect(Utils.getOrderTotal()).toInclude("50.00");

    await Utils.clickControlButton("Pricelist");
    await waitFor(".selection-item");
    await contains('.selection-item:contains("sale 10%")').click();
    await animationFrame();

    expect(Utils.hasOrderline({ productName: "Combo Product 2", quantity: "1" })).toBe(true);
    expect(Utils.hasOrderline({ productName: "Combo Product 4", quantity: "1" })).toBe(true);
    expect(Utils.hasOrderline({ productName: "Combo Product 6", quantity: "1" })).toBe(true);
    expect(Utils.getOrderTotal()).toInclude("45.00");
});

test("ProductComboDiscountTour: combo with manual discount", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    createComboSetup(store, {
        id: 7800,
        name: "Office Combo",
        price: 128,
        combos: [
            {
                name: "Combo 1",
                items: [
                    { name: "Combo Product 2", price: 11 },
                    { name: "Combo Product 3", price: 16, extraPrice: 2 },
                ],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
            {
                name: "Combo 2",
                items: [{ name: "Combo Product 4", price: 20 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
            {
                name: "Combo 3",
                items: [{ name: "Combo Product 6", price: 30 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
        ],
    });
    await animationFrame();

    await Utils.clickDisplayedProduct("Office Combo");
    await waitFor(".modal");
    await Utils.selectComboItem("Combo Product 2");
    await Utils.selectComboItem("Combo Product 4");
    await Utils.selectComboItem("Combo Product 6");
    await Utils.confirmCombo();

    expect(Utils.getOrderTotal()).toInclude("128.00");
    await Utils.clickNumpadButtons("%", "20");
    await advanceTime(200);
    expect(Utils.getOrderTotal()).toInclude("102.41");
});

test("test_combo_item_image_display: combo items show images when config enabled", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    const fakeImage =
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/x+AAwAB/QHuSElHLgAAAABJRU5ErkJggg==";

    const { products } = createComboSetup(store, {
        id: 7900,
        name: "Office Combo",
        price: 40,
        combos: [
            {
                name: "Combo 1",
                items: [
                    { name: "Combo Product 2", price: 11 },
                    { name: "Combo Product 3", price: 16, extraPrice: 2 },
                ],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
            {
                name: "Combo 2",
                items: [{ name: "Combo Product 4", price: 20 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
            {
                name: "Combo 3",
                items: [{ name: "Combo Product 6", price: 30 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
        ],
    });

    products.forEach((p) => {
        p.variant.image_128 = fakeImage;
        p.template.image_128 = fakeImage;
    });

    store.config.show_product_images = true;
    await animationFrame();

    await Utils.clickDisplayedProduct("Office Combo");
    await waitFor(".modal");
    const comboItems = document.querySelectorAll(".modal article.product");
    for (const item of comboItems) {
        const img = item.querySelector(".product-img, img");
        expect(img).not.toBe(null);
    }

    await Utils.selectComboItem("Combo Product 2");
    await Utils.selectComboItem("Combo Product 4");
    await Utils.selectComboItem("Combo Product 6");
    await Utils.confirmCombo();
});

test("test_combo_item_image_not_display: combo items hide images when config disabled", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false, show_product_images: false });

    createComboSetup(store, {
        id: 7950,
        name: "Office Combo",
        price: 40,
        combos: [
            {
                name: "Combo 1",
                items: [
                    { name: "Combo Product 2", price: 11 },
                    { name: "Combo Product 3", price: 16, extraPrice: 2 },
                ],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
            {
                name: "Combo 2",
                items: [{ name: "Combo Product 4", price: 20 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
            {
                name: "Combo 3",
                items: [{ name: "Combo Product 6", price: 30 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
            },
        ],
    });
    await animationFrame();

    await Utils.clickDisplayedProduct("Office Combo");
    await waitFor(".modal");

    const comboItems = document.querySelectorAll(".modal article.product");
    for (const item of comboItems) {
        const img = item.querySelector(".product-img");
        expect(img).toBe(null);
    }

    await Utils.selectComboItem("Combo Product 2");
    await Utils.selectComboItem("Combo Product 4");
    await Utils.selectComboItem("Combo Product 6");
    await Utils.confirmCombo();
});

test("test_combo_no_free_item: combo with all upsell items (no free qty)", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    createComboSetup(store, {
        id: 7960,
        name: "Office Combo",
        price: 40,
        combos: [
            {
                name: "Desk Accessories",
                items: [
                    { name: "Combo Product 1", price: 10 },
                    { name: "Combo Product 2", price: 11 },
                    { name: "Combo Product 3", price: 16, extraPrice: 2 },
                ],
                basePrice: 10,
                qtyFree: 0,
                qtyMax: 5,
                isUpsell: true,
                sequence: 1,
            },
            {
                name: "Desks",
                items: [
                    { name: "Combo Product 4", price: 20 },
                    { name: "Combo Product 5", price: 25, extraPrice: 2 },
                ],
                basePrice: 20,
                qtyFree: 0,
                qtyMax: 5,
                isUpsell: true,
                sequence: 2,
            },
            {
                name: "Chairs",
                items: [
                    { name: "Combo Product 6", price: 30 },
                    { name: "Combo Product 7", price: 32 },
                    { name: "Combo Product 8", price: 40, extraPrice: 5 },
                ],
                basePrice: 30,
                qtyFree: 0,
                qtyMax: 5,
                isUpsell: true,
                sequence: 3,
            },
        ],
    });
    await animationFrame();

    await Utils.clickDisplayedProduct("Office Combo");
    await waitFor(".modal");
    await Utils.selectComboItem("Combo Product 1");
    await Utils.selectComboItem("Combo Product 2");
    await Utils.selectComboItem("Combo Product 3");
    await waitFor('.modal div.h3:contains("72.00")');
    await Utils.selectComboItem("Combo Product 4");
    await Utils.selectComboItem("Combo Product 5");
    await waitFor('.modal div.h3:contains("114.00")');
    await Utils.selectComboItem("Combo Product 6");
    await Utils.selectComboItem("Combo Product 7");
    await Utils.selectComboItem("Combo Product 8");
    await waitFor('.modal div.h3:contains("209.00")');
    await Utils.confirmCombo();
    expect(Utils.hasOrderline({ productName: "Office Combo" })).toBe(true);
    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Card");
    await Utils.clickValidatePayment();
});

test("test_convert_orderlines_to_combo_with_same_product: same product with different attributes stays split", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    const officeCombo = createComboSetup(store, {
        id: 8300,
        name: "Office Combo",
        price: 40,
        combos: [
            {
                name: "Desks Combo",
                items: [{ name: "Combo Product 4", price: 20 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
                sequence: 1,
            },
            {
                name: "Chairs Combo",
                items: [{ name: "Combo Product 6", price: 30 }],
                basePrice: 10,
                qtyFree: 1,
                qtyMax: 1,
                sequence: 2,
            },
        ],
    });

    const colorAttribute = createAttribute(store, "Color", "color");
    const red = createAttributeValue(store, colorAttribute, "Red", { id: 8350 });
    const blue = createAttributeValue(store, colorAttribute, "Blue", { id: 8351 });
    const { variant: comboProduct1 } = createTestProduct(store, {
        id: 8360,
        name: "Combo Product 1",
        price: 10,
        attributes: [createAttributeLine(store, colorAttribute, [red, blue])],
    });
    const comboItem = store.models["product.combo.item"].create({
        id: 8370,
        combo_id: false,
        product_id: comboProduct1,
        extra_price: 0,
    });
    const deskAccessoriesCombo = store.models["product.combo"].create({
        id: 8380,
        name: "Desk Accessories Combo",
        combo_item_ids: [comboItem],
        base_price: 10,
        qty_free: 1,
        qty_max: 2,
        is_upsell: false,
        sequence: 3,
    });
    comboItem.combo_id = deskAccessoriesCombo;
    officeCombo.template.combo_ids = [...officeCombo.combos, deskAccessoriesCombo];
    store.comboSuggestion.productCombos = store.comboSuggestion._getProductCombos();
    await animationFrame();

    await Utils.clickDisplayedProduct("Combo Product 1");
    await waitFor(".modal");
    await Utils.pickColor("Blue");
    await Utils.confirmConfigurator();

    await Utils.clickDisplayedProduct("Combo Product 1");
    await waitFor(".modal");
    await Utils.pickColor("Red");
    await Utils.confirmConfigurator();

    await Utils.clickDisplayedProduct("Combo Product 4");
    await Utils.clickDisplayedProduct("Combo Product 6");

    await Utils.ensurePane("left");
    await waitFor(".combo-proposition");
    await contains(".combo-proposition button.btn").click();
    await animationFrame();

    expect(Utils.hasOrderline({ productName: "Office Combo", quantity: "1" })).toBe(true);
    expect(
        Utils.hasOrderline({ productName: "Combo Product 1", quantity: "1", attributeLine: "Red" })
    ).toBe(true);
    expect(
        Utils.hasOrderline({ productName: "Combo Product 1", quantity: "1", attributeLine: "Blue" })
    ).toBe(true);
    expect(Utils.hasOrderline({ productName: "Combo Product 4", quantity: "1" })).toBe(true);
    expect(Utils.hasOrderline({ productName: "Combo Product 6", quantity: "1" })).toBe(true);
    expect(queryAll(".orderline")).toHaveLength(5);
});
