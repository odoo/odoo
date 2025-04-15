/** @odoo-module */

import { nextTick } from "@web/../tests/helpers/utils";
import { createSpreadsheetWithPivot } from "./pivot";
import { insertListInSpreadsheet } from "./list";

export async function createSpreadsheetWithPivotAndList() {
    const { model, env } = await createSpreadsheetWithPivot();
    insertListInSpreadsheet(model, {
        model: "partner",
        columns: ["foo", "bar", "date", "product_id"],
    });
    await nextTick();
    return { env, model };
}
