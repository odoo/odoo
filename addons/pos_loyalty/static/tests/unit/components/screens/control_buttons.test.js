import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { deactivateAllProgramsExcept } from "@pos_loyalty/../tests/unit/utils";

definePosModels();

test("getPotentialRewards", async () => {
    const store = await setupPosEnv();
    const models = store.models;
    const order = store.addNewOrder();

    const loyaltyProgram = models["loyalty.program"].get(1);
    const reward = models["loyalty.reward"].get(1);

    // Isolate program 1 so it's the only source of available rewards.
    deactivateAllProgramsExcept(store, [1]);
    // Program 1 offers reward 1 (10% order discount, needs 10 points).
    loyaltyProgram.reward_ids = [1];
    order.setPricelist(models["product.pricelist"].get(1));

    // Card 1 (program 1, 10 points) counts once its code is activated, giving the
    // order exactly the 10 points reward 1 requires.
    order.applied_codes = ["CARD001"];

    const component = await mountWithCleanup(ControlButtons, {});

    const rewards = component.getPotentialRewards();

    expect(rewards[0].reward).toEqual(reward);
    expect(rewards[0].reward.program_id).toEqual(loyaltyProgram);
});
