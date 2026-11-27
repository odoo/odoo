import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { deactivateAllProgramsExcept } from "@pos_loyalty/../tests/unit/utils";

export async function setupDepositOrder() {
    const store = await setupPosEnv();
    store.config.module_pos_deposit = true;
    deactivateAllProgramsExcept(store, [8]);
    const order = store.addNewOrder();
    const productLine = await store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(5) },
        order
    );
    order.recomputeRewards();
    return { store, order, productLine };
}

export function setFreeProductReward(store, order) {
    store.models["loyalty.reward"].get(4).update({
        reward_type: "product",
        reward_product_id: store.models["product.product"].get(5),
    });
    order.active_rewards = [{ reward_id: 4 }];
    order.recomputeRewards();
    return order.lines.find((line) => line.is_reward_line);
}
