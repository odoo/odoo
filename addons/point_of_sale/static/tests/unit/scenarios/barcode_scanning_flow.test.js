import { expect, test } from "@odoo/hoot";
import { animationFrame, waitFor } from "@odoo/hoot-dom";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { session } from "@web/session";
import {
    setupAndMountPosApp,
    createAttribute,
    createAttributeValue,
    createAttributeLine,
    createTestProduct,
} from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as Utils from "@point_of_sale/../tests/unit/ui_utils";

definePosModels();

test("BarcodeScanningTour: scan product and weighted barcodes", async () => {
    patchWithCleanup(session, { nomenclature_id: 1 });
    const store = await setupAndMountPosApp({ use_pricelist: false });

    createTestProduct(store, {
        id: 9450,
        name: "Monitor Stand",
        price: 3.19,
        barcode: "0123456789",
    });
    createTestProduct(store, {
        id: 9451,
        name: "Magnetic Board",
        price: 1.98,
        barcode: "2305000000004",
    });
    await animationFrame();

    await Utils.scanBarcode("0123456789");
    expect(Utils.hasOrderline({ productName: "Monitor Stand", quantity: "1" })).toBe(true);

    await Utils.scanBarcode("0123456789");
    expect(Utils.hasOrderline({ productName: "Monitor Stand", quantity: "2" })).toBe(true);

    await Utils.scanBarcode("2305000000004");
    expect(Utils.hasOrderline({ productName: "Magnetic Board", price: "0.00" })).toBe(true);

    await Utils.scanBarcode("2305000123451");
    expect(Utils.hasOrderline({ productName: "Magnetic Board", price: "123.45" })).toBe(true);
});

test("BarcodeScanningProductPackagingTour: scan product packaging barcodes", async () => {
    patchWithCleanup(session, { nomenclature_id: 1 });
    const store = await setupAndMountPosApp({ use_pricelist: false });

    const packOf10 = store.models["uom.uom"].create({
        id: 9401,
        name: "Pack of 10",
        factor: 10,
        is_pos_groupable: true,
        parent_path: "1/9401/",
    });

    const { variant: prodVariant } = createTestProduct(store, {
        id: 9402,
        name: "Packaging Product",
        price: 10,
        barcode: "12345601",
    });

    store.models["product.uom"].create({
        id: 9403,
        barcode: "12345610",
        product_id: prodVariant,
        uom_id: packOf10,
    });

    const addonsAttr = createAttribute(store, "Add-ons", "multi");
    const cushion = createAttributeValue(store, addonsAttr, "Cushion", { id: 9410 });
    const cupholder = createAttributeValue(store, addonsAttr, "Cup Holder", { id: 9411 });

    const { variant: prod2Variant } = createTestProduct(store, {
        id: 9404,
        name: "Packaging Product2",
        price: 10,
        attributes: [createAttributeLine(store, addonsAttr, [cushion, cupholder])],
    });

    store.models["product.uom"].create({
        id: 9405,
        barcode: "12345618",
        product_id: prod2Variant,
        uom_id: packOf10,
    });

    await animationFrame();

    await Utils.scanBarcode("12345601");
    expect(Utils.hasOrderline({ productName: "Packaging Product", quantity: "1" })).toBe(true);

    await Utils.scanBarcode("12345601");
    expect(Utils.hasOrderline({ productName: "Packaging Product", quantity: "2" })).toBe(true);

    await Utils.scanBarcode("12345610");
    expect(Utils.hasOrderline({ productName: "Packaging Product", quantity: "1" })).toBe(true);

    await Utils.scanBarcode("12345610");
    expect(Utils.hasOrderline({ productName: "Packaging Product", quantity: "2" })).toBe(true);

    await Utils.scanBarcode("12345618");

    await waitFor(".modal");
    await Utils.pickMulti("Cushion");
    await Utils.confirmConfigurator();

    expect(
        Utils.hasOrderline({
            productName: "Packaging Product2",
            quantity: "1",
            attributeLine: "Cushion",
        })
    ).toBe(true);
});

test("BarcodeScanPartnerTour: scan customer barcode sets partner", async () => {
    patchWithCleanup(session, { nomenclature_id: 1 });
    const store = await setupAndMountPosApp();

    store.models["res.partner"].get(3).barcode = "0421234567890";
    store.models["res.partner"].get(3).barcode = "0241234567890";

    await Utils.scanBarcode("0421234567890");
    await Utils.ensurePane("left");
    await Utils.checkSelectedCustomer("Administrator");
    await Utils.scanBarcode("0241234567890");

    await waitFor(
        '.o_notification:contains("Unknown Barcode 0241234567890. The Point of Sale could not find any product, customer, employee or action associated with the scanned barcode.")'
    );
});

test("test_quantity_package_of_non_basic_unit: barcode packaging sets the packaged quantity", async () => {
    patchWithCleanup(session, { nomenclature_id: 1 });
    const store = await setupAndMountPosApp();

    const packOf6 = store.models["uom.uom"].get(2);
    const { variant } = createTestProduct(store, {
        id: 9303,
        name: "Cord",
        price: 10,
    });
    store.models["product.uom"].create({
        id: 9305,
        barcode: "555555",
        product_id: variant,
        uom_id: packOf6,
    });

    await Utils.scanBarcode("555555");
    expect(Utils.hasOrderline({ productName: "Cord", quantity: "1" })).toBe(true);
});

test("test_one_attribute_value_scan_barcode: scan barcode adds variant with attributes", async () => {
    patchWithCleanup(session, { nomenclature_id: 1 });
    const store = await setupAndMountPosApp({ use_pricelist: false });

    const category = store.models["pos.category"].get(1);
    const sizeAttr = createAttribute(store, "Size never", "radio");
    const colorAttr = createAttribute(store, "Color always", "radio", "always");

    const large = createAttributeValue(store, sizeAttr, "Large", { id: 9640 });
    const red = createAttributeValue(store, colorAttr, "Red", { id: 9641 });
    const blue = createAttributeValue(store, colorAttr, "Blue", { id: 9642 });

    const { template: productTmpl } = createTestProduct(store, {
        id: 9650,
        name: "Product Test",
        price: 10,
        attributes: [
            createAttributeLine(store, sizeAttr, [large]),
            createAttributeLine(store, colorAttr, [red, blue]),
        ],
    });
    const variantRed = store.models["product.product"].create({
        id: 9651,
        product_tmpl_id: productTmpl,
        lst_price: 10,
        display_name: "Product Test (Red)",
        barcode: "1234567",
        default_code: false,
        product_template_attribute_value_ids: [red],
        product_template_variant_value_ids: [red],
        product_tag_ids: [],
        pos_categ_ids: [category],
    });
    const variantBlue = store.models["product.product"].create({
        id: 9652,
        product_tmpl_id: productTmpl,
        lst_price: 10,
        display_name: "Product Test (Blue)",
        barcode: "1234568",
        default_code: false,
        product_template_attribute_value_ids: [blue],
        product_template_variant_value_ids: [blue],
        product_tag_ids: [],
        pos_categ_ids: [category],
    });
    productTmpl.product_variant_ids = [variantRed, variantBlue];

    await animationFrame();
    Utils.scanBarcode("1234567");
    await animationFrame();
    expect(
        Utils.hasOrderline({
            productName: "Product Test",
            attributeLine: "Large, Red",
            quantity: "1",
        })
    ).toBe(true);

    Utils.scanBarcode("1234568");
    await animationFrame();
    expect(
        Utils.hasOrderline({
            productName: "Product Test",
            attributeLine: "Large, Blue",
            quantity: "1",
        })
    ).toBe(true);
});
