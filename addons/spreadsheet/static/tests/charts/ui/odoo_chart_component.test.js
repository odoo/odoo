import { animationFrame } from "@odoo/hoot-mock";
import { expect, test } from "@odoo/hoot";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { createBasicChart, updateChart } from "@spreadsheet/../tests/helpers/commands";
import { createModelAndMountSpreadsheet } from "@spreadsheet/../tests/helpers/ui";

defineSpreadsheetModels();

/**
 * @typedef {import("@spreadsheet/../tests/helpers/data").ServerData} ServerData
 */

const chartId = "uuid1";

test("info icon is on the chart when it has an annotation", async function () {
    const { model, fixture } = await createModelAndMountSpreadsheet();
    createBasicChart(model, chartId);
    updateChart(model, chartId, {
        annotationText: "test",
    });
    await animationFrame();
    const infoIcon = fixture.querySelector(".o-chart-menu-item[data-id='chartInfo']");
    expect(infoIcon).not.toBe(null);
});
