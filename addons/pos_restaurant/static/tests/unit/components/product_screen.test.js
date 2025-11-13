import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

definePosModels();

test("addProductToOrder", async () => {
    const store = await setupPosEnv();
    const models = store.models;
    const order = store.addNewOrder();

    order.config.use_course_allocation = true;
    order.config.iface_available_categ_ids = [1, 2, 4];

    const product1 = models["product.template"].get(5);
    const product2 = models["product.template"].get(6);
    const product3 = models["product.template"].get(12);

    const screen = await mountWithCleanup(ProductScreen, {
        props: {
            orderUuid: order.uuid,
        },
    });

    await screen.addProductToOrder(product1);

    expect(order.getOrderlines()).toHaveLength(1);
    expect(order.courses).toHaveLength(1);
    expect(order.courses[0].name).toBe("Default Course 1");

    await screen.addProductToOrder(product2);

    expect(order.getOrderlines()).toHaveLength(2);
    expect(order.courses).toHaveLength(2);
    expect(order.courses[1].name).toBe("Default Course 2");

    await screen.addProductToOrder(product3);

    expect(order.getOrderlines()).toHaveLength(3);
    expect(order.courses).toHaveLength(2);
});
