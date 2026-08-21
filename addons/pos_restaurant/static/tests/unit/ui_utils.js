import { animationFrame, waitFor, press } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    clickControlButton,
    ensurePane,
    queryEl,
    clickDisplayedProduct,
    clickOrderline,
} from "@point_of_sale/../tests/unit/ui_utils";

export async function clickTable(name) {
    await contains(`.o_fp_canvas .o_fp_table:has(.o_fp_table_number:contains("${name}"))`).click();
    await animationFrame();
}

export async function clickTableById(tableId) {
    await contains(`.o_fp_table[data-table_id='${tableId}']`).click();
    await animationFrame();
}

export async function clickFloor(name) {
    await contains(`.floor-selector .button-floor:contains("${name}")`).click();
    await animationFrame();
}

export async function clickPlanButton() {
    await contains(".table-button").click();
    await animationFrame();
}

export async function clickCourseButton() {
    await ensurePane("left");
    await clickControlButton("Course");
    await animationFrame();
}

export async function clickFireCourseButton() {
    await ensurePane("left");
    await contains(".actionpad .fire-btn").click();
    await animationFrame();
}

export async function clickTransferButton() {
    await clickControlButton("Transfer");
    await animationFrame();
}

export async function setGuestCount(count) {
    await clickControlButton("Guest");
    await waitFor(".modal .numpad");
    for (const d of count.toString().split("")) {
        await contains(`.modal .numpad button:contains("${d}")`).click();
        await animationFrame();
    }
    await press("Enter");
    await animationFrame();
}

export async function moveOrderlineToCourse(productName, endCourse) {
    await contains(queryEl(".orderline .product-name", productName)).click();
    await animationFrame();
    await clickControlButton("Transfer course");
    await waitFor(".modal");
    await contains(queryEl(".modal-body button", endCourse)).click();
    await animationFrame();
}

export async function createCourseManually() {
    await clickControlButton("Course");
    await animationFrame();
}

export async function createProductCombo() {
    await clickDisplayedProduct("Product combo");
    await waitFor(".modal label.combo-item");
    await contains(
        '.modal label.combo-item article.product:has(.product-name:contains("Wood chair"))'
    ).click();
    await animationFrame();
    await contains(
        '.modal label.combo-item article.product:has(.product-name:contains("Wood desk"))'
    ).click();
    await animationFrame();
    await contains(".modal footer button.confirm").click();
    await animationFrame();
}

export async function breakCombo(comboItem) {
    await clickOrderline(comboItem);
    await animationFrame();
    await clickControlButton("Break Combo");
    await animationFrame();
}

export async function setupPosProductCategoryDefaultCourse(store, productName, courseName) {
    let course = store.models["pos.course"].getAll().find((c) => c.name === courseName);
    if (!course) {
        course = store.models["pos.course"].create({
            name: courseName,
        });
    }

    const product = store.models["product.product"].getAll().find((p) => p.name === productName);
    if (!product) {
        throw new Error(`Produit '${productName}' introuvable.`);
    }

    const category = product.pos_categ_ids[0];
    if (category) {
        category.update({ course_id: course });
    } else {
        throw new Error(`Le produit '${productName}' n'a pas de catégorie POS.`);
    }
}
