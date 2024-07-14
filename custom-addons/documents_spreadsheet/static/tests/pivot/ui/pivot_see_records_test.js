/** @odoo-module */
import { click, nextTick, getFixture } from "@web/../tests/helpers/utils";

import { selectCell } from "@spreadsheet/../tests/utils/commands";

import * as spreadsheet from "@odoo/o-spreadsheet";
import { getBasicData, getBasicServerData } from "@spreadsheet/../tests/utils/data";
import { createSpreadsheetFromPivotView } from "../../utils/pivot_helpers";

const { Model } = spreadsheet;
const { cellMenuRegistry } = spreadsheet.registries;

QUnit.module("documents_spreadsheet > see pivot records UI");

QUnit.test("Can see records and go back after a pivot insertion", async function (assert) {
    const m = new Model();
    const models = getBasicData();
    models["documents.document"].records = [
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
    await nextTick();
    assert.containsNone(getFixture(), ".o-spreadsheet");
    await click(document.body.querySelector(".o_back_button"));
    await nextTick();
    assert.containsOnce(getFixture(), ".o-spreadsheet");
});
