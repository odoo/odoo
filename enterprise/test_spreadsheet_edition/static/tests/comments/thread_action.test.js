import { expect, test } from "@odoo/hoot";
import { helpers } from "@odoo/o-spreadsheet";
import { defineTestSpreadsheetEditionModels, getDummyBasicServerData } from "@test_spreadsheet_edition/../tests/helpers/data";
import { createSpreadsheetTestAction } from "@test_spreadsheet_edition/../tests/helpers/helpers";

const { toCartesian } = helpers;

defineTestSpreadsheetEditionModels();

test("Load the action with valid thread Id", async () => {
    const spreadsheetId = 1;
    const threadId = 1;
    const workbookdata = {
        sheets: [{ comments: { Z100: [{ threadId, isResolved: false }] } }],
    };
    const serverData = getDummyBasicServerData();
    serverData.models["spreadsheet.test"].records = [
        {
            name: "Untitled Dummy Spreadsheet",
            spreadsheet_data: JSON.stringify(workbookdata),
            id: spreadsheetId,
        },
    ];
    serverData.models["spreadsheet.cell.thread"].records = [{ id: threadId, dummy_id: spreadsheetId }];
    const { model } = await createSpreadsheetTestAction("spreadsheet_test_action", {
        serverData,
        spreadsheetId,
        threadId,
    });
    const sheetId = model.getters.getActiveSheetId();
    expect(model.getters.getActivePosition()).toEqual({ sheetId, ...toCartesian("Z100") });
});

test("Load the action with invalid thread Id", async () => {
    const spreadsheetId = 1;
    const threadId = 1;
    const workbookdata = { sheets: [{ comments: { Z100: [threadId] } }] };
    const serverData = getDummyBasicServerData();
    serverData.models["spreadsheet.test"].records = [
        {
            name: "Untitled Dummy Spreadsheet",
            spreadsheet_data: JSON.stringify(workbookdata),
            id: spreadsheetId,
        },
    ];
    serverData.models["spreadsheet.cell.thread"].records = [{ id: threadId, dummy_id: spreadsheetId }];
    const { model } = await createSpreadsheetTestAction("spreadsheet_test_action", {
        serverData,
        spreadsheetId,
        threadId: "invalidId",
    });
    const sheetId = model.getters.getActiveSheetId();
    expect(model.getters.getActivePosition()).toEqual({ sheetId, ...toCartesian("A1") });
});
