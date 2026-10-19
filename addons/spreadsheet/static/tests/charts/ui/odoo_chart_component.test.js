import { animationFrame } from "@odoo/hoot-mock";
import { expect, test } from "@odoo/hoot";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { createBasicChart, updateChart } from "@spreadsheet/../tests/helpers/commands";
import { mountSpreadsheet } from "@spreadsheet/../tests/helpers/ui";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";

defineSpreadsheetModels();

/**
 * @typedef {import("@spreadsheet/../tests/helpers/data").ServerData} ServerData
 */

const chartId = "uuid1";
const serverData = /** @type {ServerData} */ ({});

test("info icon is on the chart when it has an annotation", async function () {
    const { model } = await createModelWithDataSource({
        serverData,
    });
    const fixture = await mountSpreadsheet(model);
    createBasicChart(model, chartId);
    updateChart(model, chartId, {
        annotationText: "test",
    });
    await animationFrame();
    const infoIcon = fixture.querySelector(".o-chart-menu-item[data-id='chartInfo']");
    expect(infoIcon).not.toBe(null);
});
