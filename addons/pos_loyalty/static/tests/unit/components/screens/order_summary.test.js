import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { addProductLineToOrder } from "@pos_loyalty/../tests/unit/utils";

definePosModels();

test("_updateGiftCardOrderline", async () => {
    const store = await setupPosEnv();
    const models = store.models;
    const order = store.addNewOrder();

    const product = models["product.product"].get(1);
    // Program #3 - loyalty program for gift cards
    const program = models["loyalty.program"].get(3);
    // Card #3 - gift card which program type is gift_card
    const card = models["loyalty.card"].get(3);

    await addProductLineToOrder(store, order);

    const points = product.lst_price;

    order.uiState.couponPointChanges[card.id] = {
        coupon_id: card.id,
        program_id: program.id,
        product_id: product.id,
        points: points,
        manual: false,
    };

    const component = await mountWithCleanup(OrderSummary, {});

    await component._updateGiftCardOrderline("ABC123", points);

    const updatedLine = order.getSelectedOrderline();

    expect(updatedLine.gift_code).toBe("ABC123");
    expect(updatedLine.product_id.id).toBe(product.id);
    expect(updatedLine.getQuantity()).toBe(1);
    expect(order.uiState.couponPointChanges[card.id]).toBe(undefined);
});
