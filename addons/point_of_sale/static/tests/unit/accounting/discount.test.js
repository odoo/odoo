import { test, expect } from "@odoo/hoot";
import { expectFormattedPrice, setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { getFilledOrderForPriceCheck } from "./utils";

definePosModels();

test("Taxes object should contain no discount values", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrderForPriceCheck(store);
    order.lines[0].setDiscount(10);
    order.lines[1].setDiscount(20);

    const details = order.prices.taxDetails;
    const line1 = order.lines[0].prices;
    const line2 = order.lines[1].prices;

    // Order prices
    expect(details.base_amount).toBe(980); // Base amount is 980 = (1000 - 10%) + (100 - 20%)
    expect(details.tax_amount).toBe(257); // Tax amount is 257 = (250 - 10%) + (15 - 20%) + (25 - 20%)
    expect(details.total_amount).toBe(1237); // Total amount is 1237 = 980 + 257

    // Formatted prices
    expectFormattedPrice(order.currencyDisplayPrice, "$ 1,237.00");
    expectFormattedPrice(order.currencyAmountTaxes, "$ 257.00");
    expectFormattedPrice(order.lines[0].currencyDisplayPrice, "$ 1,125.00");
    expectFormattedPrice(order.lines[0].currencyDisplayPriceUnit, "$ 1,125.00");
    expectFormattedPrice(order.lines[0].currencyDisplayPriceUnitExcl, "$ 900.00");
    expectFormattedPrice(order.lines[1].currencyDisplayPrice, "$ 112.00");
    expectFormattedPrice(order.lines[1].currencyDisplayPriceUnit, "$ 112.00");
    expectFormattedPrice(order.lines[1].currencyDisplayPriceUnitExcl, "$ 80.00");

    // First line (25% on 1000) - no discount
    expect(line1.no_discount_total_included).toBe(1250);
    expect(line1.no_discount_total_excluded).toBe(1000);
    expect(line1.no_discount_taxes_data[0].tax_amount).toBe(250);
    expect(line1.no_discount_taxes_data[0].tax.amount).toBe(25);

    // Second line (15% + 25% on 100) - no discount
    expect(line2.no_discount_total_included).toBe(140);
    expect(line2.no_discount_total_excluded).toBe(100);
    expect(line2.no_discount_taxes_data[0].tax_amount).toBe(15);
    expect(line2.no_discount_taxes_data[0].tax.amount).toBe(15);
    expect(line2.no_discount_taxes_data[1].tax_amount).toBe(25);
    expect(line2.no_discount_taxes_data[1].tax.amount).toBe(25);
});
