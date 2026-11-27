import { expect, test } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setFreeProductReward, setupDepositOrder } from "@pos_loyalty_deposit/../tests/unit/utils";

definePosModels();

test("applyReward", async () => {
    const { store, order, productLine } = await setupDepositOrder();
    const rewardLine = setFreeProductReward(store, order);
    const depositLine = rewardLine.depositLine;

    expect(depositLine.product_id).toBe(productLine.depositLine.product_id);
    expect(depositLine.qty).toBe(rewardLine.qty);
    expect(depositLine.price_unit).toBe(productLine.depositLine.price_unit);
    expect(depositLine.is_reward_line).not.toBe(true);
});

test("removeOrderline", async () => {
    const { store, order, productLine } = await setupDepositOrder();
    const rewardLine = setFreeProductReward(store, order);
    order.removeOrderline(rewardLine.depositLine);
    expect(order.lines).toEqual([productLine, productLine.depositLine]);
});
