import { expect, test } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setFreeProductReward, setupDepositOrder } from "@pos_loyalty_deposit/../tests/unit/utils";

definePosModels();

test("deposit lines with points, discount and free product rewards", async () => {
    const { store, order, productLine } = await setupDepositOrder();
    const rewardLines = () => order.lines.filter((line) => line.is_reward_line);
    const depositLines = () => order.lines.filter((line) => line.deposit_main_line_id);

    expect(store.models["loyalty.program"].get(8).getEarnedPoints(order)).toBe(1);
    const discount = rewardLines().reduce((total, line) => total + line.priceIncl, 0);
    expect(discount).toBeCloseTo(-productLine.priceIncl);

    setFreeProductReward(store, order);
    order.recomputeRewards();
    const [rebuiltFreeLine] = rewardLines();
    expect(rebuiltFreeLine.product_id).toBe(productLine.product_id);
    expect(depositLines().map((line) => line.deposit_main_line_id)).toEqual([
        productLine,
        rebuiltFreeLine,
    ]);

    order.removeOrderline(rebuiltFreeLine.depositLine);
    expect(rewardLines()).toHaveLength(0);
    expect(order.lines).toEqual([productLine, productLine.depositLine]);
});
