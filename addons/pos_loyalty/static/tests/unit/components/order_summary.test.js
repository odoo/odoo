import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { waitFor, tick } from "@odoo/hoot-dom";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { createOrderWithLoyalty } from "@pos_loyalty/../tests/unit/utils";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

async function mountProductScreen(store) {
    return mountWithCleanup(ProductScreen, {
        props: { orderUuid: store.getOrder().uuid },
    });
}

test.tags("desktop");
test("backspace on a reward line asks for confirmation", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const reward = store.models["loyalty.reward"].get(1);

    store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(20),
        qty: 1,
        price_unit: -10,
        is_reward_line: true,
        reward_id: reward,
        price_type: "manual",
    });

    await mountProductScreen(store);

    order.selectOrderline(order.lines[0]);
    await animationFrame();

    await contains('.numpad button:contains("⌫")').click();
    await animationFrame();

    await waitFor('.modal .modal-title:contains("Deactivating reward")');

    await contains('.modal .modal-footer .btn-secondary:contains("No")').click();
    await animationFrame();
    expect(order.lines.length).toBe(1);

    await contains('.numpad button:contains("⌫")').click();
    await animationFrame();
    await contains('.modal .modal-footer .btn-primary:contains("Yes")').click();
    await animationFrame();

    expect(order.lines.length).toBe(0);
    expect(order.uiState.disabledRewards.has(reward.id)).toBe(true);
});

test.tags("desktop");
test("- (minus) key shows alert for eWallet or Gift Card lines", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(20),
        qty: 1,
        price_unit: 50,
        _e_wallet_program_id: store.models["loyalty.program"].get(6),
        price_type: "manual",
    });

    await mountProductScreen(store);

    order.selectOrderline(order.lines[0]);
    await animationFrame();

    await contains('.numpad button:contains("+/-")').click();
    await animationFrame();

    await waitFor(".o_notification_manager .o_notification");
    expect(".o_notification_manager .o_notification .o_notification_content").toHaveText(
        "You cannot set negative quantity or price to gift card or ewallet."
    );
});

test.tags("desktop");
test("modifying quantity or price of a physical gift card line shows alert", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    store.models["pos.order.line"].create({
        order_id: order,
        product_id: store.models["product.product"].get(20),
        qty: 1,
        price_unit: 50,
        gift_code: "GC_RECHARGE_CODE",
        price_type: "manual",
    });

    await mountProductScreen(store);

    order.selectOrderline(order.lines[0]);
    await animationFrame();

    await contains('.numpad button:contains("5")').click();
    await animationFrame();

    await waitFor('.modal .modal-title:contains("Gift Card")');
    expect(".modal .modal-title").toHaveText("Gift Card");
    expect(".modal .modal-body").toHaveText(
        "You cannot change the quantity or the price of a physical gift card."
    );

    await contains('.modal .modal-footer .btn-primary:contains("Ok")').click();
    await animationFrame();

    await contains('.numpad button:contains("⌫")').click();
    await tick();

    await waitFor('.orderline .qty:contains("0")');
    expect(order.lines[0].qty).toBe(0);
});

test.tags("desktop");
test("_updateGiftCardOrderline", async () => {
    const store = await setupPosEnv();
    const models = store.models;
    const order = await createOrderWithLoyalty(
        store,
        [{ product: models["product.product"].get(1), qty: 1, price: 50 }],
        store.models["res.partner"].get(3)
    );

    const product = models["product.product"].get(1);
    // Program #3 - loyalty program for gift cards
    const program = models["loyalty.program"].get(3);
    // Card #3 - gift card which program type is gift_card
    const card = models["loyalty.card"].get(3);

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
