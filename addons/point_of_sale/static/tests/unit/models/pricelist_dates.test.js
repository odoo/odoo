import { expect, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

import { definePosModels } from "../data/generate_model_definitions.js";
import { setupPosEnv } from "../utils.js";

import { DateTime } from "luxon";

definePosModels();

for (const scope of ["global", "template", "variant", "category"]) {
    test(`scheduled ${scope} prices activate and expire without a reload`, async () => {
        const store = await setupPosEnv();
        const template = store.models["product.template"].get(5);
        template.categ_id = store.models["product.category"].get(4);
        const variant = template.product_variant_ids[0];
        const pricelist = store.models["product.pricelist"].create({ id: 990 });
        const start = DateTime.utc(2026, 3, 8, 7);
        const end = start.plus({ hours: 1 });
        store.models["product.pricelist.item"].create({
            id: 991,
            pricelist_id: pricelist,
            product_tmpl_id: scope === "template" ? template : false,
            product_id: scope === "variant" ? variant : false,
            categ_id: scope === "category" ? template.categ_id : false,
            date_start: start,
            date_end: end,
            compute_price: "fixed",
            fixed_price: 7,
        });
        let now = start.minus({ seconds: 1 });
        patchWithCleanup(DateTime, { now: () => now });
        const price = () => template.getPrice(pricelist, 1, 0, false, variant);
        const base = variant.lst_price;
        expect(price()).toBe(base);
        now = start;
        expect(price()).toBe(7);
        now = end;
        expect(price()).toBe(7);
        now = end.plus({ seconds: 1 });
        expect(price()).toBe(base);
    });
}

test("general rules follow additions, category changes and deletion", async () => {
    const store = await setupPosEnv();
    const template = store.models["product.template"].get(5);
    template.categ_id = store.models["product.category"].get(4);
    const pricelist = store.models["product.pricelist"].create({ id: 990 });
    expect(pricelist.getGeneralRulesIdsByCategories([])).toEqual([]);
    const rule = store.models["product.pricelist.item"].create({
        id: 991,
        pricelist_id: pricelist,
        compute_price: "fixed",
        fixed_price: 7,
    });
    expect(pricelist.getGeneralRulesIdsByCategories([])).toEqual([991]);
    rule.categ_id = template.categ_id;
    expect(pricelist.getGeneralRulesIdsByCategories([])).toEqual([]);
    expect(pricelist.getGeneralRulesIdsByCategories([template.categ_id.id])).toEqual([
        991,
    ]);
    rule.delete();
    expect(pricelist.getGeneralRulesIdsByCategories([template.categ_id.id])).toEqual(
        [],
    );
});

test("incremental general rules retain server pricing precedence", async () => {
    const store = await setupPosEnv();
    const pricelist = store.models["product.pricelist"].create({ id: 990 });
    const category = store.models["product.category"].get(4);
    const items = store.models["product.pricelist.item"];
    const createRule = (id, min_quantity, categ_id = false) =>
        items.create({
            id,
            min_quantity,
            categ_id,
            pricelist_id: pricelist,
            compute_price: "fixed",
            fixed_price: id,
        });
    createRule(991, 1);
    createRule(992, 10);
    createRule(993, 1, category);
    createRule(994, 10);
    expect(pricelist.getGeneralRulesIdsByCategories([category.id])).toEqual([
        993, 994, 992, 991,
    ]);
    expect(pricelist.getGeneralRulesIdsByCategories([])).toEqual([994, 992, 991]);
});
