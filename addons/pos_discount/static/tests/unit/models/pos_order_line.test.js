import { animationFrame, expect, test } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("isDiscountLine", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const product1 = store.models["product.template"].get(5);
    await store.addLineToOrder(
        {
            product_tmpl_id: product1,
            qty: 1,
        },
        order
    );
    await store.applyDiscount(10);
    await animationFrame();
    const orderline = order.getSelectedOrderline();
    expect(Math.abs(orderline.price_subtotal_incl).toString()).toBe(
        ((order.amount_total + order.amount_tax) * 0.1).toPrecision(2)
    );
    expect(orderline.isDiscountLine).toBe(true);
});

test("Test taxes after fiscal position with discount product (should not change)", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    order.fiscal_position_id = store.models["account.fiscal.position"].get(1);
    await store.applyDiscount(20);
    await animationFrame();
    const discountLine = order.discountLines[0];
    const lineValues = discountLine.prepareBaseLineForTaxesComputationExtraValues();
    const recomputedTaxes = order.fiscal_position_id.getTaxesAfterFiscalPosition(
        discountLine.product_id.taxes_id
    );
    expect(recomputedTaxes).not.toBe(lineValues.tax_ids);
});
