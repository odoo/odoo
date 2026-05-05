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
    const product4 = models["product.template"].get(19);

    const screen = await mountWithCleanup(ProductScreen, {
        props: {
            orderUuid: order.uuid,
        },
    });

    // Autoselect "Default Course 1"
    await screen.addProductToOrder(product1);
    const orderlines1 = order.getOrderlines();
    expect(orderlines1).toHaveLength(1);
    expect(order.courses).toHaveLength(1);
    expect(order.courses[0].name).toBe("Default Course 1");
    expect(orderlines1.filter((o) => o.course_id.id === order.courses[0].id)).toHaveLength(1);

    // Autoselect "Default Course 2"
    await screen.addProductToOrder(product2);
    const orderlines2 = order.getOrderlines();
    expect(orderlines2).toHaveLength(2);
    expect(order.courses).toHaveLength(2);
    expect(order.courses[1].name).toBe("Default Course 2");
    expect(orderlines2.filter((o) => o.course_id.id === order.courses[0].id)).toHaveLength(1);
    expect(orderlines2.filter((o) => o.course_id.id === order.courses[1].id)).toHaveLength(1);

    // No course related to the product category --> take the course selected
    await screen.addProductToOrder(product3);
    const orderlines3 = order.getOrderlines();
    expect(orderlines3).toHaveLength(3);
    expect(order.courses).toHaveLength(2);
    expect(orderlines3.filter((o) => o.course_id.id === order.courses[0].id)).toHaveLength(1);
    expect(orderlines3.filter((o) => o.course_id.id === order.courses[1].id)).toHaveLength(2);

    // Multicategory product --> take the course with the highest priority
    await screen.addProductToOrder(product4);
    const orderlines4 = order.getOrderlines();
    expect(orderlines4).toHaveLength(4);
    expect(orderlines4.filter((o) => o.course_id.id === order.courses[0].id)).toHaveLength(2);
    expect(orderlines4.filter((o) => o.course_id.id === order.courses[1].id)).toHaveLength(2);

    // Multicategory product with selected category --> take the course related to the selected category
    store.setSelectedCategory(2);
    await screen.addProductToOrder(product4);
    const orderlines5 = order.getOrderlines();
    expect(orderlines5).toHaveLength(5);
    expect(orderlines5.filter((o) => o.course_id.id === order.courses[0].id)).toHaveLength(2);
    expect(orderlines5.filter((o) => o.course_id.id === order.courses[1].id)).toHaveLength(3);

    // Multicategory product with selected category not related to the product --> take the course with the highest priority
    store.setSelectedCategory(4);
    await screen.addProductToOrder(product4);
    const orderlines6 = order.getOrderlines();
    expect(orderlines6).toHaveLength(5);
    expect(orderlines6.filter((o) => o.course_id.id === order.courses[0].id)).toHaveLength(2);
    expect(
        orderlines6
            .filter((o) => o.course_id.id === order.courses[0].id)
            .reduce((acc, o) => acc + o.qty, 0)
    ).toBe(3);
    expect(orderlines6.filter((o) => o.course_id.id === order.courses[1].id)).toHaveLength(3);
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
