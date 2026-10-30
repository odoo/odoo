import { test, expect } from "@odoo/hoot";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { fireCourse } from "@pos_restaurant/../tests/unit/data/pos_course.data";

definePosModels();

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

test("isSynced", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();
    const course = store.addCourse();
    expect(course.isSynced).toBe(false);
});

test("isLive: is true only for the last fired course", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    const course1 = store.addCourse();
    const course2 = store.addCourse();
    const course3 = store.addCourse();
    fireCourse(course1, { minutesAgo: 30 });
    fireCourse(course2, { minutesAgo: 10 });
    fireCourse(course3, { minutesAgo: 20 });

    expect(course1.isLive).toBe(false);
    expect(course2.isLive).toBe(true);
    expect(course3.isLive).toBe(false);
});

test("getDuration: calculates and formats duration for fired courses", async () => {
    const store = await setupPosEnv();
    store.addNewOrder();

    const course1 = store.addCourse();
    const course2 = store.addCourse();
    const course3 = store.addCourse();
    expect(course1.getDuration()).toBe(false);

    fireCourse(course1, { minutesAgo: 90 });
    fireCourse(course2, { minutesAgo: 15 });

    expect(course1.getDuration()).toBe("1h15'");
    expect(course2.getDuration()).toBe("15'");
    expect(course3.getDuration()).toBe(false);
});
