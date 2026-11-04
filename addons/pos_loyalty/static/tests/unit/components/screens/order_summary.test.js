import { test, expect, animationFrame } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import {
    addProductLineToOrder,
    deactivateAllProgramsExcept,
    mockAccessRight,
} from "@pos_loyalty/../tests/unit/utils";

definePosModels();

test("manageGiftCard writes the code, amount and expiration date onto the line", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    // No active programs: keep setUnitPrice's recompute from adding reward lines.
    deactivateAllProgramsExcept(store, []);

    const line = await addProductLineToOrder(store, order);

    const component = await mountWithCleanup(OrderSummary);

    // manageGiftCard opens ManageGiftCardPopup; capture its getPayload and drive it
    // directly instead of going through the dialog.
    let getPayload;
    component.dialog.add = (Comp, props) => {
        getPayload = props.getPayload;
    };
    component.manageGiftCard(line);

    getPayload("ABC123", "100", "2030-01-31");

    expect(line.gift_card_vals).toEqual({ code: "ABC123", expiration_date: "2030-01-31" });
    expect(line.price_unit).toBe(100);
    expect(order.getSelectedOrderline()).toBe(line);
});

test("loyalty points visibility", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const canApplyRewards = mockAccessRight(store, "canApplyRewards", true);

    deactivateAllProgramsExcept(store, [1]);
    order.applied_codes = [store.models["loyalty.card"].get(1).code];
    await addProductLineToOrder(store, order);
    await mountWithCleanup(OrderSummary);

    expect(".loyalty-points-title").toHaveCount(0);

    order.setPartner(store.models["res.partner"].get(1));
    await animationFrame();
    expect(".loyalty-points-title").toHaveText("Points");
    expect(".loyalty-points-balance").toHaveText("10");
    expect(".loyalty-points-won").toHaveText("+1");
    expect(".loyalty-points-total").toHaveText("11");

    canApplyRewards.set(false);
    await animationFrame();
    expect(".loyalty-points-title").toHaveCount(0);

    canApplyRewards.set(true);
    await animationFrame();
    expect(".loyalty-points-title").toHaveText("Points");
    expect(".loyalty-points-total").toHaveText("11");

    order.setPartner(false);
    await animationFrame();
    expect(".loyalty-points-title").toHaveCount(0);
});
