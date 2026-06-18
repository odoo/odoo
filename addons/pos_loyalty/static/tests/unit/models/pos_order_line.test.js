import { test, describe, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { addProductLineToOrder } from "@pos_loyalty/../tests/unit/utils";

definePosModels();

describe("pos.order.line - loyalty", () => {
    test("gift card reward lines are excluded from global discount", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        const card = models["loyalty.card"].get(3);

        // Add plain lines (distinct products so they don't merge), then flag the second as a
        // gift-card reward via update: a reward line can't be born through addProductLineToOrder
        // (recomputeRewards drops it and the merge path chokes on reward-line pricing).
        const regularLine = await addProductLineToOrder(store, order, {
            productId: 6,
            templateId: 6,
        });
        const giftCardLine = await addProductLineToOrder(store, order, {
            productId: 5,
            templateId: 5,
        });
        giftCardLine.update({ is_reward_line: true, card_id: card });

        expect(regularLine.isGlobalDiscountApplicable()).toBe(true);
        expect(giftCardLine.isGlobalDiscountApplicable()).toBe(false);
    });

    test("promotion reward lines are not excluded from global discount", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        const loyaltyCard = models["loyalty.card"].get(1);

        const rewardLine = await addProductLineToOrder(store, order);
        rewardLine.update({ is_reward_line: true, card_id: loyaltyCard });
        expect(rewardLine.isGlobalDiscountApplicable()).toBe(true);
    });

    test("getPaymentProgramBalance", async () => {
        const store = await setupPosEnv();
        const models = store.models;

        // Get loyalty card #3 which program_id = 3 (gift_card, a payment program)
        const card = models["loyalty.card"].get(3);

        const order = store.addNewOrder();

        const line = await addProductLineToOrder(store, order);
        line.update({ is_reward_line: true, card_id: card });

        expect(line.getPaymentProgramBalance()).toBe(card.points);
    });
});
