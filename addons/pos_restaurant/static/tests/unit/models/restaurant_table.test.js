import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

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

test("getParentSide", async () => {
    const store = await setupPosEnv();
    const models = store.models;
    const parent = models["restaurant.table"].get(2);
    const child = models["restaurant.table"].get(3);
    child.parent_id = parent;
    child.position_h = parent.position_h + 50;
    child.position_v = parent.position_v;
    const side = child.getParentSide();
    expect(side).toBe("left");
});

test("getX and getY", async () => {
    const store = await setupPosEnv();
    const table1 = store.models["restaurant.table"].get(2);
    const table2 = store.models["restaurant.table"].get(3);
    expect(table1.getX()).toBe(407);
    expect(table1.getY()).toBe(88);
    table2.parent_id = table1;
    table2.parent_side = "left";
    expect(table2.getX()).toBe(497);
    expect(table2.getY()).toBe(88);
    table2.parent_side = "top";
    expect(table2.getX()).toBe(407);
    expect(table2.getY()).toBe(-2);
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
