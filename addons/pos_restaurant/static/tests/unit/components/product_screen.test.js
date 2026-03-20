import { describe, test, expect } from "@odoo/hoot";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
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

describe("Mobile Pay Button", () => {
    test.tags("mobile");
    test("Restaurant - Pay button with no preparation resource", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        // Remove preparation resources (printers)
        store.models["pos.printer"].forEach((printer) => printer.delete());
        const screen = await mountWithCleanup(ProductScreen, {
            props: { orderUuid: order.uuid },
        });

        expect(Boolean(screen.swapButton)).toBe(false);
        expect("button:contains('cart')").toHaveClass("btn-primary");
        expect(".pay-button:contains('Pay')").toHaveCount(1);
        expect(".pay-button:contains('Pay')").toHaveClass("btn-secondary");
        expect(".pay-button:contains('Pay')").toHaveAttribute("disabled");

        await contains(".product:contains('TEST')").click();
        expect(".pay-button:contains('Pay')").toHaveClass("btn-secondary");
        expect(".pay-button:contains('Pay')").not.toHaveAttribute("disabled");
    });

    test.tags("mobile");
    test("Retail - Pay button behavior", async () => {
        const store = await setupPosEnv();
        store.config.module_pos_restaurant = false;
        const order = store.addNewOrder();
        const screen = await mountWithCleanup(ProductScreen, {
            props: { orderUuid: order.uuid },
        });

        expect(Boolean(screen.swapButton)).toBe(false);
        expect("button:contains('cart')").toHaveClass("btn-secondary");
        expect(".pay-button:contains('Pay')").toHaveCount(1);
        expect(".pay-button:contains('Pay')").toHaveClass("btn-primary");
        expect(".pay-button:contains('Pay')").toHaveAttribute("disabled");

        await contains(".product:contains('TEST')").click();
        expect(".pay-button:contains('Pay')").toHaveClass("btn-primary");
        expect(".pay-button:contains('Pay')").not.toHaveAttribute("disabled");
    });
});
