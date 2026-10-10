import { animationFrame } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";

export async function clickTable(name) {
    await contains(
        `.o_fp_canvas .o_fp_table:not(.syncing):has(.o_fp_table_number:contains("${name}"))`
    ).click();
    await animationFrame();
}

export async function clickPlanButton() {
    await contains(".table-button").click();
    await animationFrame();
}

export async function clickReprintButton() {
    await contains(".reprint-btn").click();
}
