import { test, describe, expect } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

describe("restaurant.order.course", () => {
    test("name returns localized name with index", async () => {
        const store = await setupPosEnv();
        store.addNewOrder();
        const course = store.addCourse();
        expect(course.name).toBe("Course 1");
    });

    test("isSelected", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        const course = store.addCourse();
        order.selectCourse(course);
        expect(course.isSelected()).toBe(true);
    });

    test("isEmpty", async () => {
        const store = await setupPosEnv();
        store.addNewOrder();
        const course = store.addCourse();
        course.line_ids = [];
        expect(course.isEmpty()).toBe(true);
    });

    test("isReadyToFire", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const course = store.addCourse();
        const line = order.lines[0];
        line.course_id = course;
        course.line_ids = [line];
        expect(course.isReadyToFire()).toBe(true);
    });

    test("isNew", async () => {
        const store = await setupPosEnv();
        store.addNewOrder();
        const course = store.addCourse();
        expect(course.isNew()).toBe(true);
    });
});
