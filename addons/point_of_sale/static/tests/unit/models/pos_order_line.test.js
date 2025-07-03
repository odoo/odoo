import { test, describe, expect } from "@odoo/hoot";
import { setupPosEnv } from "../utils";

describe.current.tags("pos");
describe("pos.order.line", () => {
    test("getAllPrices", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const data = models.loadConnectedData({
            "pos.order": [
                {
                    id: 1,
                    name: "Test Order",
                },
            ],
            "pos.order.line": [
                {
                    id: 1,
                    order_id: 1,
                    product_id: 5,
                    price_unit: 100.0,
                    qty: 2,
                    tax_ids: [1],
                },
            ],
        });

        const lineTax = data["pos.order.line"][0].getAllPrices();
        expect(lineTax.priceWithTax).toBe(230.0);
        expect(lineTax.priceWithoutTax).toBe(200.0);
        expect(lineTax.taxesData[0].tax).toEqual(models["account.tax"].getFirst());
        expect(lineTax.taxDetails[1].base).toBe(200.0);
        expect(lineTax.taxDetails[1].amount).toBe(30.0);
    });
});
