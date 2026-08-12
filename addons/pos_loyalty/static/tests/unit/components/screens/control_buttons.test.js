import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import {
    deactivateAllProgramsExcept,
    addProductLineToOrder,
} from "@pos_loyalty/../tests/unit/utils";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";

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

test("more button catches attention when rewards are available", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const card = store.models["loyalty.card"].get(1);

    await addProductLineToOrder(store, order);
    order._code_activated_coupon_ids = [card];

    await mountWithCleanup(ProductScreen, { props: { orderUuid: order.uuid } });
    const moreButtonSelector = PosUiUtils.isMobile() ? ".mobile-more-button" : ".more-btn";
    if (PosUiUtils.isMobile()) {
        PosUiUtils.ensurePane("left");
    }
    expect(moreButtonSelector).toHaveClass("o_catch_attention_reward");
    expect(`${moreButtonSelector} .o_reward-star`).toHaveCount(1);
});
