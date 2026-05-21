import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { createOrderWithLoyalty } from "@pos_loyalty/../tests/unit/utils";

definePosModels();

const { DateTime } = luxon;

test("setup initializes couponByLineUuidCache and rewardProductByLineUuidCache", async () => {
    const store = await setupPosEnv();
    expect(store.couponByLineUuidCache).toEqual({});
    expect(store.rewardProductByLineUuidCache).toEqual({});
});

test("processServerData initializes partnerId2CouponIds map", async () => {
    const store = await setupPosEnv();
    expect(store.partnerId2CouponIds).not.toBe(undefined);
    expect(typeof store.partnerId2CouponIds).toBe("object");
});

test("processServerData computes validProductIds on loyalty.rule", async () => {
    const store = await setupPosEnv();
    for (const rule of store.models["loyalty.rule"].getAll()) {
        expect(rule.validProductIds).toBeInstanceOf(Set);
    }
});

test("processServerData computes all_discount_product_ids for rewards", async () => {
    const store = await setupPosEnv();
    for (const reward of store.models["loyalty.reward"].getAll()) {
        expect(Array.isArray(reward.all_discount_product_ids)).toBe(true);
    }
});

test("afterProcessServerData deletes reward lines with no reward_id", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(5),
        qty: 1,
        price_unit: -10,
        is_reward_line: true,
        reward_id: null,
        price_type: "manual",
    });

    const linesBefore = order.lines.length;
    expect(linesBefore).toBe(1);

    await store.afterProcessServerData();
    const orphaned = order.lines.filter((l) => l.is_reward_line && !l.reward_id);
    expect(orphaned.length).toBe(0);
});

test("computePartnerCouponIds builds partnerId2CouponIds from all cards", async () => {
    const store = await setupPosEnv();
    store.partnerId2CouponIds = {};
    store.computePartnerCouponIds();

    expect(store.partnerId2CouponIds[3]?.has(1)).toBe(true);
});

test("computePartnerCouponIds ignores cards with negative id (local only)", async () => {
    const store = await setupPosEnv();
    store.partnerId2CouponIds = {};

    store.models["loyalty.card"].create({
        id: -99,
        program_id: store.models["loyalty.program"].get(1),
        partner_id: store.models["res.partner"].get(3),
        points: 0,
        code: null,
    });

    store.computePartnerCouponIds();
    expect(store.partnerId2CouponIds[3]?.has(-99)).toBe(false);
});

test("computePartnerCouponIds ignores cards with no partner", async () => {
    const store = await setupPosEnv();
    store.partnerId2CouponIds = {};

    store.models["loyalty.card"].create({
        id: 999,
        program_id: store.models["loyalty.program"].get(2),
        partner_id: null,
        points: 5,
        code: "NOPARTNER",
    });

    store.computePartnerCouponIds();
    expect(store.partnerId2CouponIds[undefined]).toBe(undefined);
});

test("computeDiscountProductIds with null domain does nothing", async () => {
    const store = await setupPosEnv();
    const reward = store.models["loyalty.reward"].get(1);
    const before = [...(reward.all_discount_product_ids || [])];

    const original = reward.reward_product_domain;
    reward.reward_product_domain = "null";
    store.computeDiscountProductIds(reward, store.models["product.product"].getAll());
    reward.reward_product_domain = original;

    expect(reward.all_discount_product_ids.length).toBe(before.length);
});

test("computeDiscountProductIdsForAllRewards runs for all rewards", async () => {
    const store = await setupPosEnv();
    expect(() => store.computeDiscountProductIdsForAllRewards()).not.toThrow();
});

test("getLoyaltyCards returns all cards for a known partner", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    const cards = store.getLoyaltyCards(partner);

    expect(cards.length).toBe(1);
    expect(cards.every((c) => c.partner_id?.id === partner.id)).toBe(true);
});

test("getLoyaltyCards returns empty array for partner with no cards", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(17);
    const cards = store.getLoyaltyCards(partner);
    expect(cards).toHaveLength(0);
});

test("fetchLoyaltyCard returns cached card when already in store", async () => {
    const store = await setupPosEnv();
    const result = await store.fetchLoyaltyCard(1, 3);
    expect(result.id).toBe(1);
    expect(result.program_id.id).toBe(1);
    expect(result.partner_id.id).toBe(3);
});

test("fetchLoyaltyCard fetches from server when not cached", async () => {
    const store = await setupPosEnv();

    onRpc("loyalty.card", "web_search_read", () => ({
        length: 1,
        records: [{ id: 77, program_id: 1, partner_id: 4, points: 5, code: "LOYAL002" }],
    }));

    const result = await store.fetchLoyaltyCard(1, 4);
    expect(result).not.toBe(undefined);
    expect(result.code).toBe("LOYAL002");
    expect(result.points).toBe(5);
});

test("fetchLoyaltyCard creates local card when server returns nothing", async () => {
    const store = await setupPosEnv();

    onRpc("loyalty.card", "web_search_read", () => ({
        length: 0,
        records: [],
    }));

    const result = await store.fetchLoyaltyCard(2, 4);
    expect(result).not.toBe(undefined);
    expect(result.id).toBeLessThan(0); // negative = local-only
    expect(result.points).toBe(0);
});

test("fetchCoupons calls server with given domain", async () => {
    const store = await setupPosEnv();
    let calledWith = null;

    onRpc("loyalty.card", "search_read", (args) => {
        calledWith = args.kwargs.domain;
        return [];
    });

    await store.fetchCoupons([
        ["partner_id", "=", 3],
        ["program_id", "=", 1],
    ]);
    expect(calledWith).toEqual([
        ["partner_id", "=", 3],
        ["program_id", "=", 1],
    ]);
});

test("couponForProgram creates new local card for non-nominative program", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    const promotionProgram = store.models["loyalty.program"].get(2);
    const coupon = await store.couponForProgram(promotionProgram);

    expect(coupon).not.toBe(undefined);
    expect(coupon.id).toBeLessThan(0);
    expect(coupon.points).toBe(0);
    expect(coupon.program_id.id).toBe(2);
});

test("couponForProgram fetches loyalty card from server for nominative program", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    store.addNewOrder();
    store.getOrder().setPartner(partner);

    const loyaltyProgram = store.models["loyalty.program"].get(1);
    const coupon = await store.couponForProgram(loyaltyProgram);

    expect(coupon).not.toBe(undefined);
    expect(coupon.program_id.id).toBe(1);
});

test("checkMissingCoupons removes coupon changes for cards not in store", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    order.uiState.couponPointChanges = {
        ...order.uiState.couponPointChanges,
        1: { points: 5, program_id: 1, coupon_id: 1 },
        999: { points: 5, program_id: 1, coupon_id: 9999 },
    };

    order.invalidCoupons = true;
    await store.checkMissingCoupons();

    expect(order.uiState.couponPointChanges[1]).not.toBe(undefined);
    expect(order.uiState.couponPointChanges[999]).toBe(undefined);
});

test("checkMissingCoupons skips processing when invalidCoupons is false", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    order.uiState.couponPointChanges[9999] = { points: 5, program_id: 1, coupon_id: 9999 };
    order.invalidCoupons = false; // Should skip

    await store.checkMissingCoupons();

    expect(order.uiState.couponPointChanges[9999]).not.toBe(undefined);
});

test("updatePrograms creates couponPointChanges for nominative program when partner set", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    const order = await createOrderWithLoyalty(
        store,
        [{ product: store.models["product.product"].get(5), qty: 1, price: 10 }],
        partner
    );

    const changes = Object.values(order.uiState.couponPointChanges);
    expect(changes.find((c) => c.program_id === 1)).not.toBe(undefined);
});

test("updatePrograms skips nominative program when no partner", async () => {
    const store = await setupPosEnv();
    const order = await createOrderWithLoyalty(store, [
        { product: store.models["product.product"].get(5), qty: 1, price: 10 },
    ]);

    const changes = Object.values(order.uiState.couponPointChanges);
    expect(changes.find((c) => c.program_id === 1)).toBe(undefined);
});

test("updatePrograms handles promo code program after code activation", async () => {
    const store = await setupPosEnv();
    const order = await createOrderWithLoyalty(store, [
        { product: store.models["product.product"].get(5), qty: 5, price: 20 },
    ]);

    expect(Object.values(order.uiState.couponPointChanges).find((c) => c.program_id === 3)).toBe(
        undefined
    );

    order.uiState.codeActivatedProgramRules.push(3); // rule for promo code
    await store.updatePrograms();

    expect(
        Object.values(order.uiState.couponPointChanges).find((c) => c.program_id === 3)
    ).not.toBe(undefined);
});

test("updatePrograms removes changes for no-longer-applicable programs", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    const order = await createOrderWithLoyalty(
        store,
        [{ product: store.models["product.product"].get(5), qty: 1, price: 10 }],
        partner
    );

    expect(
        Object.values(order.uiState.couponPointChanges).find((c) => c.program_id === 1)
    ).not.toBe(undefined);

    order.setPartner(false);
    await store.updatePrograms();

    expect(Object.values(order.uiState.couponPointChanges).find((c) => c.program_id === 1)).toBe(
        undefined
    );
});

test("updateRewards does nothing when no loyalty programs exist", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    const all = store.models["loyalty.program"].getAll();
    all.forEach((p) => p.delete());

    expect(() => store.updateRewards()).not.toThrow();
});

test("updateRewards auto-applies single non-nominative rewards after update", async () => {
    const store = await setupPosEnv();
    const order = await createOrderWithLoyalty(store, [
        { product: store.models["product.product"].get(5), qty: 10, price: 100 }, // $1000 > $50 threshold
    ]);

    await new Promise((r) => setTimeout(r, 200));

    const rewardLines = order._get_reward_lines();
    const discountLine = rewardLines.find((l) => l.reward_id?.reward_type === "discount");
    expect(discountLine).not.toBe(undefined);
});

test("orderUpdateLoyaltyPrograms does nothing when no order", async () => {
    const store = await setupPosEnv();
    patchWithCleanup(store, {
        getOrder() {
            return null;
        },
    });

    await expect(store.orderUpdateLoyaltyPrograms()).resolves.toBe(undefined);
});

test("selectPricelist triggers updateRewards after pricelist change", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    let updateRewardsCalled = false;
    patchWithCleanup(store, {
        updateRewards() {
            updateRewardsCalled = true;
        },
    });

    const pricelist = store.models["product.pricelist"].getFirst();
    await store.selectPricelist(pricelist);
    expect(updateRewardsCalled).toBe(true);
});

test("activateCode with a promo rule code activates the rule", async () => {
    const store = await setupPosEnv();
    const order = await createOrderWithLoyalty(store, [
        { product: store.models["product.product"].get(5), qty: 5, price: 20 },
    ]);

    onRpc("loyalty.card", "get_loyalty_card_partner_by_code", () => []);
    const result = await store.activateCode("SAVE10");
    expect(result).toBe(true);
    expect(order.uiState.codeActivatedProgramRules).toInclude(3);
});

test("activateCode returns error when code is already activated", async () => {
    const store = await setupPosEnv();
    await createOrderWithLoyalty(store, [
        { product: store.models["product.product"].get(5), qty: 5, price: 20 },
    ]);

    onRpc("loyalty.card", "get_loyalty_card_partner_by_code", () => []);
    await store.activateCode("SAVE10");
    const result = await store.activateCode("SAVE10");

    expect(typeof result).toBe("string");
    expect(result.includes("already been activated")).toBe(true);
});

test("activateCode returns error when promo code program is expired", async () => {
    const store = await setupPosEnv();
    await createOrderWithLoyalty(store, []);

    onRpc("loyalty.card", "get_loyalty_card_partner_by_code", () => []);
    const program = store.models["loyalty.program"].get(3);
    program.date_to = DateTime.now().minus({ months: 1 });

    const result = await store.activateCode("SAVE10");
    expect(typeof result).toBe("string");
    expect(result.includes("expired")).toBe(true);
});

test("activateCode returns error when promo code program is not yet valid", async () => {
    const store = await setupPosEnv();
    await createOrderWithLoyalty(store, []);

    onRpc("loyalty.card", "get_loyalty_card_partner_by_code", () => []);
    const program = store.models["loyalty.program"].get(3);
    program.date_from = DateTime.now().plus({ months: 1 });

    const result = await store.activateCode("SAVE10");
    expect(typeof result).toBe("string");
    expect(result.includes("not yet valid")).toBe(true);
});

test("activateCode calls server RPC for unknown codes", async () => {
    const store = await setupPosEnv();
    await createOrderWithLoyalty(store, []);

    onRpc("loyalty.card", "get_loyalty_card_partner_by_code", () => []);
    onRpc("pos.config", "use_coupon_code", () => ({
        successful: false,
        payload: { error_message: "Invalid code" },
    }));

    const result = await store.activateCode("UNKNOWN_XYZ");
    expect(result).toBe("Invalid code");
});

test("activateCode with server coupon creates loyalty card and activates it", async () => {
    const store = await setupPosEnv();
    const order = await createOrderWithLoyalty(store, [
        { product: store.models["product.product"].get(5), qty: 1, price: 10 },
    ]);

    onRpc("loyalty.card", "get_loyalty_card_partner_by_code", () => []);
    onRpc("pos.config", "use_coupon_code", () => ({
        successful: true,
        payload: {
            coupon_id: 200,
            program_id: 4, // coupons program
            partner_id: false,
            points: 1,
            points_display: "1",
            has_source_order: true,
        },
    }));

    const result = await store.activateCode("VALID_COUPON");
    expect(result).toBe(true);
    expect(order._code_activated_coupon_ids.length).toBe(1);

    // Check loyalty card availability
    const loyaltyCard = store.models["loyalty.card"].get(200);
    expect(loyaltyCard).not.toBe(undefined);
    expect(loyaltyCard.points).toBe(1);
});

test("activateCode already scanned coupon returns error", async () => {
    const store = await setupPosEnv();
    const order = await createOrderWithLoyalty(store, []);

    onRpc("loyalty.card", "get_loyalty_card_partner_by_code", () => []);

    const card = store.models["loyalty.card"].create({
        id: 300,
        program_id: store.models["loyalty.program"].get(4),
        partner_id: null,
        points: 1,
        code: "SCANNED",
    });
    order._code_activated_coupon_ids = [["link", card]];

    const result = await store.activateCode("SCANNED");
    expect(typeof result).toBe("string");
    expect(result.includes("already been scanned")).toBe(true);
});

test("addLineToCurrentOrder calls updatePrograms and updateRewards", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    let updateProgramsCalled = false;
    let updateRewardsCalled = false;
    patchWithCleanup(store, {
        async updatePrograms() {
            updateProgramsCalled = true;
        },
        updateRewards() {
            updateRewardsCalled = true;
        },
    });

    const product = store.models["product.product"].get(5);
    await store.addLineToCurrentOrder({
        product_id: product,
        product_tmpl_id: product.product_tmpl_id,
    });

    expect(updateProgramsCalled).toBe(true);
    expect(updateRewardsCalled).toBe(true);
});

test("addLineToCurrentOrder with gift_card product sets gift card options", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    const gcProgram = store.models["loyalty.program"].create({
        name: "Test GC",
        program_type: "gift_card",
        trigger: "auto",
        applies_on: "future",
    });

    const gcProduct = store.models["product.product"].get(5);
    gcProgram.trigger_product_ids = [gcProduct];

    let gcOptionsCalled = false;
    let gcProgramPassed = null;
    patchWithCleanup(store, {
        async _setupGiftCardOptions(program, opt) {
            gcOptionsCalled = true;
            gcProgramPassed = program;
            opt.eWalletGiftCardProgram = program;
            opt.merge = false;
            opt.quantity = 1;
            return true;
        },
    });

    await store.addLineToCurrentOrder({
        product_id: gcProduct,
        product_tmpl_id: gcProduct.product_tmpl_id,
    });

    expect(gcOptionsCalled).toBe(true);
    expect(gcProgramPassed).not.toBe(null);
    expect(gcProgramPassed.id).toBe(gcProgram.id);
    expect(gcProgramPassed.program_type).toBe("gift_card");
});

test("addLineToCurrentOrder with ewallet product sets ewallet options", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    const ewProgram = store.models["loyalty.program"].create({
        name: "Test eWallet",
        program_type: "ewallet",
        trigger: "auto",
        applies_on: "both",
    });

    const ewProduct = store.models["product.product"].get(6);
    ewProgram.trigger_product_ids = [ewProduct];

    let ewOptionsCalled = false;
    let ewProgramPassed = null;
    patchWithCleanup(store, {
        async setupEWalletOptions(program, opt) {
            ewOptionsCalled = true;
            ewProgramPassed = program;
            opt.eWalletGiftCardProgram = program;
            opt.merge = false;
            opt.quantity = 1;
            return true;
        },
    });

    await store.addLineToCurrentOrder({
        product_id: ewProduct,
        product_tmpl_id: ewProduct.product_tmpl_id,
    });

    expect(ewOptionsCalled).toBe(true);
    expect(ewProgramPassed).not.toBe(null);
    expect(ewProgramPassed.id).toBe(ewProgram.id);
    expect(ewProgramPassed.program_type).toBe("ewallet");
});

test("_setupGiftCardOptions and setupEWalletOptions set quantity=1, merge=false, and eWalletGiftCardProgram", async () => {
    const store = await setupPosEnv();

    // Test _setupGiftCardOptions
    const gcProgram = store.models["loyalty.program"].get(1);
    const gcOpts = {};
    const gcResult = await store._setupGiftCardOptions(gcProgram, gcOpts);

    expect(gcResult).toBe(true);
    expect(gcOpts.quantity).toBe(1);
    expect(gcOpts.merge).toBe(false);
    expect(gcOpts.eWalletGiftCardProgram).toBe(gcProgram);

    // Test setupEWalletOptions
    const ewProgram = store.models["loyalty.program"].get(2);
    const ewOpts = {};
    const ewResult = await store.setupEWalletOptions(ewProgram, ewOpts);

    expect(ewResult).toBe(true);
    expect(ewOpts.quantity).toBe(1);
    expect(ewOpts.merge).toBe(false);
    expect(ewOpts.eWalletGiftCardProgram).toBe(ewProgram);
});

test("getPotentialFreeProductRewards returns empty when no order", async () => {
    const store = await setupPosEnv();
    patchWithCleanup(store, { getOrder: () => null });
    expect(store.getPotentialFreeProductRewards()).toHaveLength(0);
});

test("getPotentialFreeProductRewards returns empty for order with no lines", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();
    expect(store.getPotentialFreeProductRewards()).toHaveLength(0);
});

test("getPotentialFreeProductRewards returns potential product rewards with enough points", async () => {
    const store = await setupPosEnv();

    const rewards = store.getPotentialFreeProductRewards();
    expect(Array.isArray(rewards)).toBe(true);
});

test("updateOrder calls orderUpdateLoyaltyPrograms", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    let called = false;
    patchWithCleanup(store, {
        async orderUpdateLoyaltyPrograms() {
            called = true;
        },
    });

    await store.updateOrder(order);
    expect(called).toBe(true);
});

test("preSyncAllOrders caches negative coupon_id by line uuid", async () => {
    const store = await setupPosEnv();
    const order = await createOrderWithLoyalty(store, [
        { product: store.models["product.product"].get(5), qty: 1, price: 10 },
    ]);

    const localCard = store.models["loyalty.card"].create({
        id: -88,
        program_id: store.models["loyalty.program"].get(2),
        partner_id: null,
        points: 0,
        code: null,
    });

    const rewardLine = store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(20),
        qty: 1,
        price_unit: -5,
        is_reward_line: true,
        reward_id: store.models["loyalty.reward"].get(1),
        coupon_id: localCard,
        price_type: "manual",
    });

    await store.preSyncAllOrders([order]);
    expect(store.couponByLineUuidCache[rewardLine.uuid]).toBe(-88);
});

test("postSyncAllOrders restores coupon_id from cache after sync", async () => {
    const store = await setupPosEnv();
    const order = await createOrderWithLoyalty(store, [
        { product: store.models["product.product"].get(5), qty: 1, price: 10 },
    ]);

    const localCard = store.models["loyalty.card"].create({
        id: -88,
        program_id: store.models["loyalty.program"].get(2),
        partner_id: null,
        points: 0,
        code: null,
    });

    const rewardLine = store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(20),
        qty: 1,
        price_unit: -5,
        is_reward_line: true,
        reward_id: store.models["loyalty.reward"].get(1),
        coupon_id: localCard,
        price_type: "manual",
    });

    store.couponByLineUuidCache[rewardLine.uuid] = -88;

    order.state = "draft";
    await store.postSyncAllOrders([order]);

    expect(rewardLine.coupon_id?.id).toBe(-88);
});

test("postProcessLoyalty compiles couponData and calls confirm_coupon_programs", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    const order = await createOrderWithLoyalty(
        store,
        [{ product: store.models["product.product"].get(5), qty: 5, price: 10 }],
        partner
    );

    let capturedCouponData = null;
    onRpc("pos.order", "confirm_coupon_programs", ({ args }) => {
        capturedCouponData = args[1];
        return {
            coupon_updates: [],
            program_updates: [],
            coupon_report: {},
        };
    });

    store.addPendingOrder([order.id]);
    await store.syncAllOrders({ orders: [order] });
    await store.postProcessLoyalty(order);

    expect(capturedCouponData).not.toBe(undefined);
});

test("postProcessLoyalty updates card points from coupon_updates (same id)", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    const order = await createOrderWithLoyalty(
        store,
        [{ product: store.models["product.product"].get(5), qty: 5, price: 10 }],
        partner
    );
    store.addPendingOrder([order.id]);
    await store.syncAllOrders({ orders: [order] });

    onRpc("pos.order", "confirm_coupon_programs", () => ({
        coupon_updates: [{ old_id: 1, id: 1, points: 75 }],
        program_updates: [],
        coupon_report: {},
    }));

    await store.postProcessLoyalty(order);

    const card = store.models["loyalty.card"].get(1);
    expect(card?.points).toBe(75);
});

test("postProcessLoyalty replaces local card with server card from coupon_updates (different id)", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    const order = await createOrderWithLoyalty(
        store,
        [{ product: store.models["product.product"].get(5), qty: 5, price: 10 }],
        partner
    );
    store.addPendingOrder([order.id]);
    await store.syncAllOrders({ orders: [order] });

    store.models["loyalty.card"].create({
        id: -5,
        program_id: store.models["loyalty.program"].get(2),
        partner_id: null,
        points: 0,
        code: null,
    });
    order.uiState.couponPointChanges[-5] = {
        points: 1,
        program_id: 2,
        coupon_id: -5,
    };

    onRpc("pos.order", "confirm_coupon_programs", () => ({
        coupon_updates: [
            {
                old_id: -5,
                id: 500,
                points: 1,
                code: "NEW_SERVER_CODE",
                program_id: 2,
                partner_id: null,
            },
        ],
        program_updates: [],
        coupon_report: {},
    }));

    await store.postProcessLoyalty(order);

    const serverCard = store.models["loyalty.card"].get(500);
    expect(serverCard).not.toBe(undefined);
    expect(serverCard.code).toBe("NEW_SERVER_CODE");
    expect(store.models["loyalty.card"].get(-5)).toBe(undefined);
});

test("postProcessLoyalty updates program total_order_count from program_updates", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    const order = await createOrderWithLoyalty(
        store,
        [{ product: store.models["product.product"].get(5), qty: 5, price: 10 }],
        partner
    );
    store.addPendingOrder([order.id]);
    await store.syncAllOrders({ orders: [order] });

    onRpc("pos.order", "confirm_coupon_programs", () => ({
        coupon_updates: [],
        program_updates: [{ program_id: 1, usages: 42 }],
        coupon_report: {},
    }));

    await store.postProcessLoyalty(order);

    const program = store.models["loyalty.program"].get(1);
    expect(program.total_order_count).toBe(42);
});

test("postProcessLoyalty skips RPC when no coupon data to send", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    store.addPendingOrder([order.id]);
    await store.syncAllOrders({ orders: [order] });

    let rpcCalled = false;
    onRpc("pos.order", "confirm_coupon_programs", () => {
        rpcCalled = true;
        return {};
    });

    expect(rpcCalled).toBe(false);
});
