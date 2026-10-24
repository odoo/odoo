import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { fireCourse } from "@pos_restaurant/../tests/unit/data/pos_course.data";

const { DateTime } = luxon;

definePosModels();

test("getOrders", async () => {
    const store = await setupPosEnv();
    const table = store.models["restaurant.table"].get(2);
    const order = store.addNewOrder({ table_id: table });
    const tableOrders = table.getOrders();
    expect(tableOrders.length).toBe(1);
    expect(tableOrders[0].id).toBe(order.id);
});

test("getParent and isParent", async () => {
    const store = await setupPosEnv();
    const models = store.models;
    const parent = models["restaurant.table"].get(2);
    const child = models["restaurant.table"].get(3);
    child.parent_id = parent;
    const result = child.getParent();
    expect(parent.isParent(child)).toBe(true);
    expect(result.id).toBe(2);
});

test("rootTable", async () => {
    const store = await setupPosEnv();
    const table1 = store.models["restaurant.table"].get(2);
    const table2 = store.models["restaurant.table"].get(3);
    const table3 = store.models["restaurant.table"].get(4);
    table2.parent_id = table1;
    table3.parent_id = table2;
    expect(table3.rootTable.id).toBe(table1.id);
});

test("startDateForDuration: returns the appropriate start date based on fired courses", async () => {
    const store = await setupPosEnv();
    const table = store.models["restaurant.table"].get(2);

    expect(table.startDateForDuration()).toBe(undefined);

    const order = store.addNewOrder({ table_id: table });
    order.create_date = DateTime.now().minus({ hours: 2 });

    expect(table.startDateForDuration()).toEqual(order.create_date);

    const course1 = store.addCourse();
    const course2 = store.addCourse();
    fireCourse(course1, { minutesAgo: 40 });
    fireCourse(course2, { minutesAgo: 20 });

    expect(table.startDateForDuration()).toEqual(course1.fired_date);
});

test("orderDuration: calculates duration from the appropriate start date", async () => {
    const store = await setupPosEnv();
    const table = store.models["restaurant.table"].get(2);

    expect(table.orderDuration()).toBe(false);

    const order = store.addNewOrder({ table_id: table });
    order.create_date = DateTime.now().minus({ minutes: 25 });

    expect(table.orderDuration()).toBe("25'");

    const course = store.addCourse();
    fireCourse(course, { minutesAgo: 90 });

    expect(table.orderDuration()).toBe("1h30'");
});
