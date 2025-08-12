import { describe, expect, test } from "@odoo/hoot";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import { getFilledOrder, setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

describe("order_payment_validation.test.js", () => {
    test("validateOrder", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const fastPaymentMethod = order.config.fast_payment_method_ids[0];
        const validation = new OrderPaymentValidation({
            pos: store,
            orderUuid: store.getOrder().uuid,
            fastPaymentMethod: fastPaymentMethod,
        });
        await validation.validateOrder(false);
        expect(order.payment_ids[0].payment_method_id).toEqual(fastPaymentMethod);
        expect(order.state).toBe("paid");
        expect(order.amount_paid).toBe(17.85);
    });
    test("isOrderValid", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        order.setToInvoice(true);
        const validation = new OrderPaymentValidation({
            pos: store,
            orderUuid: store.getOrder().uuid,
        });
        const isOrderValid = await validation.isOrderValid(false);
        expect(order.lines).toHaveLength(0);
        expect(isOrderValid).toBe(false); // The order cannot be invoiced if the order line count is zero.
    });
});
