import { expect, test } from "@odoo/hoot";
import { animationFrame, waitFor, advanceTime, press } from "@odoo/hoot-dom";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { localization } from "@web/core/l10n/localization";
import { session } from "@web/session";
import {
    setupAndMountPosApp,
    createTestProduct,
    createConfigurableChair,
    createPosTestTax,
} from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as Utils from "@point_of_sale/../tests/unit/ui_utils";

definePosModels();

test("pos_basic_order_02_decimal_order_quantity: decimal order quantity", async () => {
    const store = await setupAndMountPosApp();

    const order = store.getOrder();
    await Utils.clickDisplayedProduct("TEST");
    expect(order.lines).toHaveLength(1);
    expect(order.lines[0].qty).toBe(1);
    await Utils.sendBufferKeys(".");
    expect(order.lines[0].qty).toBe(0);
    await Utils.sendBufferKeys("9");
    expect(order.lines[0].qty).toBe(0.9);
    await Utils.sendBufferKeys("9");
    expect(order.lines[0].qty).toBe(0.99);
    expect(Utils.getOrderTotal().includes("3.42")).toBe(true);
    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Cash");
    await Utils.clickValidatePayment();
});

test("DecimalCommaOrderlinePrice: decimal comma orderline price format", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });
    patchWithCleanup(localization, { decimalPoint: ",", thousandsSep: "." });

    const productTmpl = store.models["product.template"].get(5);
    productTmpl.list_price = 1453.53;
    productTmpl.taxes_id = [];
    store.models["product.product"].get(5).lst_price = 1453.53;

    await animationFrame();

    await Utils.clickDisplayedProduct("TEST");
    await Utils.sendBufferKeys("5");

    expect(Utils.hasOrderline({ productName: "TEST", quantity: "5", price: "7.267,65" })).toBe(
        true
    );
});

test("ProductCardUoMPrecision: product card shows correct quantity precision", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    createConfigurableChair(store);
    await animationFrame();

    await Utils.clickDisplayedProduct("Configurable Chair");
    await waitFor(".modal");
    await Utils.pickRadio("Leather");
    await Utils.confirmConfigurator();

    const order = store.getOrder();
    expect(order.lines).toHaveLength(1);

    await Utils.sendBufferKeys(".", "1");
    expect(order.lines[0].qty).toBe(0.1);

    await Utils.clickDisplayedProduct("Configurable Chair");
    await waitFor(".modal");
    await Utils.pickRadio("wool");
    await Utils.confirmConfigurator();

    expect(order.lines).toHaveLength(2);

    await Utils.sendBufferKeys(".", "7");
    expect(order.lines[1].qty).toBe(0.7);

    const totalQty = order.lines
        .filter((l) => l.product_id.name === "Configurable Chair")
        .reduce((sum, l) => sum + l.qty, 0);
    expect(Math.round(totalQty * 10) / 10).toBe(0.8);
});

test("test_ctrl_number_ignored: ctrl+number does not change the order line", async () => {
    const store = await setupAndMountPosApp();

    await Utils.clickDisplayedProduct("TEST");
    const order = store.getOrder();
    expect(order.lines).toHaveLength(1);
    expect(order.lines[0].qty).toBe(1);

    window.dispatchEvent(new KeyboardEvent("keyup", { key: "5", ctrlKey: true }));
    await animationFrame();
    await advanceTime(350);

    expect(order.lines[0].qty).toBe(1);
});

test("test_orderline_merge_with_higher_price_precision: merging with high precision price", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    store.models["decimal.precision"].get(3).digits = 3;

    createTestProduct(store, { id: 9700, name: "High Precision Product", price: 8.245 });

    await animationFrame();
    await Utils.clickDisplayedProduct("High Precision Product");
    expect(
        Utils.hasOrderline({ productName: "High Precision Product", quantity: "1", price: "8.25" })
    ).toBe(true);

    await Utils.clickDisplayedProduct("High Precision Product");
    expect(
        Utils.hasOrderline({ productName: "High Precision Product", quantity: "2", price: "16.49" })
    ).toBe(true);
});

test("SearchProducts: product search is case-insensitive and accent-aware", async () => {
    const store = await setupAndMountPosApp();

    createTestProduct(store, { id: 300, name: "Test chair 1" });
    createTestProduct(store, { id: 301, name: "Test CHAIR 2" });
    createTestProduct(store, { id: 302, name: "Test sofa", default_code: "CHAIR_01" });
    createTestProduct(store, { id: 303, name: "clémentine" });
    createTestProduct(store, { id: 304, name: "Wall Shelf Unit", barcode: "2100005000000" });
    await animationFrame();

    const searchInput = ".pos-rightheader .form-control > input";

    if (Utils.isMobile()) {
        await contains(".oi.undefined").click();
        await animationFrame();
    }
    await contains(searchInput).edit("chair");
    await animationFrame();

    await waitFor('article.product .product-name:contains("Test chair 1")');
    await waitFor('article.product .product-name:contains("Test CHAIR 2")');
    await waitFor('article.product .product-name:contains("Test sofa")');

    await contains(searchInput).edit("clémentine");
    await animationFrame();

    await waitFor('article.product .product-name:contains("clémentine")');

    await contains(searchInput).edit("2100005000000");
    await animationFrame();

    await waitFor('article.product .product-name:contains("Wall Shelf Unit")');
});

test("ShowTaxExcludedTour: tax-excluded price display", async () => {
    const store = await setupAndMountPosApp({
        use_pricelist: false,
        iface_tax_included: "subtotal",
    });

    const taxIncl10 = createPosTestTax(store, {
        id: 300,
        name: "Tax 10% Included",
        amount: 10,
        priceInclude: true,
    });

    createTestProduct(store, {
        id: 9970,
        name: "Test Product Incl",
        price: 110,
        taxes_id: [taxIncl10],
    });

    const order = store.getOrder();

    await animationFrame();

    await Utils.clickDisplayedProduct("Test Product Incl");
    expect(order.lines).toHaveLength(1);

    const total = Utils.getOrderTotal();
    expect(total).toInclude("110");

    const subtotal = document.querySelector(".order-summary .subtotal");
    expect(subtotal.textContent).toInclude("100");
});

test("test_pos_snooze: snooze and unsnooze products", async () => {
    patchWithCleanup(session, { nomenclature_id: 1 });
    const store = await setupAndMountPosApp();

    await Utils.longPress('[data-product-id="5"]');
    await animationFrame();
    await waitFor(".modal");

    const snoozeBtn = document.querySelector(".modal .section-inventory .btn");
    expect(snoozeBtn.classList.contains("btn-secondary")).toBe(true);

    await contains(".modal .section-inventory .btn").click();
    await animationFrame();

    await contains('.modal label:contains("1 Hour")').click();
    await animationFrame();

    await contains('.modal .btn-primary:contains("Apply")').click();
    await animationFrame();

    await waitFor(".modal .section-inventory .btn-warning");

    await contains('.modal .btn-primary:contains("Close")').click();
    await animationFrame();

    await Utils.clickDisplayedProduct("TEST");
    await animationFrame();
    expect(document.querySelector(".modal-body").textContent).toInclude("snoozed");

    await contains('.modal .btn-primary:contains("Continue")').click();
    await animationFrame();

    const order = store.getOrder();
    expect(order.lines).toHaveLength(1);

    await Utils.clickDisplayedProduct("TEST");
    expect(order.lines[0].qty).toBe(2);

    await Utils.longPress('[data-product-id="5"]');
    await animationFrame();
    await waitFor(".modal");

    await contains(".modal .section-inventory .btn-warning").click();
    await animationFrame();

    await contains('.modal .btn-primary:contains("Yes")').click();
    await animationFrame();

    await waitFor(".modal .section-inventory .btn-secondary");
    await contains('.modal .btn-primary:contains("Close")').click();
    await animationFrame();
    await Utils.clickDisplayedProduct("TEST");
    expect(order.lines[0].qty).toBe(3);
});

test("test_pricelist_multi_items_different_qty_thresholds: prefer highest matching min_quantity", async () => {
    const store = await setupAndMountPosApp();

    const { template: productTmpl } = createTestProduct(store, {
        id: 9550,
        name: "tpmcapi product",
        price: 1,
    });

    const pricelist = store.models["product.pricelist"].create({
        id: 30,
        name: "Multi Qty Pricelist",
        display_name: "Multi Qty Pricelist (USD)",
        item_ids: [],
    });
    const item1 = store.models["product.pricelist.item"].create({
        id: 30,
        pricelist_id: pricelist.id,
        product_tmpl_id: productTmpl,
        compute_price: "fixed",
        fixed_price: 10,
        base: "list_price",
        min_quantity: 3,
    });
    const item2 = store.models["product.pricelist.item"].create({
        id: 31,
        pricelist_id: pricelist.id,
        product_tmpl_id: productTmpl,
        compute_price: "fixed",
        fixed_price: 20,
        base: "list_price",
        min_quantity: 2,
    });
    pricelist.item_ids = [item1, item2];
    pricelist.computeRuleIndexes();

    store.config.pricelist_id = pricelist;
    store.config.available_pricelist_ids = [pricelist];
    store.config.use_pricelist = true;
    const order = store.getOrder();
    order.setPricelist(pricelist);
    await animationFrame();

    await Utils.clickDisplayedProduct("tpmcapi product");
    expect(
        Utils.hasOrderline({ productName: "tpmcapi product", quantity: "1", price: "1.00" })
    ).toBe(true);
    await Utils.clickDisplayedProduct("tpmcapi product");
    expect(
        Utils.hasOrderline({ productName: "tpmcapi product", quantity: "2", price: "40.00" })
    ).toBe(true);
    await Utils.clickDisplayedProduct("tpmcapi product");
    expect(
        Utils.hasOrderline({ productName: "tpmcapi product", quantity: "3", price: "30.00" })
    ).toBe(true);

    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    const totalEl = document.querySelector(".payment-status-total, .total");
    expect(totalEl.textContent).toInclude("30");
});

test("test_pricelist_parent_category_rule: pricelist applies to child category products", async () => {
    const store = await setupAndMountPosApp();

    const parentCategory = store.models["product.category"].create({
        id: 100,
        name: "Parent Category",
        parent_id: false,
    });
    const childCategory = store.models["product.category"].create({
        id: 101,
        name: "Child Category",
        parent_id: parentCategory.id,
    });

    const { template: productTmpl } = createTestProduct(store, {
        id: 9560,
        name: "Product with child category",
        price: 100,
    });
    productTmpl.categ_id = childCategory;
    const pricelist = store.models["product.pricelist"].create({
        id: 31,
        name: "Category Pricelist",
        display_name: "Category Pricelist (USD)",
        item_ids: [],
    });
    const plItem = store.models["product.pricelist.item"].create({
        id: 32,
        pricelist_id: pricelist.id,
        compute_price: "fixed",
        fixed_price: 50,
        base: "list_price",
        categ_id: parentCategory,
        min_quantity: 0,
    });
    pricelist.item_ids = [plItem];
    pricelist.computeRuleIndexes();

    store.config.pricelist_id = pricelist;
    store.config.available_pricelist_ids = [pricelist];
    store.config.use_pricelist = true;
    const order = store.getOrder();
    order.setPricelist(pricelist);
    await animationFrame();

    await Utils.clickDisplayedProduct("Product with child category");
    expect(
        Utils.hasOrderline({
            productName: "Product with child category",
            quantity: "1",
            price: "50.00",
        })
    ).toBe(true);
});

test("test_delete_line: delete line through popup when disallowLineQuantityChange", async () => {
    const store = await setupAndMountPosApp({ use_pricelist: false });

    await Utils.clickDisplayedProduct("TEST");
    const order = store.getOrder();
    expect(order.lines).toHaveLength(1);
    store.disallowLineQuantityChange = () => true;

    await Utils.ensurePane("left");
    await Utils.sendBufferKeys("Backspace");
    await waitFor(".modal");
    await contains('.modal .numpad button:contains("0")').click();
    await animationFrame();
    await press("Enter");
    await animationFrame();
    expect(order.lines).toHaveLength(0);
});
