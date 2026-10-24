import { test, describe, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { addProductLineToOrder } from "@pos_loyalty/../tests/unit/utils";
import { onRpc } from "@web/../tests/web_test_helpers";

definePosModels();

describe("PosStore - loyalty essentials", () => {
    test("updatePrograms", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        const partner = models["res.partner"].get(1);
        // Get loyalty program #5 with program_type = "gift_card" and is_nominative = true
        const program = models["loyalty.program"].get(5);

        models["loyalty.program"].getAll = () => [program];

        order.setPartner(partner);
        order._programIsApplicable = () => true;
        order._code_activated_coupon_ids = [];
        order.uiState.couponPointChanges = {};
        order.pricelist_id = { id: 1 };

        const line = await addProductLineToOrder(store, order, {
            gift_code: "XYZ123",
        });

        order.pointsForPrograms = () => ({
            [program.id]: [{ points: 10 }],
        });

        await store.updatePrograms();

        const changes = order.uiState.couponPointChanges;
        const changeList = Object.values(changes);

        expect(changeList).toHaveLength(1);
        expect(changeList[0].program_id).toBe(program.id);
        expect(changeList[0].points).toBe(10);
        expect(changeList[0].code).toBe("XYZ123");
        expect(changeList[0].product_id).toBe(line.product_id.id);
    });

    test("activateCode", async () => {
        onRpc("loyalty.card", "get_loyalty_card_partner_by_code", () => false);
        const store = await setupPosEnv();
        store.addNewOrder();
        const result = await store.activateCode("EXPIRED");

        expect(result).toBe(true);
    });

    test("fetchLoyaltyCard", async () => {
        const store = await setupPosEnv();
        const models = store.models;

        // Get loyalty program #2 with program_type = "ewallet"
        const program = models["loyalty.program"].get(2);
        const partner = models["res.partner"].get(1);

        const card = await store.fetchLoyaltyCard(program.id, partner.id);

        expect(card.id).toBe(2);
    });

    test("postProcessLoyalty with a reward line without coupon", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();
        const card = models["loyalty.card"].get(1);
        order.uiState.couponPointChanges = {
            [card.id]: { coupon_id: card.id, program_id: 1, points: 100 },
        };

        // A promotion reward line of a draft loaded from the server: its
        // temporary negative coupon id is not serialized.
        await addProductLineToOrder(store, order, {
            is_reward_line: true,
            reward_id: models["loyalty.reward"].get(4),
            points_cost: 0,
        });

        let couponData;
        onRpc("pos.order", "confirm_coupon_programs", ({ args }) => {
            couponData = args[1];
            return {};
        });
        await store.postProcessLoyalty(order);

        expect(Object.keys(couponData)).toEqual([String(card.id)]);
        expect(couponData[card.id].points).toBe(100);
    });
});
