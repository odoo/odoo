import {
    defineDocumentSpreadsheetModels,
    getBasicServerData,
} from "@documents_spreadsheet/../tests/helpers/data";
import { expect, test } from "@odoo/hoot";
import { createSpreadsheetTemplate } from "@documents_spreadsheet/../tests/helpers/spreadsheet_test_utils";
import { Model } from "@odoo/o-spreadsheet";
import { setCellContent } from "@spreadsheet/../tests/helpers/commands";
import { getCellValue } from "@spreadsheet/../tests/helpers/getters";

defineDocumentSpreadsheetModels();

test("open template with non Latin characters", async function () {
    const model = new Model();
    setCellContent(model, "A1", "😃");
    const serverData = getBasicServerData();
    serverData.models["spreadsheet.template"].records = [
        {
            id: 99,
            name: "template",
            spreadsheet_data: JSON.stringify(model.exportData()),
        },
    ];
    const { model: template } = await createSpreadsheetTemplate({
        serverData,
        spreadsheetId: 99,
    });
    expect(getCellValue(template, "A1")).toBe("😃", {
        message: "It should show the smiley as a smiley 😉",
    });
});
