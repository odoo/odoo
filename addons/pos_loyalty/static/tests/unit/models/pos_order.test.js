import { test, describe, expect } from "@odoo/hoot";
import { tick } from "@odoo/hoot-mock";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import {
    addProductLineToOrder,
    deactivateAllProgramsExcept,
} from "@pos_loyalty/../tests/unit/utils";
import { onRpc } from "@web/../tests/web_test_helpers";

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
        const order = store.addNewOrder();

        const pricelist2 = models["product.pricelist"].get(2);

        order.uiState.couponPointChanges = {
            key1: { program_id: 1, points: 100 },
            key2: { program_id: 2, points: 50 },
        };

        order.setPricelist(pricelist2);

        const remainingKeys = Object.keys(order.uiState.couponPointChanges);
        expect(remainingKeys.length).toBe(1);
        expect(order.uiState.couponPointChanges[remainingKeys[0]].program_id).toBe(2);
    });

    test("_resetPrograms", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();

        order.uiState.disabledRewards = new Set(["reward1"]);
        order.uiState.codeActivatedProgramRules = ["rule1"];
        order.uiState.couponPointChanges = { key1: { points: 100 } };

        await addProductLineToOrder(store, order, {
            is_reward_line: true,
        });

        order._resetPrograms();

        expect(order.uiState.disabledRewards.size).toBeEmpty();
        expect(order.uiState.codeActivatedProgramRules.length).toBeEmpty();
        expect(order.uiState.couponPointChanges).toMatchObject({});
    });

    test("_programIsApplicable", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        // Get loyalty program #1 - type = "ewallet"
        const program = models["loyalty.program"].get(1);

        expect(order._programIsApplicable(program)).toBe(true);

        program.partner_id = false;
        program.is_nominative = true;

        expect(order._programIsApplicable(program)).toBe(false);
    });

    test("_getRealCouponPoints", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        // Get loyalty card #1 which program_id = 1 (loyalty)
        const card = models["loyalty.card"].get(1);

        order.uiState.couponPointChanges = {
            1: {
                coupon_id: 1,
                program_id: 1,
                points: 25,
            },
        };

        await addProductLineToOrder(store, order, {
            is_reward_line: true,
            coupon_id: card,
            points_cost: 5,
        });

        expect(order._getRealCouponPoints(card.id)).toBe(30);
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

        const couponChanges = Object.values(order.uiState.couponPointChanges);
        expect(couponChanges.length).toBe(1);
        expect(couponChanges[0].code).toBe("GIFT9999");
        expect(couponChanges[0].points).toBe(100);
        expect(couponChanges[0].expiration_date).toBe(expirationDate);
        expect(couponChanges[0].manual).toBe(true);
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

    test("_getDiscountableOnCheapest excludes fixed tax for non-ewallet program", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        // Tax #1 (15%) becomes a fixed tax, tax #2 (25%) stays as percent
        const fixedTax = models["account.tax"].get(1);
        const percentTax = models["account.tax"].get(2);
        fixedTax.amount_type = "fixed";
        models["product.template"].get(5).taxes_id = [fixedTax, percentTax];

        await addProductLineToOrder(store, order, {
            templateId: 5,
            productId: 5,
        });

        // Reward #4 - cheapest discount, program type "promotion"
        const reward = models["loyalty.reward"].get(4);
        reward.all_discount_product_ids = [models["product.product"].get(5)];

        order.triggerRecomputeAllPrices();
        const result = order._getDiscountableOnCheapest(reward);

        const taxKeys = Object.keys(result.discountablePerTax);
        expect(taxKeys.length).toBe(1);
        const taxIds = taxKeys[0].split(",").map(Number);
        expect(taxIds).toInclude(percentTax.id);
        expect(taxIds).not.toInclude(fixedTax.id);
    });

    test("_getDiscountableOnSpecific excludes fixed tax for non-ewallet program", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        const fixedTax = models["account.tax"].get(1);
        const percentTax = models["account.tax"].get(2);
        fixedTax.amount_type = "fixed";
        models["product.template"].get(5).taxes_id = [fixedTax, percentTax];

        await addProductLineToOrder(store, order, {
            templateId: 5,
            productId: 5,
        });

        const reward = models["loyalty.reward"].get(4);
        reward.discount_applicability = "specific";
        reward.all_discount_product_ids = [models["product.product"].get(5)];

        order.triggerRecomputeAllPrices();
        const result = order._getDiscountableOnSpecific(reward);

        const taxKeys = Object.keys(result.discountablePerTax);
        expect(taxKeys.length).toBe(1);
        const taxIds = taxKeys[0].split(",").map(Number);
        expect(taxIds).toInclude(percentTax.id);
        expect(taxIds).not.toInclude(fixedTax.id);
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

    test("product-restricted rules require a valid product in the order", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        // Restrict loyalty rule #1 (program #1) to product #5 only
        const rule = models["loyalty.rule"].get(1);
        rule.any_product = false;
        const program = models["loyalty.program"].get(1);

        // Order only contains product #1, which is not valid for the rule
        await addProductLineToOrder(store, order, { qty: 1 });

        expect(order.pointsForPrograms([program])[program.id]).toEqual([]);
        expect(order._canGenerateRewards(program, 1000, 1000)).toBe(false);

        // Adding the valid product #5 makes the rule apply
        await addProductLineToOrder(store, order, { templateId: 5, productId: 5 });

        expect(order.pointsForPrograms([program])[program.id]).toEqual([{ points: 1 }]);
        expect(order._canGenerateRewards(program, 1000, 1000)).toBe(true);
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

        order.uiState.codeActivatedProgramRules = [];
        order.uiState.couponPointChanges = { key1: { points: 10 } };
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
        const order = store.addNewOrder();

        const partner1 = models["res.partner"].get(1);
        const partner2 = models["res.partner"].get(3);

        order.setPartner(partner1);

        order.uiState.couponPointChanges = {
            key1: { program_id: 5, points: 100 },
            key2: { program_id: 2, points: 50 },
        };

        order.setPartner(partner2);

        const remainingKeys = Object.keys(order.uiState.couponPointChanges);
        expect(remainingKeys.length).toBe(1);
        expect(order.uiState.couponPointChanges[remainingKeys[0]].program_id).toBe(2);

        // Verify getLoyaltyPoints method
        order.uiState.couponPointChanges = {
            1: {
                coupon_id: 1,
                program_id: 1,
                points: 25,
            },
        };

        const loyaltyStats = order.getLoyaltyPoints();
        expect(loyaltyStats.length).toBe(1);
        expect(loyaltyStats[0].points.name).toBe("Points");
        expect(loyaltyStats[0].points.won).toBe(25);
        expect(loyaltyStats[0].points.balance).toBe(10);
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
        const loyaltyStats = order.getLoyaltyPoints();
        expect(loyaltyStats[0].points.won).toBe(0);
        expect(loyaltyStats[0].points.spent).toBe(3);
        expect(loyaltyStats[0].points.total).toBe(0);
        expect(loyaltyStats[0].points.balance).toBe(3);
        line.setQuantity(2);
        await store.updateRewards();
        await tick();
        const loyaltyStats2 = order.getLoyaltyPoints();
        expect(loyaltyStats2[0].points.won).toBe(0);
        expect(loyaltyStats2[0].points.spent).toBe(2);
        expect(loyaltyStats2[0].points.total).toBe(1);
        expect(loyaltyStats2[0].points.balance).toBe(3);
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

    test("already applied discount reward is not claimable again", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        deactivateAllProgramsExcept(store, [8]);

        // 2 units grant 2 points, the reward costs 1
        await addProductLineToOrder(store, order, { qty: 2 });
        await store.updateRewards();
        await tick();
        expect(order._get_reward_lines()).toHaveLength(1);

        await addProductLineToOrder(store, order, { templateId: 5, productId: 5 });
        await store.updateRewards();
        await tick();
        expect(order._get_reward_lines()).toHaveLength(1);
        // Not claimable again automatically, still claimable manually
        expect(
            order.getClaimableRewards(false, false, true).filter(({ reward }) => reward.id === 4)
        ).toHaveLength(0);
        expect(order.getClaimableRewards().filter(({ reward }) => reward.id === 4)).toHaveLength(1);
    });

    test("reward max discount quantity", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        const models = store.models;
        deactivateAllProgramsExcept(store, [1, 9]);
        onRpc("loyalty.card", "get_loyalty_card_partner_by_code", () => false);

        const loyalty_program = models["loyalty.program"].get(1);
        const loyalty_reward = models["loyalty.reward"].get(4);
        const loyalty_card = models["loyalty.card"].get(1);

        const code_program = models["loyalty.program"].get(9);
        const code_rule = models["loyalty.rule"].get(3);
        const code_reward = models["loyalty.reward"].get(1);

        loyalty_program.reward_ids = [4];
        loyalty_reward.discount_applicability = "specific";
        loyalty_reward.all_discount_product_ids = [8];
        loyalty_reward.discount_max_amount = 100;

        code_program.rule_ids = [3];
        code_program.reward_ids = [1];
        code_rule.valid_product_ids = [];
        code_rule.reward_point_amount = 10;
        code_rule.minimum_qty = 1;
        code_reward.discount_applicability = "specific";
        code_reward.all_discount_product_ids = [8];
        code_reward.discount_line_product_id = 5;

        const partner1 = models["res.partner"].get(1);
        order.setPartner(partner1);
        await store.orderUpdateLoyaltyPrograms();

        await addProductLineToOrder(store, order, {
            productId: 8,
            templateId: 8,
            price_unit: 300,
            qty: 1,
        });

        order._applyReward(loyalty_reward, loyalty_card.id);
        await store.activateCode("EXPIRED");

        expect(order.getOrderlines().length).toBe(3);
        expect(order.lines[1].prices.total_included).toBe(-100);
        expect(order.lines[2].prices.total_included).toBe(-27.5);
    });

    test("_getRewardLineValuesDiscount - gift card payment uses full amount tax-free", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        const product = models["product.product"].get(1);
        await addProductLineToOrder(store, order, { productId: product.id, price_unit: 50 });

        const reward = models["loyalty.reward"].get(4);
        const discountProduct = models["product.product"].get(200);
        discountProduct.taxes_id = [];
        reward.discount_line_product_id = discountProduct;

        const lines = order._getRewardLineValuesDiscount({ reward, coupon_id: 1 });

        expect(lines).toHaveLength(1);
        const [line] = lines;
        expect(line.price_unit).toBe(-50);
        expect(line.tax_ids).toHaveLength(0);
    });

    test("_getRewardLineValuesDiscount - gift card reward keeps full amount when tax is forced exclusive", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        const tax18Excl = models["account.tax"].create({
            name: "18% (forced excl.)",
            amount_type: "percent",
            amount: 18,
            price_include: false,
            price_include_override: "tax_excluded",
        });

        await addProductLineToOrder(store, order, { productId: 1, price_unit: 10 });

        const reward = models["loyalty.reward"].get(5);
        expect(reward.program_id.program_type).toBe("gift_card");
        const giftCard = models["loyalty.card"].get(3);

        const discountProduct = models["product.product"].get(200);
        discountProduct.taxes_id = [tax18Excl];
        reward.discount_line_product_id = discountProduct;

        const lines = order._getRewardLineValuesDiscount({ reward, coupon_id: giftCard.id });

        expect(lines).toHaveLength(1);
        const [line] = lines;
        expect(line.price_unit).toBe(-10);
        expect(line.tax_ids).toHaveLength(1);

        const applied = order._applyReward(reward, giftCard.id);
        expect(applied).toBe(true);

        const rewardLine = order._get_reward_lines()[0];
        expect(rewardLine.prices.total_included).toBe(-10);
    });
});

describe("pos.order - rebuilt client state", () => {
    const activateGiftCard = async (store, order) => {
        onRpc("loyalty.card", "get_loyalty_card_partner_by_code", () => false);
        onRpc("pos.config", "use_coupon_code", () => ({
            successful: true,
            payload: {
                coupon_id: 18,
                program_id: 3,
                partner_id: false,
                points: 92,
                points_display: "92",
                has_source_order: true,
            },
        }));
        const models = store.models;
        deactivateAllProgramsExcept(store, [3]);
        const reward = models["loyalty.reward"].get(5);
        reward.discount_mode = "per_point";
        reward.discount = 1;
        reward.discount_line_product_id = models["product.product"].get(200);
        await addProductLineToOrder(store, order, { productId: 1, price_unit: 92 });
        await store.activateCode("0449-3984-4efe");
        expect(order._get_reward_lines()).toHaveLength(1);
        expect(order._get_reward_lines()[0].coupon_id.id).toBe(18);
        expect(order.priceIncl).toBe(0);
    };

    test("code activated gift card reward survives a page reload", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        await activateGiftCard(store, order);

        // `_code_activated_coupon_ids` is a local field, it is not restored with the order,
        // and setup() flags the rebuilt order with invalidCoupons
        order._code_activated_coupon_ids = [["clear"]];
        order.invalidCoupons = true;
        await store.orderUpdateLoyaltyPrograms();
        order._updateRewardLines();

        expect(order._get_reward_lines()).toHaveLength(1);
        expect(order._get_reward_lines()[0].coupon_id.id).toBe(18);
        expect(order.priceIncl).toBe(0);
        expect(order._code_activated_coupon_ids.map((c) => c.id)).toEqual([18]);
    });

    test("code activated gift card reward survives a reload from the server", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        await activateGiftCard(store, order);

        // neither the local field nor the uiState exist when the order comes from read_pos_orders
        order._code_activated_coupon_ids = [["clear"]];
        order.uiState.couponPointChanges = {};
        order.invalidCoupons = true;
        await store.orderUpdateLoyaltyPrograms();
        order._updateRewardLines();

        expect(order._get_reward_lines()).toHaveLength(1);
        expect(order.priceIncl).toBe(0);
    });

    test("reward line of a nominative card is still dropped when the partner is removed", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();
        deactivateAllProgramsExcept(store, [7]);
        const partner = models["res.partner"].get(1);
        const program = models["loyalty.program"].get(7);
        const reward = models["loyalty.reward"].get(1);
        const card = models["loyalty.card"].get(4);
        program.reward_ids = [1];
        reward.program_id = program;
        reward.required_points = 1;
        reward.discount_line_product_id = models["product.product"].get(5);
        order.setPartner(partner);
        await store.orderUpdateLoyaltyPrograms();
        await addProductLineToOrder(store, order, { productId: 1, price_unit: 10 });
        expect(order._applyReward(reward, card.id)).toBe(true);
        expect(order._get_reward_lines()).toHaveLength(1);

        order.setPartner(false);
        order.invalidCoupons = true;
        await store.orderUpdateLoyaltyPrograms();
        order._updateRewardLines();

        expect(order._get_reward_lines()).toHaveLength(0);
    });
});
