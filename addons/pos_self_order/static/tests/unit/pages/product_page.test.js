import { describe, test, expect, click } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ProductPage } from "@pos_self_order/app/pages/product_page/product_page";
import { setupSelfPosEnv } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

test("changeQuantity and isProductAvailable", async () => {
    const store = await setupSelfPosEnv();
    const models = store.models;
    const product = models["product.template"].get(5);
    const comp = await mountWithCleanup(ProductPage, { props: { productTemplate: product } });

    expect(comp.state.qty).toBe(1);
    expect(comp.isProductAvailable()).toBe(true);

    comp.changeQuantity(true);
    expect(comp.state.qty).toBe(2);
    comp.changeQuantity(false);
    expect(comp.state.qty).toBe(1);
    // Quantity should not decrease below 1
    comp.changeQuantity(false);
    expect(comp.state.qty).toBe(1);
});

test("getProductPrice", async () => {
    const store = await setupSelfPosEnv();
    const models = store.models;
    const product = models["product.template"].get(5);
    const comp = await mountWithCleanup(ProductPage, { props: { productTemplate: product } });

    expect(comp.getProductPrice()).toBe(115);
    comp.state.qty = 4;
    expect(comp.getProductPrice()).toBe(460);

    store.config.iface_tax_included = "subtotal";
    comp.state.qty = 1;
    expect(comp.getProductPrice()).toBe(100);
    comp.state.qty = 4;
    expect(comp.getProductPrice()).toBe(400);
});

describe("getProductPrice with variants", () => {
    test("With attribute create_variant='always'", async () => {
        const store = await setupSelfPosEnv();
        const models = store.models;

        const productTemplate = models["product.template"].get(19);
        const comp = await mountWithCleanup(ProductPage, { props: { productTemplate } });

        expect(comp.getProductPrice()).toBe(10);

        // select the second variant.
        await click(".self_order_attribute_selection div:nth-child(2) button");
        expect(comp.getProductPrice()).toBe(15);

        // that variant price changes with a different pricelist.
        comp.selfOrder.currentOrder.pricelist_id = models["product.pricelist"].get(4);
        expect(comp.getProductPrice()).toBe(20);
    });

    test("With attribute create_variant='no_variant'", async () => {
        const store = await setupSelfPosEnv();
        const models = store.models;

        const productTemplate = models["product.template"].get(20);
        const comp = await mountWithCleanup(ProductPage, { props: { productTemplate } });

        expect(comp.getProductPrice()).toBe(200);

        // select the normal variant, no extra price
        await click(".self_order_attribute_selection div:nth-child(1) button");
        expect(comp.getProductPrice()).toBe(200);

        // select the second variant, with price extra of 10
        await click(".self_order_attribute_selection div:nth-child(2) button");
        expect(comp.getProductPrice()).toBe(210);
    });

    test("With mixed attribute `create_variant`", async () => {
        const store = await setupSelfPosEnv();
        const models = store.models;

        const productTemplate = models["product.template"].get(21);
        const comp = await mountWithCleanup(ProductPage, { props: { productTemplate } });

        expect(comp.getProductPrice()).toBe(100);

        // select Size S
        await click("h2:contains(Size) + .self_order_attribute_selection div:nth-child(1) button");
        expect(comp.getProductPrice()).toBe(100);
        // select Size M (price_extra 5)
        await click("h2:contains(Size) + .self_order_attribute_selection div:nth-child(2) button");
        expect(comp.getProductPrice()).toBe(105);

        // select Packaging Standard
        await click(
            "h2:contains(Packaging) + .self_order_attribute_selection div:nth-child(1) button"
        );
        expect(comp.getProductPrice()).toBe(105);
        // select Packaging Gift (price_extra 10)
        await click(
            "h2:contains(Packaging) + .self_order_attribute_selection div:nth-child(2) button"
        );
        expect(comp.getProductPrice()).toBe(115);
    });
});

test("isAddToCartEnabled", async () => {
    const store = await setupSelfPosEnv();
    const models = store.models;
    const product = models["product.template"].get(5);
    const comp = await mountWithCleanup(ProductPage, { props: { productTemplate: product } });

    // Product unavailability
    product.self_order_available = false;
    expect(comp.isAddToCartEnabled()).toBe(false);
});
