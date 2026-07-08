import { test, describe, expect } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

describe("loyalty.rule", () => {
    test("Test conditions", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = await getFilledOrder(store); // Should have 2 lines, total of 17.85
        const rule = models["loyalty.rule"].get(1);

        // Minimum quantity 0 and minimum amount 0, so its valid
        expect(rule.getPoints(order)).toBe(1);
        expect(rule.reward_point_amount).toBe(1);
        expect(rule.minimum_qty).toBe(0);
        expect(rule.minimum_amount).toBe(0);

        rule.minimum_qty = 3;
        rule.minimum_amount = 17;
        rule.minimum_amount_tax_mode = "excl";
        rule.product_category_id = false;

        expect(rule.getPoints(order)).toBe(0);
        expect(order.priceExcl).toBe(15);
        expect(order.priceIncl).toBe(17.85);

        rule.minimum_amount_tax_mode = "incl";
        expect(rule.getPoints(order)).toBe(1);

        rule.minimum_amount = 20;
        expect(rule.getPoints(order)).toBe(0);

        rule.minimum_amount = 1000;
        rule.minimum_qty = 1000;
        expect(rule.getPoints(order)).toBe(0);
    });

    test("Test among products", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = await getFilledOrder(store); // Should have 2 lines, total of 17.85
        const rule = models["loyalty.rule"].get(1);

        // Remove any conditional rules
        expect(rule.minimum_qty).toBe(0);
        expect(rule.minimum_amount).toBe(0);

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

        // Should get 3 points
        rule.product_category_id = false;
        rule.reward_point_mode = "unit";
        rule.product_domain = '[("id", "in", [5])]';
        expect(rule.getPoints(order)).toBe(3);

        // Should get 5 points
        rule.product_domain = '[("id", "in", [5, 6])]';
        expect(rule.getPoints(order)).toBe(5);

        // Remove the domain and use a category instead
        rule.product_domain = "[]";
        rule.product_category_id = models["product.category"].get(1);
        expect(rule.getPoints(order)).toBe(3);

        // Change the category to one that doesn't match
        rule.product_category_id = models["product.category"].get(2);
        expect(rule.getPoints(order)).toBe(0);

        // Combine rules - When filled each
        rule.product_category_id = models["product.category"].get(1);
        rule.product_domain = '[("id", "in", [6])]';
        expect(rule.getPoints(order)).toBe(5);
        rule.product_category_id = models["product.category"].get(2);
        expect(rule.getPoints(order)).toBe(2);
    });

    test("Points", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = await getFilledOrder(store);
        const rule = models["loyalty.rule"].get(1);

        // Remove any conditional rules
        expect(rule.minimum_qty).toBe(0);
        expect(rule.minimum_amount).toBe(0);

        rule.product_category_id = false;
        rule.reward_point_mode = "unit";
        rule.product_domain = "[]";

        expect(rule.reward_point_amount).toBe(1);
        expect(rule.reward_point_mode).toBe("unit");
        expect(rule.getPoints(order)).toBe(5);

        rule.reward_point_mode = "order";
        expect(rule.getPoints(order)).toBe(1);

        rule.reward_point_mode = "money";
        expect(rule.getPoints(order)).toBe(17);

        rule.minimum_amount_tax_mode = "excl";
        expect(rule.getPoints(order)).toBe(15);

        rule.reward_point_amount = 2;
        expect(rule.getPoints(order)).toBe(30);
    });
});
