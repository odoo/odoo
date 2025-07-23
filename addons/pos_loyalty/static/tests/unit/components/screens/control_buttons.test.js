import { describe, test, expect, beforeEach } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { TextInputPopup } from "@point_of_sale/app/components/popups/text_input_popup/text_input_popup";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

let store;
let models;

beforeEach(async () => {
    store = await setupPosEnv();
    models = store.models;
});

describe("control_buttons.js", () => {
    test("_applyReward should apply reward if product reward and single product", async () => {
        const order = store.addNewOrder();

        const card = models["loyalty.card"].get(1);
        const template = models["product.template"].get(1);
        const product = models["product.product"].get(1);
        const reward = models["loyalty.reward"].get(1);
        reward.reward_product_ids = [product];
        reward.reward_type = "product";

        await store.addLineToOrder({ product_tmpl_id: template, qty: 2 }, order);
        const potentialQty = order.getOrderlines().reduce((acc, line) => acc + line.qty, 0);

        const component = await mountWithCleanup(ControlButtons, {});

        const result = await component._applyReward(reward, card.id, potentialQty);

        expect(result).toBe(true);
    });

    test("clickPromoCode should open input popup and call activateCode", async () => {
        const called = [];

        store.activateCode = async (code) => {
            called.push(code);
            return true;
        };

        let popupProps = null;

        store.env.services.dialog.add = (Component, props) => {
            if (Component === TextInputPopup) {
                popupProps = props;
            }
        };

        const control = await mountWithCleanup(ControlButtons, {});

        await control.clickPromoCode();
        expect(popupProps).not.toBe(null);

        await popupProps.getPayload("  ABC123  ");

        expect(called).toInclude("ABC123");
    });

    test("getPotentialRewards should filter out ewallet rewards", async () => {
        const order = store.addNewOrder();

        const template = models["product.template"].get(1);
        const loyaltyProgram = models["loyalty.program"].get(1);
        const ewalletProgram = models["loyalty.program"].get(2);

        const reward1 = models["loyalty.reward"].get(1);
        const reward2 = models["loyalty.reward"].get(2);
        reward1.program_id = loyaltyProgram;
        reward2.program_id = ewalletProgram;

        const card = models["loyalty.card"].get(1);
        card.program_id = loyaltyProgram;

        await store.addLineToOrder({ product_tmpl_id: template, qty: 1 }, order);
        order._code_activated_coupon_ids = [card];

        const component = await mountWithCleanup(ControlButtons, {});

        const rewards = component.getPotentialRewards();

        expect(rewards.map((r) => r.reward.id)).toEqual([1]);
    });
});
