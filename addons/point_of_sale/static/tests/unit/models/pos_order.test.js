import { test, describe, expect } from "@odoo/hoot";
import { getRelatedModelsInstance } from "../data/get_model_definitions";
import { makeMockServer } from "@web/../tests/web_test_helpers";
import { baseData } from "../data/base_data";

describe("class pos.order", () => {
    test("Example test", async () => {
        await makeMockServer();
        const models = getRelatedModelsInstance();
        const data = models.loadConnectedData({
            ...baseData,
            "account.tax": [
                {
                    id: 1,
                    name: "10% - Percentage",
                    price_include: true,
                    include_base_amount: true,
                    is_base_affected: true,
                    has_negative_factor: false,
                    amount_type: "percent",
                    amount: 10.0,
                    formula_decoded_info: false,
                },
            ],
            "product.template": [
                {
                    id: 1,
                    name: "Test Product Template",
                    type: "consu",
                    list_price: 100.0,
                    tax_ids: [1],
                },
            ],
            "product.product": [
                {
                    id: 1,
                    product_tmpl_id: 1,
                    name: "Test Product Variant",
                    lst_price: 100.0,
                },
            ],
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
                    product_id: 1,
                    price_unit: 100.0,
                    qty: 2,
                    tax_ids: [1],
                },
            ],
        });

        const lineTax = data["pos.order.line"][0].getAllPrices();
        expect(lineTax.priceWithTax).toBe(200.0);
        expect(lineTax.priceWithoutTax).toBe(182.0);
        expect(lineTax.taxesData[0].tax).toBe(models["account.tax"].getFirst());
        expect(lineTax.taxDetails[1].base).toBe(182.0);
        expect(lineTax.taxDetails[1].amount).toBe(18.0);
    });
});
