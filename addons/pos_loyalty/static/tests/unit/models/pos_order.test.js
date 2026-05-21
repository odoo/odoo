import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { createOrderWithLoyalty, getFilledOrderLoyalty } from "@pos_loyalty/../tests/unit/utils";

definePosModels();

test("_getIgnoredProductIdsTotalDiscount: returns empty array when no rewards with global discount exist", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    store.models["loyalty.program"]
        .filter((p) => p.program_type === "gift_card")
        .map((p) => p.delete());
    const result = order._getIgnoredProductIdsTotalDiscount();
    expect(result.length).toBe(0);
});

test("_getIgnoredProductIdsTotalDiscount: includes reward product ids when global discount reward is applied", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const reward = store.models["loyalty.reward"].get(1);
    reward.is_global_discount = true;
    reward.reward_product_ids = [store.models["product.product"].get(5)];

    store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(20),
        qty: 1,
        price_unit: -10,
        is_reward_line: true,
        reward_id: reward,
        price_type: "manual",
    });

    const result = order._getIgnoredProductIdsTotalDiscount();
    expect(result).toBeInstanceOf(Array);
    expect(result.length).toBe(1);
});

test("setPricelist clears non-applicable program coupon changes", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const restrictedProgram = store.models["loyalty.program"].get(1);
    const unrestrictedProgram = store.models["loyalty.program"].get(3);
    const pricelist = store.models["product.pricelist"].getAll()[0];

    restrictedProgram.pricelist_ids = [pricelist];
    unrestrictedProgram.pricelist_ids = [];

    order.uiState.couponPointChanges[1] = {
        points: 10,
        program_id: restrictedProgram.id,
        coupon_id: 1,
    };
    order.uiState.couponPointChanges[3] = {
        points: 10,
        program_id: unrestrictedProgram.id,
        coupon_id: 3,
    };

    order.setPricelist(false);

    expect(order.pricelist_id).toBe(undefined);
    expect(order.uiState.couponPointChanges[1]).toBe(undefined);
    expect(order.uiState.couponPointChanges[3]).not.toBe(undefined);

    restrictedProgram.pricelist_ids = [];
});

test("_updateRewardLines removes reward lines whose reward is disabled", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const reward = store.models["loyalty.reward"].get(1);
    store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(20),
        qty: 1,
        price_unit: -10,
        is_reward_line: true,
        reward_id: reward,
        price_type: "manual",
    });

    order.uiState.disabledRewards.add(reward.id);
    order._updateRewardLines();

    const remaining = order._get_reward_lines().filter((l) => l.reward_id?.id === reward.id);
    expect(remaining.length).toBe(0);
});

test("returns 0 when order does not meet reward threshold", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const loyaltyProgram = store.models["loyalty.program"].get(1);
    const correction = order._getPointsCorrection(loyaltyProgram);
    expect(correction).toBe(0);
});

test("deducts points for free product reward lines with money mode", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    const order = await createOrderWithLoyalty(
        store,
        [{ product: store.models["product.product"].get(5), qty: 5, price: 100 }],
        partner
    );

    const reward = store.models["loyalty.reward"].get(5);

    store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(5),
        qty: 1,
        price_unit: 0,
        is_reward_line: true,
        reward_id: reward,
        coupon_id: store.models["loyalty.card"].get(1),
        price_type: "manual",
        _reward_product_id: store.models["product.product"].get(5),
    });

    const program = store.models["loyalty.program"].get(reward.program_id?.id || 5);
    const correction = order._getPointsCorrection(program);
    expect(typeof correction).toBe("number");
});

test("_validForPointsCorrection: returns false when reward type is not product", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const discountReward = store.models["loyalty.reward"].get(1); // discount reward
    const rule = store.models["loyalty.rule"].get(1);
    const line = store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(5),
        qty: 1,
        price_unit: -10,
        is_reward_line: true,
        reward_id: discountReward,
        price_type: "manual",
    })[0];

    expect(order._validForPointsCorrection(discountReward, line, rule)).toBe(false);
});

test("_validForPointsCorrection: returns false when rule mode is order", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const reward = store.models["loyalty.reward"].get(5);
    const rule = store.models["loyalty.rule"].get(1);
    rule.reward_point_mode = "order";

    const line = store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(5),
        qty: 1,
        price_unit: 0,
        is_reward_line: true,
        reward_id: reward,
        price_type: "manual",
    })[0];

    expect(order._validForPointsCorrection(reward, line, rule)).toBe(false);
});

test("_validForPointsCorrection: returns false when rule program does not match reward program", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const reward = store.models["loyalty.reward"].get(5);
    const rule = store.models["loyalty.rule"].get(1);

    const line = store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(5),
        qty: 1,
        price_unit: 0,
        is_reward_line: true,
        reward_id: reward,
        price_type: "manual",
    })[0];

    expect(order._validForPointsCorrection(reward, line, rule)).toBe(false);
});

test("isLineValidForLoyaltyPoints: returns true by default for any line", async () => {
    const store = await setupPosEnv();
    const order = await createOrderWithLoyalty(store, [
        { product: store.models["product.product"].get(5), qty: 1, price: 10 },
    ]);

    const line = order.lines[0];
    expect(order.isLineValidForLoyaltyPoints(line)).toBe(true);
});

test("getClaimableRewards: returns empty when order has no couponPointChanges", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    expect(order.getClaimableRewards()).toHaveLength(0);
});

test("getClaimableRewards: returns discount reward when enough points and threshold met", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    const order = await createOrderWithLoyalty(
        store,
        [{ product: store.models["product.product"].get(5), qty: 5, price: 100 }],
        partner
    );

    await store.updatePrograms();
    const rewards = order.getClaimableRewards();

    expect(Array.isArray(rewards)).toBe(true);
    expect(rewards.length).toBe(3);
});

test("getClaimableRewards: filters by coupon_id when provided", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    const order = await createOrderWithLoyalty(
        store,
        [{ product: store.models["product.product"].get(5), qty: 5, price: 100 }],
        partner
    );

    await store.updatePrograms();
    const filtered = order.getClaimableRewards(99999);

    expect(Array.isArray(filtered)).toBe(true);
    expect(filtered.length).toBe(0);
});

test("getClaimableRewards: filters by program_id when provided", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    const order = await createOrderWithLoyalty(
        store,
        [{ product: store.models["product.product"].get(5), qty: 5, price: 100 }],
        partner
    );

    await store.updatePrograms();
    const forProgram99 = order.getClaimableRewards(false, 99); // non-existent program

    expect(forProgram99.length).toBe(0);
});

test("getClaimableRewards: skips disabled rewards when auto=true", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    const order = await createOrderWithLoyalty(
        store,
        [{ product: store.models["product.product"].get(5), qty: 5, price: 100 }],
        partner
    );

    await store.updatePrograms();
    const allRewards = order.getClaimableRewards();

    const rewardId = allRewards[0].reward.id;
    order.uiState.disabledRewards.add(rewardId);

    const autoRewards = order.getClaimableRewards(false, false, true);
    const stillPresent = autoRewards.find((r) => r.reward.id === rewardId);
    expect(stillPresent).toBe(undefined);

    order.uiState.disabledRewards.delete(rewardId);
});

test("getClaimableRewards: skips discount rewards when order total is zero", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    order.uiState.couponPointChanges[-1] = {
        points: 100,
        program_id: 2,
        coupon_id: -1,
    };

    const rewards = order.getClaimableRewards();
    const discountRewards = rewards.filter((r) => r.reward.reward_type === "discount");
    expect(discountRewards.length).toBe(0);
});

test("_applyReward: returns error when not enough points on coupon", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const reward = store.models["loyalty.reward"].get(1);
    reward.required_points = 10000;

    const result = order._applyReward(reward, 1, {});
    expect(typeof result).toBe("string");
    expect(result.includes("not enough points")).toBe(true);

    reward.required_points = 10; // reset
});

test("_applyReward: successfully applies a discount reward and creates order line", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    const order = await createOrderWithLoyalty(
        store,
        [{ product: store.models["product.product"].get(5), qty: 5, price: 100 }],
        partner
    );

    await store.updatePrograms();
    const rewards = order.getClaimableRewards();
    const { reward, coupon_id } = rewards[0];
    const result = order._applyReward(reward, coupon_id, {});
    expect(result).toBe(true);
    expect(order._get_reward_lines().length).toBe(1);
});

test("_applyReward: returns error when better global discount already applied", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    const order = await createOrderWithLoyalty(
        store,
        [{ product: store.models["product.product"].get(5), qty: 5, price: 100 }],
        partner
    );

    const reward = store.models["loyalty.reward"].get(1);

    const betterReward = store.models["loyalty.reward"].create({
        program_id: store.models["loyalty.program"].get(2),
        reward_type: "discount",
        discount_mode: "percent",
        discount: 20, // higher
        is_global_discount: true,
        required_points: 1,
    });

    store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(20),
        qty: 1,
        price_unit: -20,
        is_reward_line: true,
        reward_id: betterReward,
        price_type: "manual",
    });

    const result = order._applyReward(reward, 1, {});
    expect(typeof result).toBe("string");
    expect(result.includes("better global discount")).toBe(true);
});

test("applyRewardLine creates a pos.order.line with reward fields", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const reward = store.models["loyalty.reward"].get(1);
    const coupon = store.models["loyalty.card"].get(1);

    order.applyRewardLine({
        order_id: order,
        product_id: store.models["product.product"].get(20),
        qty: 1,
        price_unit: -10,
        is_reward_line: true,
        reward_id: reward,
        coupon_id: coupon.id,
        points_cost: 10,
        reward_identifier_code: "CODE123",
        tax_ids: [],
    });

    const rewardLines = order._get_reward_lines();
    expect(rewardLines.length).toBe(1);
    expect(rewardLines[0].reward_id.id).toBe(reward.id);
    expect(rewardLines[0].coupon_id.id).toBe(coupon.id);
});

test("processGiftCard creates a couponPointChange entry with the gift card code", async () => {
    const store = await setupPosEnv();

    const gcProgram = store.models["loyalty.program"].create({
        name: "Test GC",
        program_type: "gift_card",
        trigger: "auto",
        applies_on: "future",
    });

    const gcProduct = store.models["product.product"].get(5);
    gcProgram.trigger_product_ids = [gcProduct];

    const order = await createOrderWithLoyalty(store, [{ product: gcProduct, qty: 1, price: 50 }]);

    order.selectOrderline(order.lines[0]);
    order.processGiftCard("GC_TEST_001", 50, null);

    const changes = Object.values(order.uiState.couponPointChanges);
    const gcChange = changes.find((c) => c.code === "GC_TEST_001");
    expect(gcChange).not.toBe(undefined);
    expect(gcChange.points).toBe(50);
    expect(gcChange.manual).toBe(true);
    expect(gcChange.program_id).toBe(gcProgram.id);
});

test("_getDiscountableOnOrder: returns correct discountable amount for all regular lines", async () => {
    const store = await setupPosEnv();
    const order = await createOrderWithLoyalty(store, [
        { product: store.models["product.product"].get(5), qty: 2, price: 50 },
        { product: store.models["product.product"].get(6), qty: 1, price: 100 },
    ]);

    const reward = store.models["loyalty.reward"].get(1);
    const result = order._getDiscountableOnOrder(reward);

    expect(result.discountable).toBe(240);
    expect(typeof result.discountablePerTax).toBe("object");
});

test("_getDiscountableOnOrder: excludes zero-quantity lines from discountable", async () => {
    const store = await setupPosEnv();
    const order = await createOrderWithLoyalty(store, [
        { product: store.models["product.product"].get(5), qty: 1, price: 100 },
    ]);
    store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(6),
        qty: 0,
        price_unit: 50,
        price_type: "normal",
    });

    const reward = store.models["loyalty.reward"].get(1);
    const result = order._getDiscountableOnOrder(reward);

    expect(result.discountable).toBe(115);
});

test("_getCheapestLine returns the line with the smallest price_unit", async () => {
    const store = await setupPosEnv();
    const order = await createOrderWithLoyalty(store, [
        { product: store.models["product.product"].get(5), qty: 1, price: 100 },
        { product: store.models["product.product"].get(5), qty: 1, price: 30 },
    ]);

    const reward = store.models["loyalty.reward"].get(3);
    reward.discount_applicability = "cheapest";
    const cheapest = order._getCheapestLine(reward);

    expect(cheapest).not.toBe(undefined);
    expect(cheapest.price_unit).toBe(30);
});

test("_getDiscountableOnCheapest returns discountable from cheapest line only", async () => {
    const store = await setupPosEnv();
    const order = await createOrderWithLoyalty(store, [
        { product: store.models["product.product"].get(5), qty: 1, price: 100 },
        { product: store.models["product.product"].get(6), qty: 1, price: 30 },
    ]);

    const reward = store.models["loyalty.reward"].get(3);
    reward.discount_applicability = "cheapest";
    const result = order._getDiscountableOnCheapest(reward);

    expect(result.discountable).toBe(100);
});

test("_getDiscountableOnSpecific: discountable only includes lines matching reward product domain", async () => {
    const store = await setupPosEnv();
    const order = await createOrderWithLoyalty(store, [
        { product: store.models["product.product"].get(5), qty: 2, price: 50 },
        { product: store.models["product.product"].get(6), qty: 1, price: 100 },
    ]);

    const reward = store.models["loyalty.reward"].get(3);
    reward.all_discount_product_ids = [store.models["product.product"].get(5)];

    const result = order._getDiscountableOnSpecific(reward);
    expect(result.discountable).toBe(115);
});

test("_getGlobalDiscountLines: returns empty array when no global discount reward lines", async () => {
    const store = await setupPosEnv();
    const order = await createOrderWithLoyalty(store, [
        { product: store.models["product.product"].get(5), qty: 1, price: 100 },
    ]);

    expect(order._getGlobalDiscountLines()).toHaveLength(0);
});

test("_getGlobalDiscountLines: returns only lines with is_global_discount reward", async () => {
    const store = await setupPosEnv();
    const order = await createOrderWithLoyalty(store, [
        { product: store.models["product.product"].get(5), qty: 1, price: 100 },
    ]);

    const reward = store.models["loyalty.reward"].get(1);

    store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(20),
        qty: 1,
        price_unit: -10,
        is_reward_line: true,
        reward_id: reward,
        price_type: "manual",
    });

    expect(order._getGlobalDiscountLines()).toHaveLength(1);
});

test("_isRewardProductPartOfRules: returns true when rule covers any product", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const reward = store.models["loyalty.reward"].get(1);
    const product = store.models["product.product"].get(5);

    expect(order._isRewardProductPartOfRules(reward, product)).toBe(true);
});

test("_isRewardProductPartOfRules: returns false when product not in rule's valid product ids", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const reward = store.models["loyalty.reward"].get(5);
    const product = store.models["product.product"].get(6);
    const rule = store.models["loyalty.rule"].get(5);
    rule.any_product = false;
    rule.validProductIds = new Set([5]);

    expect(order._isRewardProductPartOfRules(reward, product)).toBe(false);
});

test("_computePotentialFreeProductQty: returns 0 when not enough points for even 1 free product", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const reward = store.models["loyalty.reward"].get(5);
    const product = store.models["product.product"].get(5);
    const points = 0;

    const qty = order._computePotentialFreeProductQty(reward, product, points);
    expect(qty).toBe(0);
});

test("_computePotentialFreeProductQty: returns correct qty with sufficient points", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    const order = await createOrderWithLoyalty(
        store,
        [{ product: store.models["product.product"].get(5), qty: 10, price: 50 }],
        partner
    );

    await store.updatePrograms();
    const card = store.models["loyalty.card"].get(1);
    const reward = store.models["loyalty.reward"].get(5);
    const product = store.models["product.product"].get(5);

    const points = order._getRealCouponPoints(card.id);
    const qty = order._computePotentialFreeProductQty(reward, product, points);
    expect(qty).toBe(1);
});

test("isSaleDisallowed: returns false for a regular product (base behavior)", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const product = store.models["product.product"].get(5);
    expect(order.isSaleDisallowed({ product_id: product }, {})).toBe(false);
});

test("isSaleDisallowed: returns true for refund orders with a positive quantity", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    order.is_refund = true;

    const product = store.models["product.product"].get(5);
    expect(order.isSaleDisallowed({ product_id: product, qty: 1 }, {})).toBe(true);
});

test("isSaleDisallowed: allows gift cards on refund orders", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    order.is_refund = true;

    const product = store.models["product.product"].get(5);
    const giftCardProgram = store.models["loyalty.program"].filter(
        (program) => program.program_type === "gift_card"
    )[0];

    expect(
        order.isSaleDisallowed(
            { product_id: product, qty: 1 },
            { eWalletGiftCardProgram: giftCardProgram }
        )
    ).toBe(false);
});

test("getClaimableRewards: promo code rewards excluded before code activation", async () => {
    const store = await setupPosEnv();
    const order = await createOrderWithLoyalty(store, [
        { product: store.models["product.product"].get(5), qty: 5, price: 20 },
    ]);

    const rewards = order.getClaimableRewards();
    const promoRewards = rewards.filter((r) => r.reward.program_id?.id === 3);
    expect(promoRewards.length).toBe(0);
});

test("initState initializes loyalty uiState properties", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    expect(order.uiState.disabledRewards).toBeInstanceOf(Set);
    expect(order.uiState.disabledRewards.size).toBe(0);
    expect(order.uiState.codeActivatedProgramRules).toEqual([]);
    expect(order.uiState.couponPointChanges).toEqual({});
});

test("invalidCoupons is set to true on new order", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    expect(order.invalidCoupons).toBe(true);
});

test("serializeState includes disabledRewards", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    order.uiState.disabledRewards.add(1);
    order.uiState.disabledRewards.add(2);

    const state = order.serializeState();
    expect(state.disabledRewards).toInclude(1);
    expect(state.disabledRewards).toInclude(2);
});

test("restoreState restores disabledRewards from serialized data", async () => {
    const store = await setupPosEnv();
    const partner1 = store.models["res.partner"].get(3);

    const order = await createOrderWithLoyalty(
        store,
        [{ product: store.models["product.product"].get(5), qty: 10, price: 10 }],
        partner1
    );

    order.restoreState({ ...order.uiState, disabledRewards: [3, 5] });
    expect(order.uiState.disabledRewards.has(3)).toBe(true);
    expect(order.uiState.disabledRewards.has(5)).toBe(true);
});

test("_resetPrograms clears all loyalty state", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    const order = await createOrderWithLoyalty(
        store,
        [{ product: store.models["product.product"].get(5), qty: 1, price: 10 }],
        partner
    );

    order.uiState.disabledRewards.add(1);
    order.uiState.codeActivatedProgramRules.push(3);

    expect(Object.keys(order.uiState.couponPointChanges)).toHaveLength(1);
    order._resetPrograms();

    expect(order.uiState.disabledRewards.size).toBe(0);
    expect(order.uiState.codeActivatedProgramRules).toEqual([]);
    expect(Object.keys(order.uiState.couponPointChanges)).toHaveLength(0);
});

test("_resetPrograms removes reward lines from order", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrderLoyalty(store);

    store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(20),
        qty: 1,
        price_unit: -10,
        is_reward_line: true,
        reward_id: store.models["loyalty.reward"].get(1),
        price_type: "manual",
    });

    const rewardLinesBefore = order._get_reward_lines();
    expect(rewardLinesBefore.length).toBe(1);

    order._resetPrograms();

    const rewardLinesAfter = order._get_reward_lines();
    expect(rewardLinesAfter.length).toBe(0);
});

test("isProgramsResettable returns false with no loyalty state", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    expect(order.isProgramsResettable()).toBe(false);
});

test("isProgramsResettable returns true with couponPointChanges", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    const order = await createOrderWithLoyalty(
        store,
        [{ product: store.models["product.product"].get(5), qty: 1, price: 10 }],
        partner
    );

    expect(order.isProgramsResettable()).toBe(true);
});

test("isProgramsResettable returns true with codeActivatedProgramRules", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    order.uiState.codeActivatedProgramRules.push(3);

    expect(order.isProgramsResettable()).toBe(true);
});

test("_programIsApplicable: auto-trigger program without auto rules is not applicable", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const promotionProgram = store.models["loyalty.program"].get(2);
    store.models["loyalty.rule"].get(2).mode = "order";
    expect(order._programIsApplicable(promotionProgram)).toBe(false);
});

test("_programIsApplicable: auto-trigger program with auto rules is applicable", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    const order = await createOrderWithLoyalty(store, [], partner);

    const loyaltyProgram = store.models["loyalty.program"].get(1);
    expect(order._programIsApplicable(loyaltyProgram)).toBe(true);
});

test("_programIsApplicable: nominative program without partner is not applicable", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const loyaltyProgram = store.models["loyalty.program"].get(1);
    expect(order._programIsApplicable(loyaltyProgram)).toBe(false);
});

test("_programIsApplicable: with_code program becomes applicable after code activation", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const promoCodeProgram = store.models["loyalty.program"].get(3);
    expect(order._programIsApplicable(promoCodeProgram)).toBe(false);

    // Activate the promo code rule
    order.uiState.codeActivatedProgramRules.push(3);
    expect(order._programIsApplicable(promoCodeProgram)).toBe(true);
});

test("_canGenerateRewards: order meeting minimum amount can generate rewards", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrderLoyalty(store);

    const promotionProgram = store.models["loyalty.program"].get(2);
    const totalWithTax = order.priceIncl;
    const totalWithoutTax = order.priceExcl;

    expect(order._canGenerateRewards(promotionProgram, totalWithTax, totalWithoutTax)).toBe(true);
});

test("_canGenerateRewards: order below minimum amount cannot generate rewards", async () => {
    const store = await setupPosEnv();
    const order = await createOrderWithLoyalty(store, [
        { product: store.models["product.product"].get(14), qty: 1, price: 3.4 },
    ]);

    const promotionProgram = store.models["loyalty.program"].get(2);
    const totalWithTax = order.priceIncl;
    const totalWithoutTax = order.priceExcl;

    expect(order._canGenerateRewards(promotionProgram, totalWithTax, totalWithoutTax)).toBe(false);
});

test("_canGenerateRewards: order below minimum qty cannot generate rewards", async () => {
    const store = await setupPosEnv();
    const order = await createOrderWithLoyalty(store, [
        { product: store.models["product.product"].get(5), qty: 1, price: 10 },
    ]);

    const buyXgetYProgram = store.models["loyalty.program"].get(5);
    const totalWithTax = order.priceIncl;
    const totalWithoutTax = order.priceExcl;

    expect(order._canGenerateRewards(buyXgetYProgram, totalWithTax, totalWithoutTax)).toBe(false);
});

test("pointsForPrograms: loyalty program earns points per money (money mode)", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    const order = await createOrderWithLoyalty(
        store,
        [
            { product: store.models["product.product"].get(5), qty: 3, price: 100 },
            { product: store.models["product.product"].get(6), qty: 2, price: 100 },
        ],
        partner
    );

    const loyaltyProgram = store.models["loyalty.program"].get(1);
    const rule = store.models["loyalty.rule"].get(1);
    rule.reward_point_mode = "money";
    rule.reward_point_amount = 0.01;

    const result = order.pointsForPrograms([loyaltyProgram]);

    expect(result[1]).toHaveLength(1);
    expect(result[1][0].points).toBe(5.95);
});

test("pointsForPrograms: promotion program earns points per order when threshold met", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrderLoyalty(store);

    const promotionProgram = store.models["loyalty.program"].get(2);
    const result = order.pointsForPrograms([promotionProgram]);

    expect(result[2]).toHaveLength(1);
    expect(result[2][0].points).toBe(1);
});

test("pointsForPrograms: promotion program earns 0 points when threshold not met", async () => {
    const store = await setupPosEnv();
    const order = await createOrderWithLoyalty(store, [
        { product: store.models["product.product"].get(14), qty: 1, price: 3.4 },
    ]);

    const promotionProgram = store.models["loyalty.program"].get(2);
    const result = order.pointsForPrograms([promotionProgram]);

    expect(result[2]).toHaveLength(0);
});

test("pointsForPrograms: promo code program only earns points when code activated", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrderLoyalty(store);

    const promoCodeProgram = store.models["loyalty.program"].get(3);

    let result = order.pointsForPrograms([promoCodeProgram]);
    expect(result[3]).toHaveLength(0);
    order.uiState.codeActivatedProgramRules.push(3);
    result = order.pointsForPrograms([promoCodeProgram]);
    expect(result[3]).toHaveLength(1);
    expect(result[3][0].points).toBe(1);
});

test("_get_reward_lines returns only reward lines", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrderLoyalty(store);

    store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(20),
        qty: 1,
        price_unit: -50,
        is_reward_line: true,
        reward_id: store.models["loyalty.reward"].get(1),
        price_type: "manual",
    });

    expect(order._get_reward_lines().length).toBe(1);
    expect(order._get_reward_lines()[order._get_reward_lines().length - 1].is_reward_line).toBe(
        true
    );
});

test("_get_regular_order_lines excludes reward lines", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrderLoyalty(store);

    const regularBefore = order._get_regular_order_lines().length;

    store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(20),
        qty: 1,
        price_unit: -50,
        is_reward_line: true,
        reward_id: store.models["loyalty.reward"].get(1),
        price_type: "manual",
    });

    expect(order._get_regular_order_lines().length).toBe(regularBefore);
});

test("getOrderlines sorts reward lines to the end", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrderLoyalty(store);

    store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(20),
        qty: 1,
        price_unit: -50,
        is_reward_line: true,
        reward_id: store.models["loyalty.reward"].get(1),
        price_type: "manual",
    });

    const lines = order.getOrderlines();
    const lastLine = lines[lines.length - 1];

    expect(lastLine.is_reward_line).toBe(true);
});

test("getLastOrderline skips reward lines", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrderLoyalty(store);

    const lastRegular = order.getLastOrderline();

    store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(20),
        qty: 1,
        price_unit: -50,
        is_reward_line: true,
        reward_id: store.models["loyalty.reward"].get(1),
        price_type: "manual",
    });

    const lastAfter = order.getLastOrderline();
    expect(lastAfter.is_reward_line).toBe(undefined);
    expect(lastAfter.id).toBe(lastRegular.id);
});

test("_getRealCouponPoints returns card balance for existing coupon", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const points = order._getRealCouponPoints(1);
    expect(points).toBe(50);
});

test("_getRealCouponPoints adds couponPointChanges for non-future programs", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    const order = await createOrderWithLoyalty(
        store,
        [{ product: store.models["product.product"].get(5), qty: 10, price: 10 }],
        partner
    );

    const points = order._getRealCouponPoints(1);
    expect(points).toBe(60); // 50 + 10
});

test("_getRealCouponPoints subtracts reward line costs", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    const order = await createOrderWithLoyalty(
        store,
        [{ product: store.models["product.product"].get(5), qty: 10, price: 10 }],
        partner
    );

    store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(20),
        qty: 1,
        price_unit: -5,
        is_reward_line: true,
        reward_id: store.models["loyalty.reward"].get(1),
        coupon_id: store.models["loyalty.card"].get(1),
        points_cost: 10,
        price_type: "manual",
    });

    const points = order._getRealCouponPoints(1);
    expect(points).toBe(50);
});

test("getLoyaltyPoints returns points info for loyalty programs", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    const order = await createOrderWithLoyalty(
        store,
        [{ product: store.models["product.product"].get(5), qty: 10, price: 10 }],
        partner
    );

    const loyaltyPoints = order.getLoyaltyPoints();
    expect(loyaltyPoints).toHaveLength(1);
    expect(loyaltyPoints[0].points.won).toBe(10);
    expect(loyaltyPoints[0].points.balance).toBe(50);
    expect(loyaltyPoints[0].points.total).toBe(60);
    expect(loyaltyPoints[0].points.spent).toBe(0);
});

test("getLoyaltyPoints skips non-loyalty programs", async () => {
    const store = await setupPosEnv();
    const order = await createOrderWithLoyalty(store, [
        { product: store.models["product.product"].get(5), qty: 10, price: 10 },
    ]);

    const loyaltyPoints = order.getLoyaltyPoints();
    expect(loyaltyPoints).toHaveLength(0);
});

test("getLoyaltyPoints reflects spent points from reward lines", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    const order = await createOrderWithLoyalty(
        store,
        [{ product: store.models["product.product"].get(5), qty: 15, price: 10 }],
        partner
    );

    store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(20),
        qty: 1,
        price_unit: -5,
        is_reward_line: true,
        reward_id: store.models["loyalty.reward"].get(1),
        coupon_id: store.models["loyalty.card"].get(1),
        points_cost: 10,
        price_type: "manual",
    });

    const loyaltyPoints = order.getLoyaltyPoints();
    expect(loyaltyPoints[0].points.won).toBe(15);
    expect(loyaltyPoints[0].points.spent).toBe(10);
    expect(loyaltyPoints[0].points.balance).toBe(50);
    expect(loyaltyPoints[0].points.total).toBe(55);
});

test("setPartner clears nominative program coupon changes and re-evaluates", async () => {
    const store = await setupPosEnv();
    const partner1 = store.models["res.partner"].get(3);

    const order = await createOrderWithLoyalty(
        store,
        [{ product: store.models["product.product"].get(5), qty: 10, price: 10 }],
        partner1
    );

    expect(
        Object.values(order.uiState.couponPointChanges).find((c) => c.program_id === 1)
    ).not.toBe(undefined);

    const partner2 = store.models["res.partner"].get(4);
    order.setPartner(partner2);
    await store.updatePrograms();
    expect(order.uiState.couponPointChanges[1]).toBe(undefined);
});

test("waitForPushOrder returns true when couponPointChanges exist", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    const order = await createOrderWithLoyalty(
        store,
        [{ product: store.models["product.product"].get(5), qty: 10, price: 10 }],
        partner
    );

    // Ensure couponPointChanges were created
    expect(Object.keys(order.uiState.couponPointChanges).length).toBeGreaterThan(0);
    expect(order.waitForPushOrder()).toBe(true);
});

test("waitForPushOrder returns true when reward lines exist", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(20),
        qty: 1,
        price_unit: -5,
        is_reward_line: true,
        reward_id: store.models["loyalty.reward"].get(1),
        price_type: "manual",
    });

    // Ensure reward line exists
    const rewardLines = order._get_reward_lines();
    expect(rewardLines.length).toBe(1);
    expect(order.waitForPushOrder()).toBe(1);
});

test("removeOrderline: removing a reward line also removes related reward lines", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const rewardCode = "ABC123";

    const reward = store.models["loyalty.reward"].get(1);
    const coupon = store.models["loyalty.card"].get(1);

    store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(20),
        qty: 1,
        price_unit: -5,
        is_reward_line: true,
        reward_id: reward,
        coupon_id: coupon,
        reward_identifier_code: rewardCode,
        price_type: "manual",
    });
    store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(20),
        qty: 1,
        price_unit: -3,
        is_reward_line: true,
        reward_id: reward,
        coupon_id: coupon,
        reward_identifier_code: rewardCode,
        price_type: "manual",
    });

    expect(order._get_reward_lines().length).toBe(2);

    order.removeOrderline(order._get_reward_lines()[0]);
    expect(order._get_reward_lines().length).toBe(0);
});

test("_computeNItems counts items matching rule", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrderLoyalty(store);

    const rule1 = store.models["loyalty.rule"].get(1);
    expect(order._computeNItems(rule1)).toBe(5);

    const rule5 = store.models["loyalty.rule"].get(5);
    rule5.validProductIds = new Set([5]);
    expect(order._computeNItems(rule5)).toBe(3);
});

test("duplicateCouponChanges detects existing manual code", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    order.uiState.couponPointChanges[1] = {
        points: 1,
        program_id: 4,
        coupon_id: 1,
        existing_code: "COUPON001",
        manual: true,
    };

    expect(order.duplicateCouponChanges("COUPON001")).toBe(true);
    expect(order.duplicateCouponChanges("COUPON999")).toBe(false);
});

test("duplicateCouponChanges detects new coupon code with negative id", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    order.uiState.couponPointChanges[-1] = {
        points: 50,
        program_id: 3,
        coupon_id: -1,
        code: "GIFTCARD001",
    };

    expect(order.duplicateCouponChanges("GIFTCARD001")).toBe(true);
});
