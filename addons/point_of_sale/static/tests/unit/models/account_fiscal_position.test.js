import { expect, test } from "@odoo/hoot";
import { setupPosEnv } from "../utils";
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
