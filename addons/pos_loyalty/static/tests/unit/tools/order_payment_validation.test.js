import { test, expect, tick } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { addProductLineToOrder } from "@pos_loyalty/../tests/unit/utils";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";

definePosModels();

test("validateOrder", async () => {
    const store = await setupPosEnv();
    const models = store.models;
    const order = await getFilledOrder(store);
    const partner = models["res.partner"].get(4);
    order.setPartner(partner);
    const fastPaymentMethod = order.config.fast_payment_method_ids[0];

    // Get loyalty card #1 - linked to Partner #1
    const card = models["loyalty.card"].get(1);
    // Get loyalty reward #1 - type = "discount"
    const reward = models["loyalty.reward"].get(1);

    await addProductLineToOrder(store, order, {
        coupon_id: card,
        is_reward_line: true,
        reward_id: reward,
        points_cost: 5,
    });
    await store.updatePrograms();
    const validation = new OrderPaymentValidation({
        pos: store,
        orderUuid: store.getOrder().uuid,
        fastPaymentMethod: fastPaymentMethod,
    });

    validation.isOrderValid = async () => true;

    await validation.validateOrder(false);
    // validateOrder launches a promise. We need to wait for its resolution.
    await tick();
    expect(card.points).toBe(5); // 10 - 5 points_cost
    expect(order.new_coupon_info).toHaveLength(1); // One applies_on "future" type coupon
    expect(order.loyalty_card_ids).toHaveLength(3); // Three new loyalty cards sold
});
