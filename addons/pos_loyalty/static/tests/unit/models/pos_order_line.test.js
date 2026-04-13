import { test, describe, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { addProductLineToOrder } from "@pos_loyalty/../tests/unit/utils";

definePosModels();

describe("pos.order.line - loyalty", () => {
    test("getEWalletGiftCardProgramType", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        // Get loyalty program #2 - type = "ewallet"
        const program = models["loyalty.program"].get(2);

        const line = await addProductLineToOrder(store, order, {
            _e_wallet_program_id: program,
        });

        expect(line.getEWalletGiftCardProgramType()).toBe(`${program.program_type}`);
    });

    test("ignoreLoyaltyPoints", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        // Get loyalty program #2 - type = "ewallet"
        const programA = models["loyalty.program"].get(2);
        // Get loyalty program #4 - type = "ewallet"
        const programB = models["loyalty.program"].get(4);

        const line = await addProductLineToOrder(store, order);
        line.update({ _e_wallet_program_id: programB });

        expect(line.ignoreLoyaltyPoints({ program: programA })).toBe(true);
    });

    test("gift card reward lines are excluded from global discount", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        const card = models["loyalty.card"].get(3);

        const regularLine = await addProductLineToOrder(store, order);
        expect(regularLine.isGlobalDiscountApplicable()).toBe(true);

        const giftCardLine = await addProductLineToOrder(store, order, {
            is_reward_line: true,
            coupon_id: card,
        });
        expect(giftCardLine.isGiftCardOrEWalletReward()).toBe(true);
        expect(giftCardLine.isGlobalDiscountApplicable()).toBe(false);
    });

    test("promotion reward lines are not excluded from global discount", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        const loyaltyCard = models["loyalty.card"].get(1);

        const rewardLine = await addProductLineToOrder(store, order, {
            is_reward_line: true,
            coupon_id: loyaltyCard,
        });
        expect(rewardLine.isGiftCardOrEWalletReward()).toBe(false);
        expect(rewardLine.isGlobalDiscountApplicable()).toBe(true);
    });

    test("getGiftCardOrEWalletBalance", async () => {
        const store = await setupPosEnv();
        const models = store.models;

        // Get loyalty card #3 which program_id = 3 (gift_card)
        const card = models["loyalty.card"].get(3);

        const order = store.addNewOrder();

        const line = await addProductLineToOrder(store, order, {
            is_reward_line: true,
            coupon_id: card,
        });

        const balance = line.getGiftCardOrEWalletBalance();

        expect(balance).toBeOfType("string");
        expect(balance).toMatch(new RegExp(`${card.points}`));
    });
});
