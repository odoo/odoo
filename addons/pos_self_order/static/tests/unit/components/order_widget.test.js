import { test, describe, expect, beforeEach } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { OrderWidget } from "@pos_self_order/app/components/order_widget/order_widget";
import { setupSelfPosEnv, patchSession, getFilledSelfOrder } from "../utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();
beforeEach(patchSession);

describe("order_widget", () => {
    test("buttonToShow", async () => {
        const store = await setupSelfPosEnv();
        const models = store.models;
        const comp = await mountWithCleanup(OrderWidget, { props: { action: () => {} } });

        store.router.activeSlot = "product_list";
        expect(comp.buttonToShow).toEqual({ label: "Checkout", disabled: true });

        await getFilledSelfOrder(store);
        expect(comp.buttonToShow).toEqual({ label: "Checkout", disabled: false });

        store.router.activeSlot = "cart";
        expect(comp.buttonToShow).toEqual({ label: "Order", disabled: false });
        // With valid payment method
        models["pos.payment.method"].getFirst().use_payment_terminal = "stripe";
        expect(comp.buttonToShow).toEqual({ label: "Pay", disabled: false });
    });

    test("lineNotSend", async () => {
        const store = await setupSelfPosEnv();
        const comp = await mountWithCleanup(OrderWidget, { props: { action: () => {} } });

        expect(comp.lineNotSend).toEqual({ price: 0, count: 0 });
        await getFilledSelfOrder(store);
        expect(comp.lineNotSend).toEqual({ price: 595, count: 5 });

        const product1 = store.models["product.template"].get(5);
        await store.addToCart(product1, 1);
        expect(comp.lineNotSend).toEqual({ price: 710, count: 6 });
    });
});
