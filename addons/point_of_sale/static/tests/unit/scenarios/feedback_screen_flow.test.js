import { expect, test } from "@odoo/hoot";
import { animationFrame, waitFor, advanceTime } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { setupAndMountPosApp, createTestProduct } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as Utils from "@point_of_sale/../tests/unit/ui_utils";

definePosModels();

test("test_automatic_receipt_printing: auto print and auto-skip feedback screen", async () => {
    const store = await setupAndMountPosApp({
        use_pricelist: false,
        iface_print_auto: true,
        other_devices: true,
        preparation_printer_ids: false,
        receipt_printer_ids: [3, 4],
    });
    store.feedbackScreenAutoSkipDelay = 500;

    const productTmpl = store.models["product.template"].get(5);
    productTmpl.taxes_id = [];

    await animationFrame();
    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickPayButton();
    await Utils.clickPaymentMethod("Card");
    await Utils.clickValidatePayment();

    await waitFor(".feedback-screen");
    await animationFrame();
    await contains('.modal span:contains("Test Printer")').click();
    await animationFrame();
    await Utils.confirmDialog();
    await animationFrame();
    await Utils.closePrintingError();
    await advanceTime(600);
    await waitFor(".product-screen");

    await Utils.clickDisplayedProduct("TEST");
    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Card");
    await Utils.clickValidatePayment();

    await waitFor(".feedback-screen");
    await animationFrame();
    await Utils.closePrintingError();
    await advanceTime(600);
    await waitFor(".product-screen");
});

test("FeedbackScreenDiscountWithPricelistTour: discount display with multiple pricelists", async () => {
    const store = await setupAndMountPosApp();

    const { template: testProduct } = createTestProduct(store, {
        id: 9980,
        name: "Test Product Priceclist",
        price: 10,
    });
    testProduct.taxes_id = [];

    const basePricelist = store.models["product.pricelist"].create({
        id: 10,
        name: "base_pricelist",
        display_name: "base_pricelist (USD)",
        item_ids: [],
    });
    store.models["product.pricelist.item"].create({
        id: 10,
        pricelist_id: basePricelist.id,
        product_tmpl_id: testProduct,
        compute_price: "discount",
        price_discount: 30,
        base: "list_price",
        min_quantity: 0,
    });
    basePricelist.item_ids = [store.models["product.pricelist.item"].get(10)];

    const specialPricelist = store.models["product.pricelist"].create({
        id: 11,
        name: "special_pricelist",
        display_name: "special_pricelist (USD)",
        item_ids: [],
    });
    store.models["product.pricelist.item"].create({
        id: 11,
        pricelist_id: specialPricelist.id,
        base: "pricelist",
        base_pricelist_id: basePricelist,
        compute_price: "discount",
        price_discount: 10,
        min_quantity: 0,
    });
    specialPricelist.item_ids = [store.models["product.pricelist.item"].get(11)];

    store.config.pricelist_id = basePricelist;
    store.config.available_pricelist_ids = [basePricelist, specialPricelist];
    store.config.use_pricelist = true;
    await animationFrame();

    const order = store.getOrder();
    order.setPricelist(basePricelist);

    await Utils.clickDisplayedProduct("Test Product Priceclist");
    expect(order.lines).toHaveLength(1);

    await Utils.clickControlButton("base_pricelist");
    await waitFor(".selection-item");
    await contains('.selection-item:contains("special_pricelist")').click();
    await animationFrame();

    expect(Utils.hasOrderline({ productName: "Test Product Priceclist", price: "6.30" })).toBe(
        true
    );
    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Cash");
    await Utils.clickValidatePayment();

    await Utils.clickNextOrder();
    await waitFor(".product-screen");

    await Utils.clickDisplayedProduct("Test Product Priceclist");
    store.numpadMode = "price";
    await Utils.sendBufferKeys("9");
    expect(
        Utils.hasOrderline({ productName: "Test Product Priceclist", price: "9", quantity: "1" })
    ).toBe(true);
    await Utils.clickPayButton();
    await waitFor(".payment-screen");
    await Utils.clickPaymentMethod("Cash");
    await Utils.clickValidatePayment();
});
