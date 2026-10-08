import { expect, test } from "@odoo/hoot";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { makeServerError } from "@web/../tests/web_test_helpers";
import { getChartDefinition, insertChartInSpreadsheet } from "@spreadsheet/../tests/helpers/chart";
import { createSpreadsheetWithList } from "@spreadsheet/../tests/helpers/list";

defineSpreadsheetModels();

test("getLoadedDataSources discards datasources with an invalid model", async () => {
    const { model } = await createModelWithDataSource({
        spreadsheetData: {
            pivots: {
                1: {
                    type: "ODOO",
                    columns: [],
                    domain: [],
                    measures: [],
                    model: "unknown",
                    rows: [],
                    context: {},
                },
            },
            lists: {
                1: {
                    id: 1,
                    columns: [],
                    model: "unknown",
                    orderBy: [],
                },
            },
        },
        mockRPC: async function (route, { model, method, kwargs }) {
            if (model === "unknown" && method === "fields_get") {
                throw makeServerError({ code: 404 });
            }
        },
    });

    const definition = getChartDefinition("odoo_bar");
    definition.metaData.resModel = "unknown";
    insertChartInSpreadsheet(model, "chart1", definition);
    await waitForDataLoaded(model);

    expect(model.getters.getLoadedDataSources()).resolves.toHaveLength(0);
});

test("list source sent to the export log carries its column names", async () => {
    const { model } = await createSpreadsheetWithList({
        columns: ["foo", "bar"],
    });
    const listSources = model.getters.getLoadedDataSources().filter((s) => s.type === "list");
    expect(listSources).toHaveLength(1);
    expect(listSources[0].resModel).toBe("partner");
    expect(listSources[0].fields).toEqual(["id", "foo", "bar"]);
});
