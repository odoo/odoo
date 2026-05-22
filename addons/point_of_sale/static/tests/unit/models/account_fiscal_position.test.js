import { expect, test } from "@odoo/hoot";
import { expectFormattedPrice, setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

test("getTaxesAfterFiscalPosition: empty tax_ids, taxes have fiscal_position_ids → returns []", async () => {
    const store = await setupPosEnv();
    const models = store.models;
    const emptyFp = models["account.fiscal.position"].get(2);
    // tax id=1 has fiscal_position_ids: [1], so it is managed by a fiscal position
    const taxWithFp = models["account.tax"].get(1);

    const result = emptyFp.getTaxesAfterFiscalPosition([taxWithFp]);
    expect(result).toEqual([]);
});

test("getTaxesAfterFiscalPosition: empty tax_ids, taxes have no fiscal_position_ids → passes taxes through", async () => {
    const store = await setupPosEnv();
    const models = store.models;
    const emptyFp = models["account.fiscal.position"].get(2);
    // tax id=2 has fiscal_position_ids: [], so it is not managed by any fiscal position
    const taxWithoutFp = models["account.tax"].get(2);

    const result = emptyFp.getTaxesAfterFiscalPosition([taxWithoutFp]);
    expect(result).toEqual([taxWithoutFp]);
});

test("getTaxesAfterFiscalPosition: fiscal position has tax_ids, unmapped tax passes through", async () => {
    const store = await setupPosEnv();
    const models = store.models;
    // fiscal position id=1 has tax_ids but no tax_map entry for tax id=2
    const fp = models["account.fiscal.position"].get(1);
    const unmappedTax = models["account.tax"].get(2);

    const result = fp.getTaxesAfterFiscalPosition([unmappedTax]);
    expect(result).toEqual([unmappedTax]);
});

test("getProductInfo: VAT uses pricelist price and fiscal-position-mapped tax", async () => {
    const store = await setupPosEnv();
    const models = store.models;

    const tax15 = models["account.tax"].get(1);
    const tax30 = models["account.tax"].create({
        id: 30,
        name: "30%",
        amount_type: "percent",
        amount: 30,
    });
    const fp = models["account.fiscal.position"].get(1);
    fp.update({ tax_map: { [tax15.id]: [tax30.id] } });

    const pricelist = models["product.pricelist"].create({ name: "Double" });
    const pricelistItem = models["product.pricelist.item"].create({
        pricelist_id: pricelist,
        compute_price: "fixed",
        fixed_price: 200,
    });
    pricelist.update({ item_ids: [pricelistItem] });
    pricelist.computeRuleIndexes();

    const productTemplate = models["product.template"].create({
        name: "Test product",
        list_price: 100,
        taxes_id: [tax15],
    });
    models["product.product"].create({ product_tmpl_id: productTemplate, lst_price: 100 });

    const order = store.addNewOrder();
    order.pricelist_id = pricelist;
    order.fiscal_position_id = fp;

    const productInfo = await store.getProductInfo(productTemplate, 1, 0);

    expect(productInfo.taxName).toBe("30%");
    expectFormattedPrice(productInfo.taxAmount, "$ 60.00");
});
