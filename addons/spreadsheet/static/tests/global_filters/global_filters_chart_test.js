/** @odoo-module */

import { createSpreadsheetWithGraph } from "../utils/chart";
import { addGlobalFilter } from "../utils/commands";

async function addChartGlobalFilter(model) {
    const chartId = model.getters.getChartIds(model.getters.getActiveSheetId())[0];
    const filter = {
        id: "42",
        type: "date",
        label: "Last Year",
        rangeType: "year",
        defaultValue: { yearOffset: -1 },
        graphFields: { [chartId]: { field: "date", type: "date" } },
    };
    await addGlobalFilter(model, { filter });
}

QUnit.module("spreadsheet > Global filters chart", {}, () => {
    QUnit.test("Can add a chart global filter", async function (assert) {
        const { model } = await createSpreadsheetWithGraph();
        assert.equal(model.getters.getGlobalFilters().length, 0);
        await addChartGlobalFilter(model);
        assert.equal(model.getters.getGlobalFilters().length, 1);
        const chartId = model.getters.getChartIds(model.getters.getActiveSheetId())[0];
        const computedDomain = model.getters.getGraphDataSource(chartId).getComputedDomain();
        assert.equal(computedDomain.length, 3);
        assert.equal(computedDomain[0], "&");
    });

    QUnit.test("Chart is loaded with computed domain", async function (assert) {
        assert.expect(3);

        const { model } = await createSpreadsheetWithGraph({
            mockRPC: function (route, { model, method, kwargs }) {
                if (model === "partner" && method === "web_read_group") {
                    assert.strictEqual(kwargs.domain.length, 3);
                    assert.strictEqual(kwargs.domain[0], "&");
                    assert.strictEqual(kwargs.domain[1][0], "date");
                }
            },
        });
        await addChartGlobalFilter(model);
    });
});
