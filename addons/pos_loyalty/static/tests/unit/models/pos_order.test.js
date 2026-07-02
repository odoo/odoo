import { test, describe, expect } from "@odoo/hoot";
import { tick } from "@odoo/hoot-mock";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { addProductLineToOrder } from "@pos_loyalty/../tests/unit/utils";

definePosModels();

const { DateTime } = luxon;

describe("pos.order - loyalty", () => {
    test("_getIgnoredProductIdsTotalDiscount", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();

        const ignoredProductIds = order._getIgnoredProductIdsTotalDiscount();

        expect(ignoredProductIds.length).toBeGreaterThan(0);
    });

    test("getOrderlines, _get_reward_lines and _get_regular_order_lines", async () => {
        const store = await setupPosEnv();

        const order = await getFilledOrder(store);
        const [line1, line2] = order.getOrderlines();
        line1.update({ is_reward_line: true });
        line2.update({ is_reward_line: false, refunded_orderline_id: 123 });

        // Verify getOrderlines method
        const orderedLines = order.getOrderlines();

        expect(orderedLines[0]).toBe(line2);
        expect(orderedLines[1]).toBe(line1);
        expect(orderedLines[0].is_reward_line).toBe(false);
        expect(orderedLines[1].is_reward_line).toBe(true);
        expect(order.getLastOrderline()).toBe(line2);

        // Verify _get_reward_lines method
        const rewardLines = order._get_reward_lines();

        expect(rewardLines).toEqual([line1]);
        expect(rewardLines[0].is_reward_line).toBe(true);

        // Verify _get_regular_order_lines
        const regularLine = await addProductLineToOrder(store, order);

        expect(order.getOrderlines().length).toBe(3);

        const regularLines = order._get_regular_order_lines();

        expect(regularLines.length).toBe(2);
        expect(regularLines[1].id).toBe(regularLine.id);
    });

    test("setPricelist", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = await getFilledOrder(store);
        const partner = models["res.partner"].get(4);
        order.setPartner(partner);
        await store.updatePrograms();
        const appliedLoyaltyCardsLength = order.loyalty_card_ids.length;
        const pricelist2 = models["product.pricelist"].get(2);

        order.setPricelist(pricelist2);
        // Some loyalty cards associated with pricelists other than 2 should have been removed after the pricelist change.
        expect(order.loyalty_card_ids.length).toBeLessThan(appliedLoyaltyCardsLength);
    });

    test("_resetPrograms", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);

        order.uiState.disabledRewards = new Set(["reward1"]);
        order.uiState.codeActivatedProgramRules = ["rule1"];

        await addProductLineToOrder(store, order, {
            is_reward_line: true,
            reward_id: 1,
        });
        await store.updatePrograms();
        expect(order.loyalty_card_ids.length).toBeGreaterThan(0);
        order._resetPrograms();

        expect(order.uiState.disabledRewards.size).toBeEmpty();
        expect(order.uiState.codeActivatedProgramRules.length).toBeEmpty();
        expect(order.loyalty_card_ids.length).toBe(0);
    });

    test("_programIsApplicable", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        // Get loyalty program #1 - type = "ewallet"
        const program = models["loyalty.program"].get(1);
        const partner = models["res.partner"].get(4);
        order.setPartner(partner);
        expect(order._programIsApplicable(program)).toBe(true);

        order.partner_id = false;

        expect(order._programIsApplicable(program)).toBe(false);
    });

    test("_getRealCouponPoints", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = await getFilledOrder(store);
        // Get loyalty card #1 which program_id is #1 (loyalty) and assign it to partner #4
        const card = models["loyalty.card"].get(1);
        card.partner_id = 4;
        const partner = models["res.partner"].get(4);
        order.setPartner(partner);
        await store.updatePrograms();

        await addProductLineToOrder(store, order, {
            is_reward_line: true,
            coupon_id: card,
            points_cost: 5,
            reward_id: 1,
        });
        await store.updatePrograms();
        expect(order._getRealCouponPoints(card.id)).toBe(6); // 10 + 1 (from rule 1) - 5 (spent) = 6
    });

    test("processGiftCard", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        // Get loyalty program #3 - type = "gift_card"
        const giftProgram = models["loyalty.program"].get(3);

        const line = await addProductLineToOrder(store, order, {
            price_unit: 10,
            eWalletGiftCardProgram: giftProgram,
        });
        order.selected_orderline = line;

        const expirationDate = DateTime.now().plus({ days: 1 }).toISODate();
        order.processGiftCard("GIFT9999", 100, expirationDate);

        const giftCard = order.loyalty_card_ids.find(
            (card) => card.program_id.id === giftProgram.id
        );
        expect(giftCard.code).toBe("GIFT9999");
        expect(giftCard.points).toBe(100);
        expect(giftCard.expiration_date.toISODate()).toBe(expirationDate);
    });

    test("_getDiscountableOnOrder", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        await addProductLineToOrder(store, order, {
            qty: 2,
        });

        await addProductLineToOrder(store, order, {
            price_unit: 5,
        });

        // Get loyalty reward #1 - type = "discount"
        const reward = models["loyalty.reward"].get(1);

        const result = order._getDiscountableOnOrder(reward);
        expect(result.discountable).toBe(25);
    });

    test("_computeNItems", async () => {
        const store = await setupPosEnv();
        const models = store.models;

        const order = await getFilledOrder(store);

        // Get loyalty rule #1 - which program_id = 1 (loyalty)
        const rule = models["loyalty.rule"].get(1);

        expect(order.getOrderlines().length).toBe(2);
        expect(order._computeNItems(rule)).toBe(5);
    });

    test("_canGenerateRewards", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        await addProductLineToOrder(store, order, {
            qty: 5,
        });

        // Get loyalty program #2 - type = "ewallet"
        const program = models["loyalty.program"].get(2);

        expect(order._canGenerateRewards(program, 50, 50)).toBe(true);
        expect(order._canGenerateRewards(program, 30, 30)).toBe(false);
    });

    test("isProgramsResettable", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();

        expect(order.isProgramsResettable()).toBe(false);

        order.uiState.disabledRewards = [...new Set(["RULE1"])];
        expect(order.isProgramsResettable()).toBe(true);

        order.uiState.disabledRewards = new Set();
        order.uiState.codeActivatedProgramRules.push("RULE2");
        expect(order.isProgramsResettable()).toBe(true);

        const card = store.models["loyalty.card"].get(1);
        order.loyalty_card_ids = [["link", card]];
        expect(order.isProgramsResettable()).toBe(true);
    });

    test("removeOrderline", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        // Get loyalty reward #1 - type = "discount"
        const reward = models["loyalty.reward"].get(1);
        // Get loyalty card #1 - which program_id = 1 (loyalty)
        const coupon = models["loyalty.card"].get(1);

        const rewardLine = await addProductLineToOrder(store, order, {
            is_reward_line: true,
            reward_id: reward,
            coupon_id: coupon,
            reward_identifier_code: "ABC123",
        });

        const normalLine = await addProductLineToOrder(store, order, {
            price_unit: 20,
            is_reward_line: false,
        });

        expect(order.getOrderlines().length).toBe(2);

        const result = order.removeOrderline(rewardLine);
        expect(result).toBe(true);
        expect(order.getOrderlines().length).toBe(1);

        const remainingLines = order.getOrderlines();
        expect(remainingLines.length).toBe(1);
        expect(remainingLines[0].id).toBe(normalLine.id);
        expect(remainingLines[0].is_reward_line).toBe(false);
    });

    test("isSaleDisallowed", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        // Get loyalty program #3 - type = "gift_card"
        const giftProgram = models["loyalty.program"].get(3);

        const result = order.isSaleDisallowed({}, { eWalletGiftCardProgram: giftProgram });
        expect(result).toBe(false);
    });

    test("setPartner and getLoyaltyPoints", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = await getFilledOrder(store);

        const partner1 = models["res.partner"].get(1);
        const partner2 = models["res.partner"].get(3);
        await store.updatePrograms();
        expect(order.loyalty_card_ids.filter((lc) => lc.program_id.is_nominative).length).toBe(0);
        order.setPartner(partner1);
        await store.updatePrograms();
        expect(
            order.loyalty_card_ids.filter((lc) => lc.program_id.is_nominative).length
        ).toBeGreaterThan(0);
        order.setPartner(partner2);
        expect(order.loyalty_card_ids.filter((lc) => lc.program_id.is_nominative).length).toBe(0); // Removed nominative loyalty cards after partner change
        await store.updatePrograms();
        expect(
            order.loyalty_card_ids.filter((lc) => lc.program_id.is_nominative).length
        ).toBeGreaterThan(0); // Reassigned new nominative loyalty cards after partner change

        const loyaltyStats = order.getLoyaltyPoints();
        expect(loyaltyStats.length).toBe(2); // Two loyalty cards as `loyalty` program type applied
        expect(loyaltyStats[0].points.name).toBe("Points");
        expect(loyaltyStats[0].points.won).toBe(1);
        expect(loyaltyStats[0].points.balance).toBe(0);
        expect(loyaltyStats[1].points.name).toBe("Points");
        expect(loyaltyStats[1].points.won).toBe(5);
        expect(loyaltyStats[1].points.balance).toBe(0);
    });

    test("getLoyaltyPoints adapts to qty decreasing", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        const partner1 = models["res.partner"].get(1);
        order.setPartner(partner1);
        await store.orderUpdateLoyaltyPrograms();
        const reward = models["loyalty.reward"].get(3);
        const loyalty_card = models["loyalty.card"].get(4);
        const line = await addProductLineToOrder(store, order, {
            productId: 10,
            templateId: 10,
            qty: 3,
        });
        await store.orderUpdateLoyaltyPrograms();
        order._applyReward(reward, loyalty_card.id);
        const loyaltyStats = order.getLoyaltyPoints().find((stat) => stat.couponId === "4"); // same as loyalty_card.id

        expect(loyaltyStats.points.won).toBe(0);
        expect(loyaltyStats.points.spent).toBe(3);
        expect(loyaltyStats.points.total).toBe(0);
        expect(loyaltyStats.points.balance).toBe(3);
        line.setQuantity(2);
        await store.updateRewards();
        await tick();
        const loyaltyStats2 = order.getLoyaltyPoints().find((stat) => stat.couponId === "4"); // same as loyalty_card.id
        expect(loyaltyStats2.points.won).toBe(0);
        expect(loyaltyStats2.points.spent).toBe(2);
        expect(loyaltyStats2.points.total).toBe(1);
        expect(loyaltyStats2.points.balance).toBe(3);
    });

    test("reward amount tax included cheapest product", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();

        const line = await addProductLineToOrder(store, order, {
            productId: 24,
            templateId: 24,
            qty: 1,
        });
        expect(line.prices.total_included).toBe(10);
        expect(line.prices.total_excluded).toBe(8.7);
        await store.updateRewards();
        await tick();
        expect(order.getOrderlines().length).toBe(2);
        const rewardLine = order._get_reward_lines()[0];
        expect(rewardLine.prices.total_included).toBe(-10);
    });
});
