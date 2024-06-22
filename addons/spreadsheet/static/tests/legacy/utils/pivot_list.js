/** @odoo-module */

import { nextTick } from "@web/../tests/helpers/utils";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/legacy/utils/pivot";
import { insertListInSpreadsheet } from "@spreadsheet/../tests/legacy/utils/list";

export async function createSpreadsheetWithPivotAndList() {
    const { model, env } = await createSpreadsheetWithPivot();
    insertListInSpreadsheet(model, {
        model: "partner",
        columns: ["foo", "bar", "date", "product_id"],
    });
    await nextTick();
    return { env, model };
}
