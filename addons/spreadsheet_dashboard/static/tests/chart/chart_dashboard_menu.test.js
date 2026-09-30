import { describe, expect, test } from "@odoo/hoot";
import { Model } from "@odoo/o-spreadsheet";
import { insertChartInSpreadsheet } from "@spreadsheet/../tests/helpers/chart";
import { makeSpreadsheetMockEnv } from "@spreadsheet/../tests/helpers/model";
import { OdooDataProvider } from "@spreadsheet/data_sources/odoo_data_provider";
import { createDashboardActionWithData } from "@spreadsheet_dashboard/../tests/helpers/dashboard_action";
import { defineSpreadsheetDashboardModels } from "@spreadsheet_dashboard/../tests/helpers/data";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineSpreadsheetDashboardModels();

test("can change granularity", async () => {
    const env = await makeSpreadsheetMockEnv();
    const setupModel = new Model({}, { custom: { odooDataProvider: new OdooDataProvider(env) } });
    const chartId = insertChartInSpreadsheet(setupModel, "odoo_line", {
        metaData: {
            groupBy: ["date:month"],
            resModel: "partner",
            measure: "__count",
            order: null,
        },
    });
    const { model } = await createDashboardActionWithData(setupModel.exportData());

    expect("select.o-chart-dashboard-item").toHaveValue("month");
    await contains("select.o-chart-dashboard-item", { visible: false }).select("quarter");
    expect(model.getters.getChartGranularity(chartId)).toEqual({
        fieldName: "date",
        granularity: "quarter",
    });
    expect(model.getters.getChartDefinition(chartId).metaData.groupBy).toEqual(["date:quarter"]);
});
