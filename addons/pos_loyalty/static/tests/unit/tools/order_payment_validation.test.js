import { describe, test, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { addProductLineToOrder } from "@pos_loyalty/../tests/unit/utils";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";

definePosModels();

describe("order_payment_validation.js", () => {
    test("validateOrder", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();
        const fastPaymentMethod = order.config.fast_payment_method_ids[0];

        // Get loyalty program #1 - type = "loyalty"
        const loyaltyProgram = models["loyalty.program"].get(1);
        // Get loyalty card #1 - linked to Partner #1
        const card = models["loyalty.card"].get(1);
        // Get loyalty reward #1 - type = "discount"
        const reward = models["loyalty.reward"].get(1);

        order.uiState.couponPointChanges = {
            [card.id]: { coupon_id: card.id, program_id: loyaltyProgram.id, points: 100 },
            "-1": { coupon_id: -1, program_id: loyaltyProgram.id, points: 30, partner_id: 1 },
        };

        await addProductLineToOrder(store, order, {
            coupon_id: card,
            is_reward_line: true,
            reward_id: reward,
            points_cost: 60,
        });

        const validation = new OrderPaymentValidation({
            pos: store,
            orderUuid: store.getOrder().uuid,
            fastPaymentMethod: fastPaymentMethod,
        });

        validation.isOrderValid = async () => true;

        await validation.validateOrder();

        expect(card.points).toBe(50);
        expect(loyaltyProgram.total_order_count).toBe(0);
        expect(order.new_coupon_info[0].code).toMatch(/^[A-Za-z0-9]+$/);
        expect(order.new_coupon_info[0].program_name).toBe(loyaltyProgram.name);
    });
});
