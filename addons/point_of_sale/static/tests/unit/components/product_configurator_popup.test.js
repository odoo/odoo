import { test, expect } from "@odoo/hoot";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "../utils";
import { ProductConfiguratorPopup } from "@point_of_sale/app/components/popups/product_configurator_popup/product_configurator_popup";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

test("Include extra price for dynamic variants in popup", async () => {
    const store = await setupPosEnv();
    const productTemplate = store.models["product.template"].get(60);
    const noVariantLine = store.models["product.template.attribute.line"].get(4);
    productTemplate.update({
        product_variant_ids: [],
        attribute_line_ids: [...productTemplate.attribute_line_ids, noVariantLine],
    });
    store.models["product.template.attribute.value"].get(8).price_extra = 10;
    store.models["product.template.attribute.value"].get(10).price_extra = 20;
    store.models["product.template.attribute.value"].get(7).price_extra = 15;

    const popup = await mountWithCleanup(ProductConfiguratorPopup, {
        props: {
            productTemplate: productTemplate,
            getPayload: () => {},
            close: () => {},
        },
    });
    expect(popup.title.includes("65")).toBe(true);
});

// "Ice Cream", 5.00, untaxed, carrying a single `no_variant` attribute line whose
// only value is "Sprinkles".
const ICE_CREAM_TMPL_ID = 52;
const SPRINKLES_PTAV_ID = 11;

const mountConfigurator = async (rule = false) => {
    const store = await setupPosEnv();
    const productTemplate = store.models["product.template"].get(ICE_CREAM_TMPL_ID);
    store.models["product.template.attribute.value"].get(SPRINKLES_PTAV_ID).price_extra = 1;

    // The default preset already carries a pricelist, so always state the premise.
    let pricelist = false;
    if (rule) {
        pricelist = store.models["product.pricelist"].create({ name: "TAKEAWAY" });
        const item = store.models["product.pricelist.item"].create({
            pricelist_id: pricelist,
            product_tmpl_id: productTemplate,
            base: "list_price",
            ...rule,
        });
        pricelist.update({ item_ids: [item] });
        pricelist.computeRuleIndexes();
    }
    store.addNewOrder().setPricelist(pricelist);

    await mountWithCleanup(ProductConfiguratorPopup, {
        props: {
            productTemplate: productTemplate,
            getPayload: () => {},
            close: () => {},
        },
    });
};

test("Extra price is shown when no pricelist rule applies", async () => {
    await mountConfigurator();
    expect(".price_extra").toHaveCount(1);
});

test("Extra price is hidden when a fixed pricelist rule prices the product", async () => {
    // A fixed rule replaces the whole price of the product, extra prices included,
    // so the 1.00 of "Sprinkles" is never charged and must not be advertised.
    await mountConfigurator({ compute_price: "fixed", fixed_price: 10 });
    expect(".price_extra").toHaveCount(0);
});

test("Extra price is shown when a percentage pricelist rule prices the product", async () => {
    // A percentage rule discounts the price the extra is part of, so it still counts.
    await mountConfigurator({ compute_price: "percentage", percent_price: 50 });
    expect(".price_extra").toHaveCount(1);
});

test("Same attribute on two lines keeps one selection per line", async () => {
    const store = await setupPosEnv();
    const productTemplate = store.models["product.template"].get(ICE_CREAM_TMPL_ID);
    const attribute = store.models["product.attribute"].create({
        name: "Type",
        display_type: "radio",
        create_variant: "no_variant",
    });
    const lines = [1, 2].map((price_extra) => {
        const line = store.models["product.template.attribute.line"].create({
            attribute_id: attribute,
        });
        const value = store.models["product.template.attribute.value"].create({
            name: `Type ${price_extra}`,
            attribute_id: attribute,
            attribute_line_id: line,
            price_extra,
        });
        line.update({ product_template_value_ids: [value] });
        return line;
    });
    productTemplate.update({ attribute_line_ids: lines });
    store.addNewOrder().setPricelist(false);

    let payload;
    const popup = await mountWithCleanup(ProductConfiguratorPopup, {
        props: {
            productTemplate: productTemplate,
            getPayload: (p) => (payload = p),
            close: () => {},
        },
    });
    expect("input[type=radio]:checked").toHaveCount(2);
    expect(popup.title.includes("8")).toBe(true);
    popup.confirm();
    expect(payload.attribute_value_ids.length).toBe(2);
    expect(payload.price_extra).toBe(3);

    // Reopening the configurator from the line restores both selections.
    const line = await store.addLineToCurrentOrder(
        { product_tmpl_id: productTemplate, ...payload },
        {},
        false
    );
    expect(Object.keys(line.selectedAttributes).length).toBe(2);
});

const setupAndAssertExcludedValuesConfigurator = async (displayType, selector) => {
    const store = await setupPosEnv();
    const productTemplate = store.models["product.template"].get(51);
    const ptal = store.models["product.template.attribute.line"].get(5);

    store.models["product.attribute"].get(10).display_type = displayType;
    store.models["product.attribute"].get(7).display_type = displayType;

    productTemplate.update({
        attribute_line_ids: [productTemplate.attribute_line_ids[0], ptal],
    });

    const [choco, vanilla, s, m] = store.models["product.template.attribute.value"]
        .getAll()
        .filter((c) => [5, 6, 8, 9].includes(c.id));

    choco.update({ excluded_value_ids: [m] });
    vanilla.update({ excluded_value_ids: [s] });
    store.processProductAttributes();

    await mountWithCleanup(ProductConfiguratorPopup, {
        props: {
            productTemplate: productTemplate,
            getPayload: () => {},
            close: () => {},
        },
    });

    expect(`label[${selector}='Chocolate']`).toHaveClass("active");
    expect(`label[${selector}='S']`).toHaveClass("active");
    expect(".btn:contains('Add')").not.toHaveClass("disabled");

    await contains(`label[${selector}='Vanilla']`).click();
    expect(`label[${selector}='Vanilla']`).toHaveClass("active");
    expect(".btn:contains('Add')").toHaveClass("disabled");
    await contains(`label[${selector}='M']`).click();
    expect(`label[${selector}='M']`).toHaveClass("active");
    expect(".btn:contains('Add')").not.toHaveClass("disabled");

    await contains(`label[${selector}='Chocolate']`).click();
    expect(`label[${selector}='Chocolate']`).toHaveClass("active");
    expect(".btn:contains('Add')").toHaveClass("disabled");
};

test("pills: excluded value remains selectable and resolves to a valid combination", async () => {
    await setupAndAssertExcludedValuesConfigurator("pills", "name");
});

test("color: excluded value remains selectable and resolves to a valid combination", async () => {
    await setupAndAssertExcludedValuesConfigurator("color", "title");
});
