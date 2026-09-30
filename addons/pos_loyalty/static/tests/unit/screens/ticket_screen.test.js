import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { addProductLineToOrder } from "@pos_loyalty/../tests/unit/utils";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

definePosModels();

test("TicketScreen.setOrder keeps reward line and triggers pos.updateRewards", async () => {
    const store = await setupPosEnv();
    const models = store.models;

    const order = store.addNewOrder();
    const reward = models["loyalty.reward"].get(1);
    const coupon = models["loyalty.card"].get(1);

    await addProductLineToOrder(store, order, {
        is_reward_line: true,
        reward_id: reward,
        coupon_id: coupon,
        reward_identifier_code: "LOAD-ORDER-REWARD",
        points_cost: 10,
    });
    order.uiState.couponPointChanges = {};
    store.selectedOrderUuid = null;

    let updateRewardsCalled = false;
    const originalUpdateRewards = store.updateRewards.bind(store);
    store.updateRewards = () => {
        updateRewardsCalled = true;
        return originalUpdateRewards();
    };
    const comp = await mountWithCleanup(TicketScreen, {});
    await comp.setOrder(order);

    expect(updateRewardsCalled).toBe(true);
    const currentOrder = store.getOrder();
    expect(currentOrder).toBe(order);
    const rewardLines = currentOrder.lines.filter((l) => l.is_reward_line);
    expect(rewardLines.length).toBe(1);
    expect(rewardLines[0].reward_id.id).toBe(reward.id);
    expect(rewardLines[0].coupon_id.id).toBe(coupon.id);
});
