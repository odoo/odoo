import { test, describe, expect, beforeEach } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

const { DateTime } = luxon;

let store;
let models;
let order;

beforeEach(async () => {
    store = await setupPosEnv();
    models = store.models;
    order = store.addNewOrder();
});

describe("pos.order - loyalty", () => {
    test("waitForPushOrder returns true when coupon changes exist", async () => {
        order.uiState.couponPointChanges = {
            key1: { points: 100 },
        };

        expect(order.waitForPushOrder()).toBe(true);

        order.uiState.couponPointChanges = {};
        expect(order.waitForPushOrder()).toBe(false);
    });

    test("_getIgnoredProductIdsTotalDiscount includes gift card product IDs", async () => {
        const product = models["product.template"].get(1);

        const rule = models["loyalty.rule"].get(1);
        rule.valid_product_ids = [product.id];

        const program = models["loyalty.program"].get(3);
        program.program_type = "gift_card";
        program.rule_ids = [rule];

        const ignoredProductIds = order._getIgnoredProductIdsTotalDiscount();

        expect(ignoredProductIds.length).toBeGreaterThan(0);
    });

    test("getOrderlines returns non-reward lines first, then reward lines", async () => {
        const product = models["product.template"].get(1);

        const regularLine1 = await store.addLineToOrder(
            {
                product_tmpl_id: product,
                qty: 1,
                price_unit: 10,
            },
            order
        );

        const rewardLine = await store.addLineToOrder(
            {
                product_tmpl_id: product,
                qty: 1,
                price_unit: 5,
                is_reward_line: true,
            },
            order
        );

        const regularLine2 = await store.addLineToOrder(
            {
                product_tmpl_id: product,
                qty: 1,
                price_unit: 15,
            },
            order
        );

        const orderedLines = order.getOrderlines();
        expect(orderedLines.length).toBe(3);
        expect(orderedLines[0]).toBe(regularLine1);
        expect(orderedLines[1]).toBe(regularLine2);
        expect(orderedLines[2]).toBe(rewardLine);
    });

    test("_get_reward_lines filters reward lines correctly", async () => {
        const product1 = models["product.template"].get(1);

        const rewardLine = await store.addLineToOrder(
            {
                product_tmpl_id: product1,
                qty: 1,
                is_reward_line: true,
            },
            order
        );

        const rewardLines = order._get_reward_lines();
        expect(rewardLines.length).toBe(1);
        expect(rewardLines[0].is_reward_line).toBe(true);
        expect(rewardLines[0]).toBe(rewardLine);
    });

    test("_get_regular_order_lines excludes reward and refunded lines", async () => {
        const product = models["product.template"].get(1);

        const regularLine = await store.addLineToOrder(
            {
                product_tmpl_id: product,
                qty: 1,
                price_unit: 10,
            },
            order
        );

        const rewardLine = await store.addLineToOrder(
            {
                product_tmpl_id: product,
                qty: 1,
                price_unit: 5,
            },
            order
        );

        const refundedLine = await store.addLineToOrder(
            {
                product_tmpl_id: product,
                qty: 1,
                price_unit: 8,
            },
            order
        );

        expect(order.getOrderlines().length).toBe(3);

        rewardLine.update({ is_reward_line: true });
        refundedLine.update({ refunded_orderline_id: 123 });

        const regularLines = order._get_regular_order_lines();

        expect(regularLines.length).toBe(2);
        expect(regularLines[0].id).toBe(regularLine.id);
    });

    test("getLastOrderline returns last non-reward line", async () => {
        const product = models["product.template"].get(1);

        await store.addLineToOrder(
            {
                product_tmpl_id: product,
                qty: 1,
                is_reward_line: false,
            },
            order
        );

        await store.addLineToOrder(
            {
                product_tmpl_id: product,
                qty: 1,
                is_reward_line: true,
            },
            order
        );

        const lastLine = await store.addLineToOrder(
            {
                product_tmpl_id: product,
                qty: 1,
                is_reward_line: false,
            },
            order
        );

        expect(order.getLastOrderline()).toBe(lastLine);
    });

    test("setPricelist removes coupon changes for unavailable programs", async () => {
        const pricelist1 = models["product.pricelist"].create({ id: 1, name: "List 1" });
        const pricelist2 = models["product.pricelist"].create({ id: 2, name: "List 2" });

        models["loyalty.program"].create({
            id: 101,
            pricelist_ids: [pricelist1],
        });

        models["loyalty.program"].create({
            id: 102,
            pricelist_ids: [],
        });

        order.uiState.couponPointChanges = {
            key1: { program_id: 101, points: 100 },
            key2: { program_id: 102, points: 50 },
        };

        order.setPricelist(pricelist2);

        const remainingKeys = Object.keys(order.uiState.couponPointChanges);
        expect(remainingKeys.length).toBe(1);
        expect(order.uiState.couponPointChanges[remainingKeys[0]].program_id).toBe(102);
    });

    test("_resetPrograms clears all loyalty states", async () => {
        const product = models["product.template"].get(1);

        order.uiState.disabledRewards = new Set(["reward1"]);
        order.uiState.codeActivatedProgramRules = ["rule1"];
        order.uiState.couponPointChanges = { key1: { points: 100 } };

        await store.addLineToOrder(
            {
                product_tmpl_id: product,
                qty: 1,
                is_reward_line: true,
            },
            order
        );

        order._resetPrograms();

        expect(order.uiState.disabledRewards.size).toBe(0);
        expect(order.uiState.codeActivatedProgramRules.length).toBe(0);
        expect(Object.keys(order.uiState.couponPointChanges).length).toBe(0);
    });

    test("_programIsApplicable checks program eligibility", async () => {
        const validProgram = models["loyalty.program"].get(1);
        const rule = models["loyalty.rule"].get(1);
        validProgram.rule_ids = [rule];

        expect(order._programIsApplicable(validProgram)).toBe(true);

        const nominativeProgram = models["loyalty.program"].get(1);
        nominativeProgram.is_nominative = true;

        expect(order._programIsApplicable(nominativeProgram)).toBe(false);
    });

    test("_getRealCouponPoints calculates available points correctly", async () => {
        const card = models["loyalty.card"].get(1);
        const program = models["loyalty.program"].get(1);

        order.uiState.couponPointChanges = {
            [card.id]: {
                coupon_id: card.id,
                program_id: program.id,
                points: 25,
            },
        };

        expect(order._getRealCouponPoints(card.id)).toBe(35);
    });

    test("duplicateCouponChanges detects duplicate coupon codes", async () => {
        order.uiState.couponPointChanges = {
            key1: { existing_code: "CARD001", manual: true },
            key2: { code: "CARD002", coupon_id: -1 },
        };

        expect(order.duplicateCouponChanges("CARD001")).toBe(true);
        expect(order.duplicateCouponChanges("CARD002")).toBe(true);
        expect(order.duplicateCouponChanges("UNKNOWN")).toBe(false);
    });

    test("processGiftCard creates new gift card with proper data", async () => {
        const product = models["product.template"].get(1);

        const giftProgram = models["loyalty.program"].get(3);

        const line = await store.addLineToOrder(
            {
                product_tmpl_id: product,
                qty: 1,
                price_unit: 10,
                eWalletGiftCardProgram: giftProgram,
            },
            order
        );

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

    test("_getDiscountableOnOrder calculates total discountable amount", async () => {
        const product = models["product.template"].get(1);
        await store.addLineToOrder(
            {
                product_tmpl_id: product,
                qty: 2,
                price_unit: 10,
            },
            order
        );

        await store.addLineToOrder(
            {
                product_tmpl_id: product,
                qty: 1,
                price_unit: 5,
            },
            order
        );

        const reward = models["loyalty.reward"].get(1);
        const program = models["loyalty.program"].get(1);
        reward.program_id = program;

        const result = order._getDiscountableOnOrder(reward);
        expect(result.discountable).toBe(25);
    });

    test("_computeNItems counts applicable product items", async () => {
        const product1 = models["product.template"].get(1);
        const product5 = models["product.template"].get(5);

        await store.addLineToOrder(
            {
                product_tmpl_id: product1,
                qty: 8,
                price_unit: 10,
            },
            order
        );

        await store.addLineToOrder(
            {
                product_tmpl_id: product5,
                qty: 5,
                price_unit: 15,
            },
            order
        );

        const rule = models["loyalty.rule"].get(1);

        expect(order.getOrderlines().length).toBe(2);
        expect(order._computeNItems(rule)).toBe(13);
    });

    test("_canGenerateRewards validates minimum requirements", async () => {
        const product = models["product.template"].get(1);

        await store.addLineToOrder(
            {
                product_tmpl_id: product,
                qty: 5,
                price_unit: 10,
            },
            order
        );

        const rule = models["loyalty.rule"].get(1);
        rule.minimum_amount = 40;
        rule.minimum_qty = 3;
        rule.minimum_amount_tax_mode = "excl";

        const program = models["loyalty.program"].get(1);
        program.rule_ids = [rule];

        expect(order._canGenerateRewards(program, 50, 50)).toBe(true);
        expect(order._canGenerateRewards(program, 30, 30)).toBe(false);
    });

    test("isProgramsResettable detects if programs need reset", async () => {
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

    test("removeOrderline removes related reward lines together", async () => {
        const reward = models["loyalty.reward"].get(1);
        const coupon = models["loyalty.card"].get(1);
        const product = models["product.template"].get(1);

        const rewardLine = await store.addLineToOrder(
            {
                product_tmpl_id: product,
                qty: 1,
                price_unit: 10,
                is_reward_line: true,
                reward_id: reward,
                coupon_id: coupon,
                reward_identifier_code: "ABC123",
            },
            order
        );

        const normalLine = await store.addLineToOrder(
            {
                product_tmpl_id: product,
                qty: 1,
                price_unit: 20,
                is_reward_line: false,
            },
            order
        );

        expect(order.getOrderlines().length).toBe(2);

        const result = order.removeOrderline(rewardLine);
        expect(result).toBe(true);

        const remainingLines = order.getOrderlines().filter((line) => !line.deleted);
        expect(remainingLines.length).toBe(1);
        expect(remainingLines[0]).toBe(normalLine);
        expect(remainingLines[0].is_reward_line).toBe(false);
    });

    test("isSaleDisallowed allows gift cards in refunds", async () => {
        const giftProgram = models["loyalty.program"].get(3);

        const result = order.isSaleDisallowed({}, { eWalletGiftCardProgram: giftProgram });
        expect(result).toBe(false);
    });

    test("setPartner removes nominative program coupon changes on partner change", async () => {
        const partner1 = models["res.partner"].create({ id: 1, name: "John" });
        const partner2 = models["res.partner"].create({ id: 2, name: "Doe" });

        order.setPartner(partner1);

        const program1 = models["loyalty.program"].get(1);
        program1.is_nominative = true;

        order.uiState.couponPointChanges = {
            key1: { program_id: 1, points: 100 },
            key2: { program_id: 2, points: 50 },
        };

        order.setPartner(partner2);

        const remainingKeys = Object.keys(order.uiState.couponPointChanges);
        expect(remainingKeys.length).toBe(1);
        expect(order.uiState.couponPointChanges[remainingKeys[0]].program_id).toBe(2);
    });

    test("getLoyaltyPoints returns formatted loyalty statistics", async () => {
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
});
