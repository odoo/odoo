import { test, expect } from "@odoo/hoot";
import { click, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { mountWithCleanup, contains } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

definePosModels();

test("addProductToOrder", async () => {
    const store = await setupPosEnv();
    const models = store.models;
    const order = store.addNewOrder();

    order.config.use_course_allocation = true;

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

test("select existing order when preset requires order name", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    order.floating_order_name = "The Other Order";
    order.preset_id = 2;
    order.preset_time = luxon.DateTime.now();
    const order2 = await getFilledOrder(store);
    store.setOrder(order2);
    await mountWithCleanup(ProductScreen, { props: { orderUuid: order2.uuid } });

    const namePreset = store.models["pos.preset"].get(3);
    namePreset.use_timing = true;
    await click("button:contains(In)");
    // Select namePreset preset
    await waitFor(".modal-title:contains(Select preset)");
    await click("button:contains(Name Required Preset)");
    await waitFor(".modal-title:contains(Edit Order Name)");
    await animationFrame();
    // Select Existing Order
    await click("button:contains(The Other Order)");
    await animationFrame();
    expect(".modal-dialog").toHaveCount(0);
    expect(store.models["pos.order"].get(order2.id)).toBeEmpty();
    const currentOrder = store.getOrder();
    expect(currentOrder.id).toBe(order.id);
    expect(currentOrder.preset_id.id).toBe(2);
    expect(currentOrder.getName()).toBe("The Other Order");
});

test("breakCombo with course allocation", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    order.config.use_course_allocation = true;

    const product1 = store.models["product.template"].get(7);
    const product2 = store.models["product.product"].get(8);

    product2.pos_categ_ids = [1];

    const screen = await mountWithCleanup(ProductScreen, {
        props: {
            orderUuid: order.uuid,
        },
    });
    screen.addProductToOrder(product1);

    await contains(".modal-dialog article[data-product-id='8']").click();
    await contains(".modal-dialog article[data-product-id='10']").click();
    await contains("button:contains('Add to order')").click();

    expect(order.courses[0].name).toBe("Default Course 2");
    expect(order.courses).toHaveLength(1);

    store.breakCombo(order.lines[0]);

    expect(order.courses[0].name).toBe("Default Course 1");
    expect(order.courses[1].name).toBe("Default Course 2");
    expect(order.courses).toHaveLength(2);

    order.removeOrderline(order.lines[0]);

    expect(order.getOrderlines()).toHaveLength(1);
    expect(order.courses).toHaveLength(1);
    expect(order.courses[0].name).toBe("Default Course 2");
});
