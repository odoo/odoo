import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

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
        price_discount: 0,
        price_surcharge: 10,
    });
    basePricelist.update({ item_ids: [baseRule] });
    basePricelist.computeGeneralRulesByCateg();

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
    posPricelist.computeGeneralRulesByCateg();

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
