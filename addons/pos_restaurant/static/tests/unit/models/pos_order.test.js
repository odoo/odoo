import { test, describe, expect } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

describe("pos.order restaurant patches", () => {
    test("customer count and amount per guest", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        order.setCustomerCount(3);
        expect(order.getCustomerCount()).toBe(3);
        order.setCustomerCount(4);
        expect(order.amountPerGuest()).toBe(4.4625);
    });

    test("isDirectSale", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        expect(order.isDirectSale).toBe(true);
    });

    test("setPartner", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        const partner = store.models["res.partner"].get(18);
        order.setPartner(partner);
        expect(order.floating_order_name).toBe("Public user");
    });

    test("cleanCourses", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const course1 = store.addCourse();
        const line = order.lines[0];
        line.course_id = course1;
        const course2 = store.addCourse();
        course1.fired = true;
        order.cleanCourses();
        expect(order.course_ids.includes(course2)).toBe(false);
        expect(order.course_ids.includes(course1)).toBe(true);
    });

    test("getNextCourseIndex", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        store.addCourse();
        store.addCourse();
        expect(order.getNextCourseIndex()).toBe(4);
    });

    test("getName returns formatted name for table + children", async () => {
        const store = await setupPosEnv();
        const table = store.models["restaurant.table"].get(2);
        const order = store.addNewOrder({ table_id: table });
        const child = store.models["restaurant.table"].get(3);
        let name = order.getName();
        expect(name).toBe("T 1");
        child.parent_id = table;
        name = order.getName();
        expect(name).toBe("T 1 & 2");
    });

    test("ensureCourseSelection and getSelectedCourse", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        const course1 = store.addCourse();
        course1.fired = false;
        const course2 = store.addCourse();
        course2.fired = true;
        order.ensureCourseSelection();
        expect(order.getSelectedCourse().uuid).toBe(course1.uuid);
    });
});
