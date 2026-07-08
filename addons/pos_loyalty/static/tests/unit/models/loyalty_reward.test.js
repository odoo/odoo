import { test, describe, expect } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

describe("loyalty.reward", () => {
    test("Test conditions", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = await getFilledOrder(store); // Should have 2 lines, total of 17.85
        const reward = models["loyalty.reward"].get(1);

        reward.type = "discount";
        reward.required_points = 5;
        reward.discount_applicability = "order";
        expect(reward.discount).toBe(10);
        expect(reward.getRewards(order, 4)).toBe(false);
        expect(reward.getRewards(order, 5)).toEqual({
            clear: false,
            type: "discount",
            discountMode: "percent",
            discountValue: 1.785,
            cost: 5,
        });

        reward.discount_applicability = "cheapest";
        expect(reward.getRewards(order, 5)).toEqual({
            clear: false,
            type: "discount",
            discountMode: "percent",
            discountValue: 0.75,
            cost: 5,
        });

        // Check order products for domain
        expect(order.lines[0].product_id.categ_id.id).toBe(1);
        expect(order.lines[0].product_id.id).toBe(5);
        expect(order.lines[0].product_id.name).toBe("TEST");
        expect(order.lines[0].qty).toBe(3);
        expect(order.lines[1].product_id.name).toBe("TEST 2");
        expect(order.lines[1].product_id.id).toBe(6);
        expect(order.lines[1].qty).toBe(2);
        expect(order.priceExcl).toBe(15);
        expect(order.priceIncl).toBe(17.85);

        reward.discount = 100;
        reward.discount_product_ids = [];
        reward.discount_applicability = "specific";
        reward.discount_product_category_id = false;
        reward.discount_product_domain = '[("id", "in", [5])]';
        expect(reward.getRewards(order, 5)).toEqual({
            clear: false,
            type: "discount",
            discountMode: "percent",
            discountValue: 10.35,
            cost: 5,
        });

        // Should get 5 points
        reward.discount_product_domain = '[("id", "in", [5, 6])]';
        expect(reward.getRewards(order, 5)).toEqual({
            clear: false,
            type: "discount",
            discountMode: "percent",
            discountValue: 17.85,
            cost: 5,
        });

        // Remove the domain and use a category instead
        reward.discount_product_domain = "[]";
        reward.discount_product_category_id = models["product.category"].get(1);
        expect(reward.getRewards(order, 5)).toEqual({
            clear: false,
            type: "discount",
            discountMode: "percent",
            discountValue: 10.35,
            cost: 5,
        });

        // Change the category to one that doesn't match
        reward.discount_product_category_id = models["product.category"].get(2);
        expect(reward.getRewards(order, 5)).toEqual({
            clear: false,
            type: "discount",
            discountMode: "percent",
            discountValue: 0,
            cost: 5,
        });

        // Combine rules - When filled each
        reward.clear_wallet = true;
        reward.discount_product_category_id = models["product.category"].get(1);
        reward.discount_product_domain = '[("id", "in", [6])]';
        expect(reward.getRewards(order, 5)).toEqual({
            clear: true,
            type: "discount",
            discountMode: "percent",
            discountValue: 17.85,
            cost: 5,
        });

        reward.discount_product_category_id = models["product.category"].get(2);
        expect(reward.getRewards(order, 5)).toEqual({
            clear: true,
            type: "discount",
            discountMode: "percent",
            discountValue: 7.5,
            cost: 5,
        });
    });
});
