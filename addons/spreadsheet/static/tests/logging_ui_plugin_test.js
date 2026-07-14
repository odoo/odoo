/** @odoo-module */
import { createModelWithDataSource } from "@spreadsheet/../tests/utils/model";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";
import { makeServerError } from "@web/../tests/helpers/mock_server";
import { getChartDefinition, insertChartInSpreadsheet } from "@spreadsheet/../tests/utils/chart";

QUnit.module("Logging plugin", {}, () => {
    QUnit.test(
        "getLoadedDataSources discards datasources with an invalid model",
        async (assert) => {
            const model = await createModelWithDataSource({
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

            assert.equal(model.getters.getLoadedDataSources().length, 0, "No loaded data sources");
        }
    );
});
