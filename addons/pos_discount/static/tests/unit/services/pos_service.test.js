import { test, describe, expect } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
definePosModels();

describe("PoS Discount", () => {
    test("changing fiscal positions reapplies the global discount", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();

        const product = store.models["product.template"].get(5);

        await store.addLineToOrder({ product_tmpl_id: product, qty: 10 }, order);
        expect(order.priceIncl).toBe(34.5);
        expect(order.priceExcl).toBe(30);
        expect(order.amountTaxes).toBe(4.5);

        await store.applyDiscount(10);
        expect(order.priceIncl).toBe(31.05);
        expect(order.priceExcl).toBe(27);
        expect(order.amountTaxes).toBe(4.05);

        let [productLine, discountLine] = order.lines;
        expect(productLine.priceIncl).toBe(34.5);
        expect(discountLine.priceIncl).toBe(-3.45);

        let resolveReapplyDiscount = null;
        const reapplyDiscountPromise = new Promise((resolve) => {
            resolveReapplyDiscount = resolve;
        });

        patchWithCleanup(store, {
            async debouncedDiscount() {
                await super.applyDiscount(...arguments);
                resolveReapplyDiscount();
            },
        });

        const nonTaxFP = store.models["account.fiscal.position"].get(2);
        order.fiscal_position_id = nonTaxFP;

        await reapplyDiscountPromise;
        expect(order.priceIncl).toBe(27);
        expect(order.priceExcl).toBe(27);
        expect(order.amountTaxes).toBe(0);

        [productLine, discountLine] = order.lines;
        expect(productLine.priceIncl).toBe(30);
        expect(discountLine.priceIncl).toBe(-3);
    });
});
