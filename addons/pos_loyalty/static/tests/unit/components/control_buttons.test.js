import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains, mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { createOrderWithLoyalty } from "@pos_loyalty/../tests/unit/utils";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

async function mountProductScreen(store) {
    return mountWithCleanup(ProductScreen, {
        props: { orderUuid: store.getOrder().uuid },
    });
}

test("Reward button is disabled when no rewards exist", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();
    const productScreen = await mountProductScreen(store);

    productScreen.displayAllControlPopup();
    await animationFrame();
    await waitFor(".control-button:has(i.fa-star)");
    expect(
        document.querySelector(".control-button:has(i.fa-star)").classList.contains("disabled")
    ).toBe(true);
});

test("Reward button is enabled and opens popup when rewards exist", async () => {
    const store = await setupPosEnv();
    const partner = store.models["res.partner"].get(3);
    const order = await createOrderWithLoyalty(
        store,
        [{ product: store.models["product.product"].get(5), qty: 1, price: 10 }],
        partner
    );

    patchWithCleanup(order, {
        getClaimableRewards() {
            return [
                {
                    coupon_id: 1,
                    reward: store.models["loyalty.reward"].get(1), // 10% discount
                    potentialQty: 1,
                },
            ];
        },
    });

    const productScreen = await mountProductScreen(store);
    productScreen.displayAllControlPopup();
    await animationFrame();

    await waitFor(".control-button:has(i.fa-star)");
    const rewardBtn = document.querySelector(".control-button:has(i.fa-star)");
    expect(rewardBtn.classList.contains("disabled")).toBe(false);
    expect(rewardBtn.classList.contains("highlight")).toBe(true);

    await rewardBtn.click();
    await animationFrame();

    expect(".selection-item").toHaveCount(1);
    expect(".selection-item").toHaveText('Loyalty Program\nAdd "10% on your order"'); // from the reward's program name
});

test("Reset Programs button calls pos.resetPrograms()", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    let resetCalled = false;
    patchWithCleanup(store, {
        resetPrograms() {
            resetCalled = true;
        },
    });

    patchWithCleanup(store.getOrder(), {
        isProgramsResettable() {
            return true;
        },
    });

    const productScreen = await mountProductScreen(store);
    productScreen.displayAllControlPopup();

    await contains('.control-button:contains("Reset Programs")').click();
    expect(resetCalled).toBe(true);
});

test("eWallet button handles refunds when order total is negative", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    await store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(5), qty: -1 },
        order
    );

    store.models["loyalty.program"].create({
        name: "eWallet Refund Program",
        program_type: "ewallet",
        trigger_product_ids: [store.models["product.product"].get(5)],
    });
    store.models["loyalty.program"].create({
        name: "eWallet Refund Program 2",
        program_type: "ewallet",
        trigger_product_ids: [store.models["product.product"].get(5)],
    });

    const productScreen = await mountProductScreen(store);
    productScreen.displayAllControlPopup();
    await animationFrame();

    await waitFor(".control-button:has(i.fa-credit-card)");
    const ewalletBtn = document.querySelector(".control-button:has(i.fa-credit-card)");
    expect(ewalletBtn.textContent).toBe("eWallet Refund");
    expect(ewalletBtn.classList.contains("highlight")).toBe(true);
    expect(ewalletBtn.classList.contains("disabled")).toBe(false);

    await ewalletBtn.click();
    await animationFrame();

    expect(".selection-item").toHaveCount(
        store.models["loyalty.program"].filter((p) => p.program_type == "ewallet").length
    );
});

test("_applyReward", async () => {
    const store = await setupPosEnv();
    const models = store.models;
    const order = await createOrderWithLoyalty(
        store,
        [{ product: models["product.product"].get(5), qty: 1, price: 10 }],
        store.models["res.partner"].get(3)
    );

    // Get card #1 - belongs to a loyalty-type program
    const card = models["loyalty.card"].get(1);
    // Get reward #2 - belongs to the same loyalty program, type = discount reward
    const reward = models["loyalty.reward"].get(2);

    // Total quantity in the order
    const potentialQty = order.getOrderlines().reduce((acc, line) => acc + line.qty, 0);

    const component = await mountWithCleanup(ControlButtons, {});

    const result = await component._applyReward(reward, card.id, potentialQty);

    expect(result).toBe(true);
});

test("getPotentialRewards", async () => {
    const store = await setupPosEnv();
    const models = store.models;
    const order = await createOrderWithLoyalty(
        store,
        [{ product: models["product.product"].get(5), qty: 1, price: 10 }],
        store.models["res.partner"].get(3)
    );

    // Get loyalty program #1 - type = loyalty
    const loyaltyProgram = models["loyalty.program"].get(1);
    // Get card #1 - linked to loyalty program #1
    const card = models["loyalty.card"].get(1);

    order._code_activated_coupon_ids = [card];

    const component = await mountWithCleanup(ControlButtons, {});

    const rewards = component.getPotentialRewards();
    const reward = rewards[0].reward;

    expect(reward).toEqual(models["loyalty.reward"].get(1));
    expect(reward.program_id).toEqual(loyaltyProgram);
});
