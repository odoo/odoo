import {
    defineDocumentSpreadsheetModels,
    DocumentsDocument,
    getBasicData,
    getBasicServerData,
} from "@documents_spreadsheet/../tests/helpers/data";
import { createSpreadsheetFromPivotView } from "@documents_spreadsheet/../tests/helpers/pivot_helpers";
import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { selectCell } from "@spreadsheet/../tests/helpers/commands";
import { contains } from "@web/../tests/web_test_helpers";
const { Model } = spreadsheet;
const { cellMenuRegistry } = spreadsheet.registries;

defineDocumentSpreadsheetModels();

test("Can see records and go back after a pivot insertion", async function () {
    const m = new Model();
    const models = getBasicData();
    models["documents.document"].records = [
        DocumentsDocument._records[0], // res_company.document_spreadsheet_folder_id
        {
            spreadsheet_data: JSON.stringify(m.exportData()),
            name: "a spreadsheet",
            folder_id: 1,
            handler: "spreadsheet",
            id: 456,
            is_favorited: false,
        },
    ];
    const serverData = {
        models: models,
        views: getBasicServerData().views,
    };
    const { model, env } = await createSpreadsheetFromPivotView({
        documentId: 456,
        serverData,
    });
    // Go the the list view and go back, a third pivot should not be opened
    selectCell(model, "B3");
    const root = cellMenuRegistry.getAll().find((item) => item.id === "pivot_see_records");
    await root.execute(env);
    await animationFrame();
    expect(".o-spreadsheet").toHaveCount(0);
    await contains(document.body.querySelector(".o_back_button")).click();
    await animationFrame();
    expect(".o-spreadsheet").toHaveCount(1);
});
