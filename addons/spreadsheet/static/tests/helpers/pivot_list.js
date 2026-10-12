import { animationFrame } from "@odoo/hoot-mock";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/helpers/pivot";
import { insertListInSpreadsheet } from "@spreadsheet/../tests/helpers/list";

export async function createSpreadsheetWithPivotAndList(params) {
    const { model, env } = await createSpreadsheetWithPivot(params);
    insertListInSpreadsheet(model, {
        model: "partner",
        columns: [
            { name: "foo", string: "Foo" },
            { name: "bar", string: "Bar" },
            { name: "date", string: "Date" },
            { name: "product_id", string: "Product" },
        ],
    });
    await animationFrame();
    return { env, model };
}
