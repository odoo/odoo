import { expect, test } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupDepositOrder } from "@pos_loyalty_deposit/../tests/unit/utils";

definePosModels();

test("_countsForPoints", async () => {
    const { store, productLine } = await setupDepositOrder();
    const rule = store.models["loyalty.rule"].get(5);

    expect(rule._countsForPoints(productLine)).toBe(true);
    expect(rule._countsForPoints(productLine.depositLine)).toBe(false);
});
