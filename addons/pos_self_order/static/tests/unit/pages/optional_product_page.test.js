import { test, expect } from "@odoo/hoot";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { OptionalProductPage } from "@pos_self_order/app/pages/optional_product_page/optional_product_page";
import { setupSelfPosEnv } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";
import { animationFrame, click } from "@odoo/hoot-dom";
import * as Utils from "../ui_utils";
import { ConfirmationPage } from "@pos_self_order/app/pages/confirmation_page/confirmation_page";

definePosSelfModels();

test("optionalProducts and isOptionalProductSelected", async () => {
    const store = await setupSelfPosEnv();
    store.computeAvailableCategories();
    const models = store.models;
    const product = models["product.template"].get(5);
    product.update({ pos_optional_product_ids: [8, 10] });

    const comp = await mountWithCleanup(OptionalProductPage, {
        props: { productTemplate: product },
    });
    expect(comp.optionalProducts).toHaveLength(2);
    expect(comp.isOptionalProductSelected).toBe(false);

    await click("span:text('Wood chair')");
    await animationFrame();
    expect(comp.isOptionalProductSelected).toBe(true);
});

test("optionalProducts skips products not available in self order", async () => {
    const store = await setupSelfPosEnv();
    store.computeAvailableCategories();
    const models = store.models;
    const product = models["product.template"].get(5);
    product.update({ pos_optional_product_ids: [8, 10] });

    // A combo choice may be loaded client-side while not being sold on its own.
    models["product.template"].get(8).self_order_available = false;

    const comp = await mountWithCleanup(OptionalProductPage, {
        props: { productTemplate: product },
    });
    expect(comp.optionalProducts).toHaveLength(1);
    expect(comp.optionalProducts[0].id).toBe(10);
    expect(".o_self_product_card").toHaveCount(1);
});

test("optional product UI behavior for self-order", async () => {
    const store = await setupSelfPosEnv("kiosk", "counter", "each", {}, true);
    store.ticketPrinter.printOrderReceipt = () => {};
    store.config.use_presets = false;
    const order = store.currentOrder;
    const product = store.models["product.template"].get(5);
    product.pos_optional_product_ids = [51, 17, 23]; // 'Cake' (Product with Attribute), 'Product combo (no upsell)', 'Fries'

    Utils.clickBtn("Order Now");
    await Utils.page.isProductList();
    await Utils.clickProduct("Test");
    await Utils.page.isOptionalProduct();
    expect(order.lines).toHaveLength(1);
    expect(order.lines[0].product_id.id).toBe(5);
    order.access_token = "TEST_TOKEN";

    await Utils.hasBtn("No Thanks");
    await Utils.clickProduct("Fries");
    Utils.expectProductCardQty("Fries", 1);
    expect(order.lines).toHaveLength(2);
    await Utils.hasBtn("Continue");
    await Utils.clickProduct("Fries");
    Utils.expectProductCardQty("Fries", 2);

    await Utils.clickProduct("Cake");
    await Utils.page.isProduct();
    await Utils.setupAttributeNew([{ name: "Flavor", value: "Vanilla" }]);
    await Utils.page.isOptionalProduct();
    Utils.expectProductCardQty("Cake", 1);

    await Utils.clickProduct("Product combo (no upsell)");
    await Utils.page.isCombo();
    await Utils.setupComboNew([{ product: "Steel Chair" }, { product: "Wood desk", qty: 2 }]);
    await Utils.page.isOptionalProduct();
    Utils.expectProductCardQty("Product combo (no upsell)", 1);

    await Utils.clickBtn("Continue");
    await Utils.page.isProductList();
    await Utils.clickBtn("Checkout");
    await Utils.confirmCart(
        [
            { productName: "Test", qty: 1, price: "115.00" },
            { productName: "Fries", qty: 2, price: "10.00" },
            { productName: "Cake", attributes: ["Flavor: Vanilla"] },
            {
                productName: "Product combo (no upsell)",
                combos: ["Steel chair", "Wood desk", "Wood desk"],
                qty: 1,
                price: "981.25",
            },
        ],
        "1,121.25"
    );
    await Utils.clickBtn("Order");
    patchWithCleanup(ConfirmationPage.prototype, { async printOrderChanges() {} });
    await Utils.page.isConfirmation();
    await Utils.clickBtn("Close");
    await Utils.page.isLanding();
});
