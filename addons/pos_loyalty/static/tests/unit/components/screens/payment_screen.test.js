import { describe, test, expect } from "@odoo/hoot";
import { mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

describe("payment_screen.js", () => {
    test("validateOrder should handle full loyalty flow including point updates, coupon replacement, and history", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        const template = models["product.template"].get(1);
        const partner = models["res.partner"].get(1);

        const rule = models["loyalty.rule"].get(1);
        const loyaltyProgram = models["loyalty.program"].get(1);
        loyaltyProgram.rule_ids = [rule];

        const card = models["loyalty.card"].get(1);
        card.program_id = loyaltyProgram;
        card.partner_id = partner;

        const reward = models["loyalty.reward"].get(1);
        reward.program_id = loyaltyProgram;

        order.uiState.couponPointChanges = {
            [card.id]: { coupon_id: card.id, program_id: loyaltyProgram.id, points: 60 },
        };

        await store.addLineToOrder(
            {
                product_tmpl_id: template,
                qty: 1,
                price_unit: 10,
                coupon_id: card,
                is_reward_line: true,
                reward_id: reward,
            },
            order
        );

        const screen = await mountWithCleanup(PaymentScreen, {
            props: {
                orderUuid: order.uuid,
            },
        });

        screen._isOrderValid = async () => true;

        onRpc("pos.order", "validate_coupon_programs", () => ({
            successful: true,
            payload: {
                updated_points: { [card.id]: 60 },
                removed_coupons: [],
            },
        }));

        onRpc("pos.order", "confirm_coupon_programs", () => ({
            coupon_updates: [
                {
                    id: 101,
                    old_id: card.id,
                    code: "CODE101",
                    program_id: loyaltyProgram.id,
                    partner_id: partner.id,
                    points: 30,
                },
            ],
            program_updates: [],
            coupon_report: {},
            new_coupon_info: { 101: "info" },
        }));

        let historyCalled = false;
        onRpc("pos.order", "add_loyalty_history_lines", () => {
            historyCalled = true;
            return true;
        });

        await screen.validateOrder();

        const newCoupon = models["loyalty.card"].get(101);
        expect(card.points).toBe(60);
        expect(newCoupon).toMatchObject({ id: 101, points: 30 });
        expect(order.new_coupon_info).toMatchObject({ 101: "info" });
        expect(historyCalled).toBe(true);
    });
});
