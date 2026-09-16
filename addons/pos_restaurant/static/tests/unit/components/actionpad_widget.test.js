import { expect, test } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("highlightPay", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const comp = await mountWithCleanup(ActionpadWidget, {
        props: {
            order: order,
            actionName: "Payment",
            actionToTrigger: () => {},
        },
    });

    expect(comp.highlightPay).toBe(false);
    // simulating order send
    order.updateLastOrderChange();
    expect(comp.highlightPay).toBe(true);

    // orderline qty change
    order.lines[1].qty = 21;
    expect(comp.highlightPay).toBe(false);
    order.updateLastOrderChange();
    expect(comp.highlightPay).toBe(true);

    // orderline note update
    order.lines[0].note = "Test Orderline Note";
    expect(comp.highlightPay).toBe(false);
    order.updateLastOrderChange();
    expect(comp.highlightPay).toBe(true);

    // general customer note
    order.general_customer_note = "Test Order Customer Note";
    expect(comp.highlightPay).toBe(false);
    order.updateLastOrderChange();
    expect(comp.highlightPay).toBe(true);

    // internal note
    order.internal_note = "Test Order Internal Note";
    expect(comp.highlightPay).toBe(false);
    order.updateLastOrderChange();
    expect(comp.highlightPay).toBe(true);
});

test("displayFireCourseBtn when a course product is routed to preparation", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    order.table_id = store.models["restaurant.table"].get(2);
    const course = store.addCourse();
    order.selectCourse(course);
    const comp = await mountWithCleanup(ActionpadWidget, {
        props: {
            order: order,
            actionName: "Payment",
            actionToTrigger: () => {},
        },
    });

    expect(store.config.preparationCategories.has(1)).toBe(true);
    expect(comp.displayFireCourseBtn).toBe(true);
});

test("displayFireCourseBtn hidden when no course product is routed to preparation", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    order.table_id = store.models["restaurant.table"].get(2);
    await store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(12), qty: 1 },
        order
    );
    const course = store.addCourse();
    order.selectCourse(course);
    const comp = await mountWithCleanup(ActionpadWidget, {
        props: {
            order: order,
            actionName: "Payment",
            actionToTrigger: () => {},
        },
    });

    expect(store.config.preparationCategories.has(4)).toBe(false);
    expect(course.isReadyToFire()).toBe(true);
    expect(comp.displayFireCourseBtn).toBe(false);
});

test("getCourseToFire falls back to the next fireable course", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    order.table_id = store.models["restaurant.table"].get(2);
    await store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(12), qty: 1 },
        order
    );
    const unrouted = store.addCourse();
    const routed = order.courses[1];
    const line = await store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(5), qty: 1 },
        order
    );
    line.course_id = routed;
    order.selectCourse(unrouted);
    const comp = await mountWithCleanup(ActionpadWidget, {
        props: {
            order: order,
            actionName: "Payment",
            actionToTrigger: () => {},
        },
    });

    expect(order.getSelectedCourse()).toBe(unrouted);
    expect(unrouted.isReadyToFire()).toBe(true);
    expect(comp.getCourseToFire()).toBe(routed);
    expect(comp.displayFireCourseBtn).toBe(true);
});

test("getCourseToFire does not go back to an earlier course", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    order.table_id = store.models["restaurant.table"].get(2);
    await store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(5), qty: 1 },
        order
    );
    const routed = store.addCourse();
    const unrouted = order.courses[1];
    const line = await store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(12), qty: 1 },
        order
    );
    line.course_id = unrouted;
    order.selectCourse(unrouted);
    const comp = await mountWithCleanup(ActionpadWidget, {
        props: {
            order: order,
            actionName: "Payment",
            actionToTrigger: () => {},
        },
    });

    expect(routed.canBeFired()).toBe(true);
    expect(comp.getCourseToFire()).toBe(undefined);
    expect(comp.displayFireCourseBtn).toBe(false);
});
