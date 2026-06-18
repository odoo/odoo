import { test, expect } from "@odoo/hoot";
import { tick } from "@odoo/hoot-mock";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import {
    addProductLineToOrder,
    deactivateAllProgramsExcept,
} from "@pos_loyalty/../tests/unit/utils";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";

definePosModels();

test("TicketScreen.setOrder keeps the reward line and triggers pos.updateRewards", async () => {
    const store = await setupPosEnv();
    const models = store.models;

    const order = store.addNewOrder();
    // Program 8's auto 100% cheapest discount builds a real reward line.
    deactivateAllProgramsExcept(store, [8]);
    order.setPricelist(models["product.pricelist"].get(1));

    await addProductLineToOrder(store, order, { productId: 24, templateId: 24 });
    await store.updateRewards();
    await tick();

    const reward = models["loyalty.reward"].get(4);
    expect(order.lines.filter((l) => l.is_reward_line)).toHaveLength(1);

    // Deselect so setOrder actually switches to this order.
    store.selectedOrderUuid = null;

    let updateRewardsCalled = false;
    const originalUpdateRewards = store.updateRewards.bind(store);
    store.updateRewards = (...args) => {
        updateRewardsCalled = true;
        return originalUpdateRewards(...args);
    };

    const comp = await mountWithCleanup(TicketScreen, {});
    await comp.setOrder(order);

    expect(updateRewardsCalled).toBe(true);
    expect(store.getOrder()).toBe(order);
    const rewardLines = store.getOrder().lines.filter((l) => l.is_reward_line);
    expect(rewardLines).toHaveLength(1);
    expect(rewardLines[0].reward_id.id).toBe(reward.id);
});
