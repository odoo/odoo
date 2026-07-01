import { expect, test } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { addProductLineToOrder } from "@pos_loyalty/../tests/unit/utils";

definePosModels();

async function setupPePosEwalletOrder({ price_unit = 50, qty = 1 } = {}) {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    await addProductLineToOrder(store, order, { price_unit, qty });
    return { store, order };
}

test("PE eWallet reward line keeps tax-included wallet balance", async () => {
    const { store, order } = await setupPePosEwalletOrder();
    const models = store.models;
    const reward = models["loyalty.reward"].get(50);
    const coupon = models["loyalty.card"].get(2);

    expect(order.company.country_id.code).toBe("PE");

    const rewardLines = order._getRewardLineValuesDiscount({
        reward,
        coupon_id: coupon.id,
    });

    expect(rewardLines).toHaveLength(1);
    expect(rewardLines[0].points_cost).toBe(coupon.points);
    expect(rewardLines[0].price_unit).toBe(-coupon.points);
});

test("PE eWallet payment line total matches wallet balance", async () => {
    const { order } = await setupPePosEwalletOrder();
    const models = order.models;
    const coupon = models["loyalty.card"].get(2);

    order._applyReward(models["loyalty.reward"].get(50), coupon.id);
    order.triggerRecomputeAllPrices();

    const rewardLine = order._get_reward_lines()[0];
    expect(rewardLine.prices.total_included).toBe(-coupon.points);
    expect(rewardLine.points_cost).toBe(coupon.points);
});
