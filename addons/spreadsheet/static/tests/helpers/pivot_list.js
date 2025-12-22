import { animationFrame } from "@odoo/hoot-mock";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/helpers/pivot";
import { insertListInSpreadsheet } from "@spreadsheet/../tests/helpers/list";

export async function createSpreadsheetWithPivotAndList() {
    const { model, env } = await createSpreadsheetWithPivot();
    insertListInSpreadsheet(model, {
        model: "partner",
        columns: ["foo", "bar", "date", "product_id"],
    });
    await animationFrame();
    return { env, model };
}
