import { describe, expect, test } from "@odoo/hoot";
import { runAllTimers } from "@odoo/hoot-dom";
import { setupAndMountPosApp } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import * as PosUiUtils from "@point_of_sale/../tests/unit/ui_utils";
import * as ResUiUtils from "@pos_restaurant/../tests/unit/ui_utils";

const Utils = { ...PosUiUtils, ...ResUiUtils };

definePosModels();

async function setupCourseComboTest() {
    await Utils.clickTable("1");
    await Utils.createCourseManually();
    await Utils.createCourseManually();
    await Utils.createCourseManually();
    await Utils.createProductCombo();
}

describe("Combo works perfectly with courses", () => {
    const comboLabel = "Product combo";
    const chairLabel = "Wood chair";
    const deskLabel = "Wood desk";
    const includedLabel = "Included";
    const course2Label = "Course 2";
    const course3Label = "Course 3";
    const startLabel = "Starter";

    describe("Without auto allocation", () => {
        test("test_combo_moves_accros_courses: course transfer (child, last child, then parent)", async () => {
            const store = await setupAndMountPosApp();
            await setupCourseComboTest();

            const order = store.getOrder();
            const parentLine = order.lines.find((l) => l.combo_line_ids?.length > 0);
            const chairLine = order.lines.find(
                (l) => l.combo_parent_id && l.product_id?.name === chairLabel
            );
            const deskLine = order.lines.find(
                (l) => l.combo_parent_id && l.product_id?.name === deskLabel
            );
            expect(Utils.getOrderlineText(chairLabel)).not.toInclude(includedLabel);
            expect(Utils.getOrderlineText(deskLabel)).not.toInclude(includedLabel);

            // Move a Children
            await Utils.moveOrderlineToCourse(chairLabel, course2Label);
            expect(chairLine.course_id?.name).toBe(course2Label);
            expect(parentLine.course_id?.name).not.toBe(course2Label);
            expect(deskLine.course_id?.name).not.toBe(course2Label);
            expect(parentLine.course_id?.id).toBe(deskLine.course_id?.id);
            expect(Utils.getOrderlineText(chairLabel)).toInclude(includedLabel);

            // Move Last Children
            await Utils.moveOrderlineToCourse(deskLabel, course3Label);
            expect(deskLine.course_id?.name).toBe(course3Label);
            expect(chairLine.course_id?.name).toBe(course2Label);
            expect(parentLine.course_id?.name).toBe(course3Label); // Parent also moves when there is no children remaining
            expect(Utils.getOrderlineText(chairLabel)).toInclude(includedLabel);
            expect(Utils.getOrderlineText(deskLabel)).not.toInclude(includedLabel);

            // Move Last Children in the same course as the other children
            await Utils.moveOrderlineToCourse(deskLabel, course2Label);
            expect(deskLine.course_id?.name).toBe(course2Label);
            expect(chairLine.course_id?.name).toBe(course2Label);
            expect(parentLine.course_id?.name).toBe(course2Label);
            expect(Utils.getOrderlineText(chairLabel)).not.toInclude(includedLabel);
            expect(Utils.getOrderlineText(deskLabel)).not.toInclude(includedLabel);

            // Move Parent
            await Utils.moveOrderlineToCourse(comboLabel, course3Label);
            expect(parentLine.course_id?.name).toBe(course3Label);
            expect(chairLine.course_id?.name).toBe(course3Label);
            expect(deskLine.course_id?.name).toBe(course3Label);
            expect(Utils.getOrderlineText(chairLabel)).not.toInclude(includedLabel);
            expect(Utils.getOrderlineText(deskLabel)).not.toInclude(includedLabel);
        });

        test("test_delete_a_child_parent_too: when deleting a child, it deletes the other combo components too", async () => {
            const store = await setupAndMountPosApp();
            await setupCourseComboTest();

            const order = store.getOrder();
            expect(order.lines.length).toBe(3);

            await Utils.deleteOrderline(chairLabel);
            await runAllTimers();

            expect(order.lines.length).toBe(0);
        });

        test("test_breaking_combo_tidy_everything_up: when breaking a combo, separated children get their prices back", async () => {
            const store = await setupAndMountPosApp();
            await setupCourseComboTest();

            const order = store.getOrder();
            const chairLine = order.lines.find(
                (l) => l.combo_parent_id && l.product_id?.name === chairLabel
            );
            const deskLine = order.lines.find(
                (l) => l.combo_parent_id && l.product_id?.name === deskLabel
            );

            await Utils.moveOrderlineToCourse(chairLabel, course2Label);
            expect(Utils.getOrderlineText(chairLabel)).toInclude(includedLabel);

            await Utils.breakCombo(comboLabel);

            expect(chairLine.combo_parent_id).toBeEmpty();
            expect(deskLine.combo_parent_id).toBeEmpty();
            expect(Utils.getOrderlineText(chairLabel)).not.toInclude(includedLabel);
            expect(Utils.getOrderlineText(deskLabel)).not.toInclude(includedLabel);
        });
    });

    describe("With auto allocation", () => {
        test("test_add_combo_with_course_allocation: children with same pos_category_default_course in the same course", async () => {
            const store = await setupAndMountPosApp({ use_course_allocation: true });
            await Utils.setupPosProductCategoryDefaultCourse(store, chairLabel, startLabel);
            await Utils.setupPosProductCategoryDefaultCourse(store, deskLabel, startLabel);

            await Utils.clickTable("1");
            await Utils.createProductCombo();

            const order = store.getOrder();
            const chairLine = order.lines.find((l) => l.product_id?.name === chairLabel);
            const deskLine = order.lines.find((l) => l.product_id?.name === deskLabel);

            expect(chairLine.course_id).not.toBe(false);
            expect(deskLine.course_id).not.toBe(false);
            expect(chairLine.course_id?.id).toBe(deskLine.course_id?.id);
            expect(chairLine.course_id?.name).toBe(startLabel);
        });
    });
});
