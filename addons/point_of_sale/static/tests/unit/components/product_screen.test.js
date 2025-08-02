import { describe, test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "../utils";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

describe("product_screen.js", () => {
    test("_getProductByBarcode", async () => {
        const store = await setupPosEnv();
        const order = store.getOrder();
        const comp = await mountWithCleanup(ProductScreen, { props: { orderUuid: order.uuid } });
        await comp.addProductToOrder(store.models["product.template"].get(5));

        expect(order.amount_total).toBe(3.45);
        expect(comp.total).toBe("$\u00a03.45");
        expect(comp.items).toBe("1");

        const productByBarcode = await comp._getProductByBarcode({ base_code: "test_test" });
        const match = store.models["product.product"].get(5);

        expect(productByBarcode).toEqual(match);
    });

    test("fastValidate", async () => {
        const store = await setupPosEnv();
        const order = store.getOrder();
        const fastPaymentMethod = order.config.fast_payment_method_ids[0];
        const productScreen = await mountWithCleanup(ProductScreen, {
            props: { orderUuid: order.uuid },
        });
        await productScreen.addProductToOrder(store.models["product.template"].get(5));

        expect(order.amount_total).toBe(3.45);
        expect(productScreen.total).toBe("$\u00a03.45");
        expect(productScreen.items).toBe("1");

        await productScreen.fastValidate(fastPaymentMethod);

        expect(order.payment_ids[0].payment_method_id).toEqual(fastPaymentMethod);
        expect(order.state).toBe("paid");
        expect(order.amount_paid).toBe(3.45);
    });
});
