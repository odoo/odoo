import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

test("Pricelist: Precedence Rules (Variant > Template > Category > Global)", async () => {
    const store = await setupPosEnv();
    const pricelist = store.models["product.pricelist"].create({
        name: "Test Pricelist",
    });

    const category = store.models["product.category"].create({ name: "Test Category" });
    const productTemplate = store.models["product.template"].create({
        name: "Test Template",
        list_price: 100,
        categ_id: category,
    });
    const product = store.models["product.product"].create({
        product_tmpl_id: productTemplate,
        lst_price: 100,
    });

    // 1. Global Rule
    const globalRule = store.models["product.pricelist.item"].create({
        pricelist_id: pricelist,
        compute_price: "fixed",
        fixed_price: 90,
    });
    pricelist.update({ item_ids: [globalRule] });
    pricelist.computeRuleIndexes();
    expect(product.getPrice(pricelist, 1, 0, false, product)).toBe(90);

    // 2. Category Rule (should win over Global)
    const categoryRule = store.models["product.pricelist.item"].create({
        pricelist_id: pricelist,
        categ_id: category,
        compute_price: "fixed",
        fixed_price: 80,
    });
    pricelist.update({ item_ids: [globalRule, categoryRule] });
    pricelist.computeRuleIndexes();
    expect(product.getPrice(pricelist, 1, 0, false, product)).toBe(80);

    // 3. Template Rule (should win over Category)
    const templateRule = store.models["product.pricelist.item"].create({
        pricelist_id: pricelist,
        product_tmpl_id: productTemplate,
        compute_price: "fixed",
        fixed_price: 70,
    });
    pricelist.update({ item_ids: [globalRule, categoryRule, templateRule] });
    pricelist.computeRuleIndexes();
    expect(product.getPrice(pricelist, 1, 0, false, product)).toBe(70);

    // 4. Variant Rule (should win over Template)
    const variantRule = store.models["product.pricelist.item"].create({
        pricelist_id: pricelist,
        product_id: product,
        compute_price: "fixed",
        fixed_price: 60,
    });
    pricelist.update({ item_ids: [globalRule, categoryRule, templateRule, variantRule] });
    pricelist.computeRuleIndexes();
    expect(product.getPrice(pricelist, 1, 0, false, product)).toBe(60);
});

test("Pricelist: Min Quantity logic", async () => {
    const store = await setupPosEnv();
    const pricelist = store.models["product.pricelist"].create({
        name: "Qty Pricelist",
    });

    const productTemplate = store.models["product.template"].create({
        name: "Qty Product",
        list_price: 100,
    });
    const product = store.models["product.product"].create({
        product_tmpl_id: productTemplate,
        lst_price: 100,
    });

    const ruleSmall = store.models["product.pricelist.item"].create({
        pricelist_id: pricelist,
        product_id: product,
        compute_price: "fixed",
        fixed_price: 50,
        min_quantity: 0,
    });
    const ruleLarge = store.models["product.pricelist.item"].create({
        pricelist_id: pricelist,
        product_id: product,
        compute_price: "fixed",
        fixed_price: 20,
        min_quantity: 10,
    });

    pricelist.update({ item_ids: [ruleSmall, ruleLarge] });
    pricelist.computeRuleIndexes();

    // Qty 1 -> should use ruleSmall (50)
    expect(product.getPrice(pricelist, 1, 0, false, product)).toBe(50);
    // Qty 10 -> should use ruleLarge (20)
    expect(product.getPrice(pricelist, 10, 0, false, product)).toBe(20);
    // Qty 15 -> should use ruleLarge (20)
    expect(product.getPrice(pricelist, 15, 0, false, product)).toBe(20);
});

test("Pricelist: Nested Pricelists (Pricelist of Pricelist)", async () => {
    const store = await setupPosEnv();

    // Base Pricelist: -10% discount
    const basePricelist = store.models["product.pricelist"].create({
        name: "Base Pricelist",
    });
    const baseRule = store.models["product.pricelist.item"].create({
        pricelist_id: basePricelist,
        compute_price: "percentage",
        percent_price: 10,
        base: "list_price",
    });
    basePricelist.update({ item_ids: [baseRule] });
    basePricelist.computeRuleIndexes();

    // Nested Pricelist: Base + another -5$ surcharge
    const nestedPricelist = store.models["product.pricelist"].create({
        name: "Nested Pricelist",
    });
    const nestedRule = store.models["product.pricelist.item"].create({
        pricelist_id: nestedPricelist,
        compute_price: "formula", // formula to use base + surcharge
        base: "pricelist",
        base_pricelist_id: basePricelist,
        price_surcharge: 5,
    });
    nestedPricelist.update({ item_ids: [nestedRule] });
    nestedPricelist.computeRuleIndexes();

    const productTemplate = store.models["product.template"].create({
        name: "Nested Test Product",
        list_price: 100,
    });
    const product = store.models["product.product"].create({
        product_tmpl_id: productTemplate,
        lst_price: 100,
    });

    // Calculation: (100 - 10%) + 5 = 90 + 5 = 95
    expect(product.getPrice(nestedPricelist, 1, 0, false, product)).toBe(95);
});

test("Pricelist: rule targeting a product missing from the PoS is not applied globally", async () => {
    const store = await setupPosEnv();

    // Rules whose product/template was archived are dropped from the local data by
    // filter_local_data, but the rule itself is kept, so its raw id points to a
    // record that is not in the store.
    const archivedTmplId = 99999;
    const archivedVariantId = 99998;
    const [pricelist] = store.models.loadConnectedData({
        "product.pricelist": [
            {
                id: 90,
                name: "Orphan Rules Pricelist",
                display_name: "Orphan Rules Pricelist",
                currency_id: 1,
                item_ids: [900, 901],
            },
        ],
        "product.pricelist.item": [
            {
                id: 900,
                pricelist_id: 90,
                product_tmpl_id: archivedTmplId,
                product_id: false,
                categ_id: false,
                base: "list_price",
                compute_price: "fixed",
                fixed_price: 5,
                min_quantity: 0,
            },
            {
                id: 901,
                pricelist_id: 90,
                product_tmpl_id: archivedTmplId,
                product_id: archivedVariantId,
                categ_id: false,
                base: "list_price",
                compute_price: "fixed",
                fixed_price: 7,
                min_quantity: 0,
            },
        ],
    })["product.pricelist"];

    expect(pricelist.getGlobalRulesIds()).toEqual([]);

    const productTmpl = store.models["product.template"].get(5);
    const product = productTmpl.product_variant_ids[0];
    expect(productTmpl.getPrice(pricelist, 1, 0, false, product)).toBe(productTmpl.list_price);
});

test("Nested Pricelists with different currencies", async () => {
    const store = await setupPosEnv();

    const mxn = store.models["res.currency"].create({
        name: "MXN",
        symbol: "MX$",
        position: "before",
        rounding: 0.01,
        rate: 2.0,
        decimal_places: 2,
    });

    // POS uses MXN
    const config = store.models["pos.config"].getFirst();
    config.update({ currency_id: mxn });

    // Base pricelist in USD: +10 USD surcharge on list_price
    const usd = store.models["res.currency"].get(1);
    const basePricelist = store.models["product.pricelist"].create({
        name: "USD Pricelist",
        currency_id: usd,
    });
    const baseRule = store.models["product.pricelist.item"].create({
        pricelist_id: basePricelist,
        compute_price: "formula",
        base: "list_price",
        price_surcharge: 10,
    });
    basePricelist.update({ item_ids: [baseRule] });
    basePricelist.computeRuleIndexes();

    // POS pricelist in MXN: based on USD pricelist + 25% discount
    const posPricelist = store.models["product.pricelist"].create({
        name: "MXN Pricelist",
        currency_id: mxn,
    });
    const posRule = store.models["product.pricelist.item"].create({
        pricelist_id: posPricelist,
        compute_price: "percentage",
        percent_price: 25,
        base: "pricelist",
        base_pricelist_id: basePricelist,
    });
    posPricelist.update({ item_ids: [posRule] });
    posPricelist.computeRuleIndexes();

    const productTemplate = store.models["product.template"].create({
        name: "Test Product",
        list_price: 100,
    });
    const product = store.models["product.product"].create({
        product_tmpl_id: productTemplate,
        lst_price: 100,
    });

    // 100 MXN → 50 USD, + 10 surcharge = 60 USD → 120 MXN
    // 120 MXN - 25% = 90 MXN
    expect(product.getPrice(posPricelist, 1, 0, false, product)).toBe(90);
});
