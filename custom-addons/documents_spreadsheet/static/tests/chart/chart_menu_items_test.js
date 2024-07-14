/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";
const { topbarMenuRegistry } = spreadsheet.registries;

import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { createSpreadsheetFromGraphView } from "../utils/chart_helpers";
import { GraphRenderer } from "@web/views/graph/graph_renderer";
import { patchGraphSpreadsheet } from "@spreadsheet_edition/assets/graph_view/graph_view";
import { doMenuAction } from "@spreadsheet/../tests/utils/ui";

QUnit.module(
    "documents_spreadsheet > Odoo Chart Menu Items",
    {
        beforeEach: function () {
            patchWithCleanup(GraphRenderer.prototype, patchGraphSpreadsheet());
        },
    },
    function () {
        QUnit.test(
            "Verify presence of chart in top menu bar in a spreadsheet with a chart",
            async function (assert) {
                const { model, env } = await createSpreadsheetFromGraphView();
                const sheetId = model.getters.getActiveSheetId();
                const chartId = model.getters.getChartIds(sheetId)[0];

                const root = topbarMenuRegistry.getMenuItems().find((item) => item.id === "data");
                const children = root.children(env);
                assert.ok(children.find((c) => c.id === `item_chart_${chartId}`));
            }
        );

        QUnit.test("Chart focus changes on top bar menu click", async function (assert) {
            const { model, env } = await createSpreadsheetFromGraphView();
            const sheetId = model.getters.getActiveSheetId();
            const chartId = model.getters.getChartIds(sheetId)[0];

            env.openSidePanel("ChartPanel");
            assert.notOk(model.getters.getSelectedFigureId(), "No chart should be selected");
            await doMenuAction(topbarMenuRegistry, ["data", `item_chart_${chartId}`], env);
            assert.equal(
                model.getters.getSelectedFigureId(),
                chartId,
                "The selected chart should have id " + chartId
            );
        });
    }
);
