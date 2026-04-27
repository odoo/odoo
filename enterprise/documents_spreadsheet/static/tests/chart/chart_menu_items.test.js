import { createSpreadsheetFromGraphView } from "@documents_spreadsheet/../tests/helpers/chart_helpers";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { defineDocumentSpreadsheetModels } from "@documents_spreadsheet/../tests/helpers/data";
import { doMenuAction } from "@spreadsheet/../tests/helpers/ui";
import { patchGraphSpreadsheet } from "@spreadsheet_edition/assets/graph_view/graph_view";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { GraphRenderer } from "@web/views/graph/graph_renderer";
const { topbarMenuRegistry } = spreadsheet.registries;

defineDocumentSpreadsheetModels();
describe.current.tags("desktop");

beforeEach(() => {
    patchWithCleanup(GraphRenderer.prototype, patchGraphSpreadsheet());
});

test("Verify presence of chart in top menu bar in a spreadsheet with a chart", async function () {
    const { model, env } = await createSpreadsheetFromGraphView();
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];

    const root = topbarMenuRegistry.getMenuItems().find((item) => item.id === "data");
    const children = root.children(env);
    const chartItem = children.find((c) => c.id === `item_chart_${chartId}`);
    expect(chartItem).not.toBe(undefined);
    expect(chartItem.name(env)).toBe("(#1) PartnerGraph");
});

test("Chart focus changes on top bar menu click", async function () {
    const { model, env } = await createSpreadsheetFromGraphView();
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];

    env.openSidePanel("ChartPanel");
    expect(model.getters.getSelectedFigureId()).toBe(null, {
        message: "No chart should be selected",
    });
    await doMenuAction(topbarMenuRegistry, ["data", `item_chart_${chartId}`], env);
    expect(model.getters.getSelectedFigureId()).toBe(chartId, {
        message: "The selected chart should have id " + chartId,
    });
});
