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

test("getProductPrice uses getTaxDetails with order fiscal position", async () => {
    const store = await setupSelfPosEnv();
    const models = store.models;
    const order = store.currentOrder;
    const productTemplate = models["product.template"].get(5);
    const comp = await mountWithCleanup(ProductPage, { props: { productTemplate } });
    const outPreset = models["pos.preset"].get(2);
    const fpStrip = models["account.fiscal.position"].get(2);

    store.config.default_fiscal_position_id = false;
    outPreset.fiscal_position_id = fpStrip;
    order.setPreset(outPreset);

    const price = productTemplate.getPrice(
        order.pricelist_id,
        1,
        0,
        false,
        productTemplate.product_variant_ids[0]
    );
    const taxDetails = productTemplate.getTaxDetails({
        overridedValues: {
            price,
            fiscalPosition: order.fiscal_position_id,
            quantity: comp.state.qty,
        },
    });

    expect(comp.getProductPrice()).toBe(taxDetails.total_included);
    expect(comp.getProductPrice()).toBe(100);

    const taxDetailsWithoutFp = productTemplate.getTaxDetails({
        overridedValues: {
            price,
            fiscalPosition: false,
            quantity: comp.state.qty,
        },
    });
    expect(taxDetailsWithoutFp.total_included).toBe(115);
});

test("getProductPrice matches cart line after take-out preset", async () => {
    const store = await setupSelfPosEnv();
    const models = store.models;
    const order = store.currentOrder;
    const productTemplate = models["product.template"].get(5);
    const comp = await mountWithCleanup(ProductPage, { props: { productTemplate } });
    const outPreset = models["pos.preset"].get(2);
    const fpStrip = models["account.fiscal.position"].get(2);

    store.config.default_fiscal_position_id = false;
    outPreset.fiscal_position_id = fpStrip;
    order.setPreset(outPreset);

    expect(comp.getProductPrice()).toBe(100);

    await store.addToCart(productTemplate, 1);
    const line = order.lines.at(-1);
    expect(line.displayPrice).toBe(comp.getProductPrice());
});

describe("getProductPrice with variants", () => {
    test("With attribute create_variant='always'", async () => {
        const store = await setupSelfPosEnv();
        const models = store.models;

        const productTemplate = models["product.template"].get(101);
        const comp = await mountWithCleanup(ProductPage, { props: { productTemplate } });

        expect(comp.getProductPrice()).toBe(10);

        // select the second variant.
        await click(".self_order_attribute_selection div:nth-child(2) button");
        expect(comp.getProductPrice()).toBe(15);

        // that variant price changes with a different pricelist.
        comp.selfOrder.currentOrder.pricelist_id = models["product.pricelist"].get(101);
        expect(comp.getProductPrice()).toBe(20);
    });

    test("With attribute create_variant='no_variant'", async () => {
        const store = await setupSelfPosEnv();
        const models = store.models;

        const productTemplate = models["product.template"].get(102);
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

        const productTemplate = models["product.template"].get(103);
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

test("hide attribute with single 'is_custom' value", async () => {
    const store = await setupSelfPosEnv();
    const product = store.models["product.template"].get(51);
    const attributeLines = product.attribute_line_ids;
    const comp = await mountWithCleanup(ProductPage, {
        props: { productTemplate: product },
    });
    const attributeHelper = comp.state.selectedValues[product.id];
    expect(attributeLines.length).toBeGreaterThan(attributeHelper.availableAttributes.size);
    expect(comp.isAddToCartEnabled()).toBe(false);
    attributeHelper.selectAttribute(
        attributeLines[0],
        attributeLines[0].product_template_value_ids[1]
    );
    expect(comp.isAddToCartEnabled()).toBe(true);
});

test("self_multi_attribute_selector: multi attributes are optional and can be selected together", async () => {
    const store = await setupSelfPosEnv();
    const models = store.models;
    const product = models["product.template"].get(102);
    const attribute = models["product.attribute"].create({
        id: 201,
        name: "Attribute 1",
        display_type: "multi",
        template_value_ids: [],
        attribute_line_ids: [],
        create_variant: "no_variant",
    });
    const attributeValue1 = models["product.template.attribute.value"].create({
        id: 201,
        attribute_id: attribute,
        price_extra: 0,
        name: "Attribute Val 1",
        is_custom: false,
        html_color: false,
        image: false,
        excluded_value_ids: [],
    });
    const attributeValue2 = models["product.template.attribute.value"].create({
        id: 202,
        attribute_id: attribute,
        price_extra: 0,
        name: "Attribute Val 2",
        is_custom: false,
        html_color: false,
        image: false,
        excluded_value_ids: [],
    });
    const attributeLine = models["product.template.attribute.line"].create({
        id: 201,
        attribute_id: attribute,
        product_template_value_ids: [["link", attributeValue1, attributeValue2]],
    });
    product.update({ attribute_line_ids: [["set", attributeLine]] });

    const comp = await mountWithCleanup(ProductPage, { props: { productTemplate: product } });

    expect("h2:contains('Attribute 1') .badge").toHaveCount(0);
    expect(".self_order_attribute_selection button").toHaveCount(2);
    expect(".self_order_attribute_selection button:contains('Attribute Val 1')").toHaveCount(1);
    expect(".self_order_attribute_selection button:contains('Attribute Val 2')").toHaveCount(1);
    expect(comp.isAddToCartEnabled()).toBe(true);

    await click(".self_order_attribute_selection button:contains('Attribute Val 1')");
    await click(".self_order_attribute_selection button:contains('Attribute Val 2')");

    expect(comp.getSelectedAttributesValues()).toEqual([201, 202]);
});
