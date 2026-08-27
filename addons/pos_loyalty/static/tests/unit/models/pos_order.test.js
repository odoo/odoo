import { test, describe, expect } from "@odoo/hoot";
import { tick } from "@odoo/hoot-mock";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import {
    addProductLineToOrder,
    deactivateAllProgramsExcept,
} from "@pos_loyalty/../tests/unit/utils";

definePosModels();

describe("pos.order - loyalty", () => {
    test("getOrderlines sorts reward lines last", async () => {
        const store = await setupPosEnv();
        // Avoid any auto-applied reward lines so the ordering is controlled by the test.
        deactivateAllProgramsExcept(store, []);
        const order = store.addNewOrder();

        const rewardLine = await addProductLineToOrder(store, order, {
            productId: 5,
            templateId: 5,
        });
        const productLine = await addProductLineToOrder(store, order, {
            productId: 6,
            templateId: 6,
        });
        rewardLine.update({ is_reward_line: true });

        const orderedLines = order.getOrderlines();

        expect(orderedLines[0]).toBe(productLine);
        expect(orderedLines[1]).toBe(rewardLine);
        expect(orderedLines[0].is_reward_line).not.toBe(true);
        expect(orderedLines[1].is_reward_line).toBe(true);
    });

    test("claimed loyalty state survives an IndexedDB round-trip", async () => {
        const store = await setupPosEnv();
        deactivateAllProgramsExcept(store, [8]);
        const order = store.addNewOrder();
        await addProductLineToOrder(store, order);

        // Prevent the auto-apply path so the reward line can only be rebuilt from
        // active_rewards: that's the state a page reload must restore.
        order.disabled_program_ids = [8];
        order.active_rewards = [{ reward_id: 4, qty: 2 }];
        order.active_payment_programs = [{ reward_id: 5, card_id: 3 }];

        // indexed_db.js stores JSON.parse(JSON.stringify(serializeForIndexedDB(record))).
        const restored = JSON.parse(JSON.stringify(order.serializeForIndexedDB()));

        // The entries must round-trip as plain id-based data (no live records).
        expect(restored.active_rewards).toEqual([{ reward_id: 4, qty: 2 }]);
        expect(restored.active_payment_programs).toEqual([{ reward_id: 5, card_id: 3 }]);

        // Simulate a reload: the restored state must be directly consumable by
        // recomputeRewards, which deletes and rebuilds all reward lines.
        order.active_rewards = restored.active_rewards;
        order.recomputeRewards();
        const rewardLines = order
            .getOrderlines()
            .filter((line) => line.is_reward_line && line.reward_id?.id === 4);
        expect(rewardLines.length).toBe(1);
    });

    test("a pricelist-restricted program only applies for its pricelist", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        // Program 8 is an auto discount restricted to pricelist 1.
        deactivateAllProgramsExcept(store, [8]);

        order.setPricelist(models["product.pricelist"].get(1));
        expect(order.appliedPrograms.map((program) => program.id)).toInclude(8);

        // Switching to a pricelist the program doesn't allow drops it.
        order.setPricelist(models["product.pricelist"].get(2));
        expect(order.appliedPrograms.map((program) => program.id)).not.toInclude(8);

        await addProductLineToOrder(store, order);
        await store.selectPricelist(models["product.pricelist"].get(1));
        expect(order.getOrderlines().some((line) => line.is_reward_line)).toBe(true);
        await store.selectPricelist(models["product.pricelist"].get(2));
        expect(order.getOrderlines().some((line) => line.is_reward_line)).toBe(false);
        await store.selectPricelist(models["product.pricelist"].get(1));
        expect(order.getOrderlines().some((line) => line.is_reward_line)).toBe(true);
    });

    test("a cheapest discount reward line excludes fixed tax", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        // Program 8 is an auto cheapest discount (reward 4), restricted to pricelist 1.
        deactivateAllProgramsExcept(store, [8]);
        order.setPricelist(models["product.pricelist"].get(1));

        // Tax #1 becomes a fixed tax, tax #2 stays as percent.
        const fixedTax = models["account.tax"].get(1);
        const percentTax = models["account.tax"].get(2);
        fixedTax.amount_type = "fixed";
        models["product.template"].get(5).taxes_id = [fixedTax, percentTax];

        const reward = models["loyalty.reward"].get(4);
        reward.all_discount_product_ids = [models["product.product"].get(5)];

        await addProductLineToOrder(store, order, { templateId: 5, productId: 5 });
        order.recomputeRewards();

        const rewardLine = order.getOrderlines().find((line) => line.is_reward_line);
        const taxIds = rewardLine.tax_ids.map((tax) => tax.id);
        expect(taxIds).toInclude(percentTax.id);
        expect(taxIds).not.toInclude(fixedTax.id);
    });

    test("a specific discount reward line excludes fixed tax", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        deactivateAllProgramsExcept(store, [8]);
        order.setPricelist(models["product.pricelist"].get(1));

        const fixedTax = models["account.tax"].get(1);
        const percentTax = models["account.tax"].get(2);
        fixedTax.amount_type = "fixed";
        models["product.template"].get(5).taxes_id = [fixedTax, percentTax];

        const reward = models["loyalty.reward"].get(4);
        reward.discount_applicability = "specific";
        reward.all_discount_product_ids = [models["product.product"].get(5)];

        await addProductLineToOrder(store, order, { templateId: 5, productId: 5 });
        order.recomputeRewards();

        const rewardLine = order.getOrderlines().find((line) => line.is_reward_line);
        const taxIds = rewardLine.tax_ids.map((tax) => tax.id);
        expect(taxIds).toInclude(percentTax.id);
        expect(taxIds).not.toInclude(fixedTax.id);
    });

    test("product-restricted rules only earn points with a valid product", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        // Restrict loyalty rule #1 (program #1, order-mode, 1 point) to product #5 only.
        const rule = models["loyalty.rule"].get(1);
        rule.any_product = false;
        const program = models["loyalty.program"].get(1);

        // Order only contains product #1, which is not valid for the rule: nothing earned.
        await addProductLineToOrder(store, order, { qty: 1 });
        expect(program.getEarnedPoints(order)).toBe(0);

        // Adding the valid product #5 makes the rule apply.
        await addProductLineToOrder(store, order, { templateId: 5, productId: 5 });
        expect(program.getEarnedPoints(order)).toBe(1);
    });

    test("removeOrderline removes a reward line and re-selects the product line", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        // Program 8's auto 100% cheapest discount produces a reward line for product 24.
        deactivateAllProgramsExcept(store, [8]);
        order.setPricelist(models["product.pricelist"].get(1));

        const productLine = await addProductLineToOrder(store, order, {
            productId: 24,
            templateId: 24,
        });
        await store.updateRewards();
        await tick();

        const rewardLine = order.getOrderlines().find((line) => line.is_reward_line);
        expect(order.getOrderlines().length).toBe(2);

        const result = order.removeOrderline(rewardLine);
        expect(result).toBe(true);

        // Removing the reward line disables its program, so it isn't rebuilt.
        const remainingLines = order.getOrderlines();
        expect(remainingLines.length).toBe(1);
        expect(remainingLines[0].id).toBe(productLine.id);
        expect(remainingLines[0].is_reward_line).not.toBe(true);
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

    test("totalItemQuantity", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();

        await addProductLineToOrder(store, order);
        const rewardLine = await addProductLineToOrder(store, order);
        rewardLine.is_reward_line = true;

        expect(order._isItemCountExcludedLine(rewardLine)).toBe(true);
        expect(order.totalItemQuantity).toBe(1);
    });

    test("changing partner drops nominative rewards and updates the balance", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        const partner1 = models["res.partner"].get(1);
        const partner2 = models["res.partner"].get(3);
        const program = models["loyalty.program"].get(7); // loyalty, nominative

        store.setPartnerToCurrentOrder(partner1);
        // Card 4 (program 7, partner 1, 3 points) is partner1's balance; nothing earned yet.
        expect(program.getEarnedPoints(order)).toBe(0);
        expect(program.getAvailablePoints(order)).toBe(3);

        // Claim reward 3 (program 7, nominative free product) for partner1; recompute builds
        // the reward line from the program.
        order.active_rewards = [{ reward_id: 3 }];
        await store.updateRewards();
        await tick();
        expect(order.getOrderlines().filter((line) => line.is_reward_line).length).toBeGreaterThan(
            0
        );

        // Switching partner triggers removeNominativeRewards, dropping partner1's rewards
        // and its balance.
        store.setPartnerToCurrentOrder(partner2);
        expect(order.active_rewards).toHaveLength(0);
        expect(order.getOrderlines().filter((line) => line.is_reward_line)).toHaveLength(0);
        expect(program.getAvailablePoints(order)).toBe(0); // partner2 has no program-7 card
    });

    test("a 100% cheapest discount reward line is the product's full tax-included price", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        // Program 8 is an auto 100% cheapest discount, restricted to pricelist 1.
        deactivateAllProgramsExcept(store, [8]);
        order.setPricelist(models["product.pricelist"].get(1));

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
        const rewardLine = order.getOrderlines().find((orderline) => orderline.is_reward_line);
        expect(rewardLine.prices.total_included).toBe(-10);
    });

    test("an already applied discount reward is not offered again", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();
        deactivateAllProgramsExcept(store, [8]);
        order.setPricelist(models["product.pricelist"].get(1));

        // 2 units grant 2 points, the reward costs 1: it auto-applies once.
        await addProductLineToOrder(store, order, { qty: 2 });
        await store.updateRewards();
        await tick();
        expect(order.getOrderlines().filter((line) => line.is_reward_line)).toHaveLength(1);

        // Adding more products doesn't apply the discount a second time.
        await addProductLineToOrder(store, order, { templateId: 5, productId: 5 });
        await store.updateRewards();
        await tick();
        expect(order.getOrderlines().filter((line) => line.is_reward_line)).toHaveLength(1);

        // The applied reward is no longer offered for claiming.
        expect(order.availableRewards.filter(({ reward }) => reward.id === 4)).toHaveLength(0);
    });

    test("stacked specific discounts respect discount_max_amount", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        const models = store.models;
        deactivateAllProgramsExcept(store, [1, 9]);

        const loyalty_program = models["loyalty.program"].get(1);
        const loyalty_reward = models["loyalty.reward"].get(4);

        const code_program = models["loyalty.program"].get(9);
        const code_rule = models["loyalty.rule"].get(3);
        const code_reward = models["loyalty.reward"].get(1);

        // Program 1: a specific discount on product 8, capped at 100.
        loyalty_program.reward_ids = [4];
        loyalty_reward.discount_applicability = "specific";
        loyalty_reward.all_discount_product_ids = [8];
        loyalty_reward.discount_max_amount = 100;

        // Program 9: a with_code ("EXPIRED") specific discount on product 8.
        code_program.rule_ids = [3];
        code_program.reward_ids = [1];
        code_rule.valid_product_ids = [];
        code_rule.reward_point_amount = 10;
        code_rule.minimum_qty = 1;
        code_reward.discount_applicability = "specific";
        code_reward.all_discount_product_ids = [8];
        code_reward.discount_line_product_id = 5;

        store.setPartnerToCurrentOrder(models["res.partner"].get(1));
        order.setPricelist(models["product.pricelist"].get(1));

        await addProductLineToOrder(store, order, {
            productId: 8,
            templateId: 8,
            price_unit: 300,
            qty: 1,
        });

        // Claim program 1's capped discount, then enter program 9's code.
        order.active_rewards = [{ reward_id: loyalty_reward.id }];
        await store.loadCode("EXPIRED");
        order.applyCode("EXPIRED");
        order.recomputeRewards();
        await tick();

        expect(order.getOrderlines().length).toBe(3);
        // Product 8 is 25%-taxed: the with_code 10% reward is -37.5 (10% of 375 incl), and
        // program 1's specific reward is capped at its discount_max_amount of 100.
        expect(order.lines[1].prices.total_included).toBe(-37.5);
        expect(order.lines[2].prices.total_included).toBe(-100);
    });

    test("a reward for a no_variant/custom attribute product carries the selected attributes onto the order line", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();
        deactivateAllProgramsExcept(store, [7]);

        // Product 51 (Cake, Chocolate) has attribute line 4: attribute 11 "Customization" is
        // no_variant and its only value (7, "Yes") is_custom.
        const product = models["product.product"].get(51);
        const customizationValue = models["product.template.attribute.value"].get(7);

        // Reward 3 (program 7) costs 1 point; give it product 51 as its free product.
        const reward = models["loyalty.reward"].get(3);
        reward.update({ reward_product_id: product, reward_product_ids: [product] });

        // Card 4 gives partner 1 exactly the 3 (>= 1 required) points program 7 needs.
        store.setPartnerToCurrentOrder(models["res.partner"].get(1));

        order.active_rewards = [
            {
                reward_id: reward.id,
                attribute_value_ids: [customizationValue.id],
                attribute_custom_values: { [customizationValue.id]: "Happy Birthday" },
            },
        ];
        order.recomputeRewards();
        await tick();

        const rewardLine = order.getOrderlines().find((line) => line.is_reward_line);
        expect(rewardLine).not.toBe(undefined);
        expect(rewardLine.product_id.id).toBe(product.id);
        expect(rewardLine.attribute_value_ids.map((v) => v.id)).toInclude(customizationValue.id);
        expect(rewardLine.custom_attribute_value_ids.length).toBe(1);
        expect(
            rewardLine.custom_attribute_value_ids[0].custom_product_template_attribute_value_id.id
        ).toBe(customizationValue.id);
        expect(rewardLine.custom_attribute_value_ids[0].custom_value).toBe("Happy Birthday");
    });
});
