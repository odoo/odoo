import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import {
    addProductLineToOrder,
    deactivateAllProgramsExcept,
} from "@pos_loyalty/../tests/unit/utils";

definePosModels();

test("manageGiftCard writes the code, amount and expiration date onto the line", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    // No active programs: keep setUnitPrice's recompute from adding reward lines.
    deactivateAllProgramsExcept(store, []);

<<<<<<< 3b5ffdc4184b25128fa8204bccffcce82cad345e
    const line = await addProductLineToOrder(store, order);
||||||| df947972f49099b7cd5638f4d277f36d19339b2c
    const product = models["product.product"].get(1);
    // Program #3 - loyalty program for gift cards
    const program = models["loyalty.program"].get(3);
    // Card #3 - gift card which program type is gift_card
    const card = models["loyalty.card"].get(3);

    await addProductLineToOrder(store, order);

    const points = product.lst_price;

    order.uiState.couponPointChanges[card.id] = {
        coupon_id: card.id,
        program_id: program.id,
        product_id: product.id,
        points: points,
        manual: false,
    };
=======
    const product = models["product.product"].get(1);
    // Program #3 - loyalty program for gift cards
    const program = models["loyalty.program"].get(3);
    // Card #3 - gift card which program type is gift_card
    const card = models["loyalty.card"].get(3);

    await addProductLineToOrder(store, order, {}, { eWalletGiftCardProgram: program });

    const points = product.lst_price;

    order.uiState.couponPointChanges[card.id] = {
        coupon_id: card.id,
        program_id: program.id,
        product_id: product.id,
        points: points,
        manual: false,
    };
>>>>>>> 5c7cedf731ae735be0ce2fdd1edd306f3230697c

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
