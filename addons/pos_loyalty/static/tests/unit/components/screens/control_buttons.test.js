import { describe, test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { addProductLineToOrder } from "@pos_loyalty/../tests/unit/utils";

definePosModels();

describe("control_buttons.js", () => {
    test("_applyReward", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        // Get card #1 - belongs to a loyalty-type program
        const card = models["loyalty.card"].get(1);
        // Get reward #2 - belongs to the same loyalty program, type = discount reward
        const reward = models["loyalty.reward"].get(2);

        await addProductLineToOrder(store, order);

        // Total quantity in the order
        const potentialQty = order.getOrderlines().reduce((acc, line) => acc + line.qty, 0);

        const component = await mountWithCleanup(ControlButtons, {});

        const result = await component._applyReward(reward, card.id, potentialQty);

        expect(result).toBe(true);
    });

    test("getPotentialRewards", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const order = store.addNewOrder();

        // Get loyalty program #1 - type = loyalty
        const loyaltyProgram = models["loyalty.program"].get(1);
        // Get card #1 - linked to loyalty program #1
        const card = models["loyalty.card"].get(1);

        await addProductLineToOrder(store, order);
        order._code_activated_coupon_ids = [card];

        const component = await mountWithCleanup(ControlButtons, {});

        const rewards = component.getPotentialRewards();
        const reward = rewards[0].reward;

        expect(reward).toEqual(models["loyalty.reward"].get(1));
        expect(reward.program_id).toEqual(loyaltyProgram);
    });
});
