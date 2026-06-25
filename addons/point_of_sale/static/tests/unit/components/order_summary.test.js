import { test, expect, animationFrame } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { setupPosEnv, getFilledOrder } from "../utils";
import { getFilledOrderForPriceCheck } from "../accounting/utils";
import { definePosModels } from "../data/generate_model_definitions";
import { queryAll, queryOne } from "@odoo/hoot-dom";

definePosModels();

test("getNewLine", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const orderSummary = await mountWithCleanup(OrderSummary);
    order.getSelectedOrderline().uiState.savedQuantity = 5;
    const newLine = orderSummary.getNewLine();
    expect(newLine.order_id.id).toBe(order.id);
    expect(newLine.qty).toBe(0);
});

test("Display tax include/exclude subtotal label", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);

    order.config.iface_tax_included = "total";
    await mountWithCleanup(OrderSummary);
    const total = queryOne(".total");
    const subtotal = queryAll(".subtotal");
    expect(subtotal).toHaveLength(0);
    expect(total.innerHTML).toBe("$&nbsp;17.85");

    order.config.iface_tax_included = "subtotal";
    await animationFrame();
    const total2 = queryOne(".total");
    const subtotal2 = queryOne(".subtotal");
    expect(total2.innerHTML).toBe("$&nbsp;17.85");
    expect(subtotal2.innerHTML).toBe("$&nbsp;15.00");
});

test("setLinePrice: input is per-unit tax-included price, discount is preserved", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrderForPriceCheck(store);
    const orderSummary = await mountWithCleanup(OrderSummary, {});

    order.config.iface_tax_included = "total";

    // singleTaxLine: 25% tax-excluded, qty=1, no discount.
    // User types 125 (per-unit tax-included). price_unit should be 100.
    const singleTaxLine = order.lines[0];
    await orderSummary.setLinePrice(singleTaxLine, 125);
    expect(singleTaxLine.price_unit).toBe(100);
    expect(singleTaxLine.displayPrice).toBe(125);

    // multiTaxLine: 15% + 25% (both tax-excluded) = 40% total, qty=1, no discount.
    // User types 140 (per-unit tax-included). price_unit should be 100.
    const multiTaxLine = order.lines[1];
    await orderSummary.setLinePrice(multiTaxLine, 140);
    expect(multiTaxLine.price_unit).toBe(100);
    expect(multiTaxLine.displayPrice).toBe(140);

    // Discount is preserved: 10% discount on singleTaxLine.
    // User types 110 as pre-discount per-unit tax-included price.
    // price_unit = 110 / 1.25 = 88. displayPrice = 88 * 0.9 * 1.25 = 99.
    singleTaxLine.setDiscount(10);
    await orderSummary.setLinePrice(singleTaxLine, 110);
    expect(singleTaxLine.price_unit).toBe(88);
    expect(singleTaxLine.displayPrice).toBe(99);
});
