import { expect, test } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupDepositOrder } from "@pos_loyalty_deposit/../tests/unit/utils";

definePosModels();

test("_isDiscountableLine", async () => {
    const { store, productLine } = await setupDepositOrder();
    const reward = store.models["loyalty.reward"].get(4);

    expect(reward._isDiscountableLine(productLine)).toBe(true);
    expect(reward._isDiscountableLine(productLine.depositLine)).toBe(false);
});
