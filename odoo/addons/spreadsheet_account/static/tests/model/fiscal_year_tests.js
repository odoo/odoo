/** @odoo-module */
import { setCellContent } from "@spreadsheet/../tests/utils/commands";
import {
    createModelWithDataSource,
    waitForDataSourcesLoaded,
} from "@spreadsheet/../tests/utils/model";
import { getEvaluatedCell } from "@spreadsheet/../tests/utils/getters";
import "@spreadsheet_account/index";

import * as spreadsheet from "@odoo/o-spreadsheet";
const { DEFAULT_LOCALE } = spreadsheet.constants;

QUnit.module("spreadsheet_account > fiscal year", {}, () => {
    QUnit.test("Basic evaluation", async (assert) => {
        const model = await createModelWithDataSource({
            mockRPC: async function (route, args) {
                if (args.method === "get_fiscal_dates") {
                    assert.step("get_fiscal_dates");
                    assert.deepEqual(args.args, [
                        [
                            {
                                date: "2020-11-11",
                                company_id: null,
                            },
                        ],
                    ]);
                    return [{ start: "2020-01-01", end: "2020-12-31" }];
                }
            },
        });
        setCellContent(model, "A1", `=ODOO.FISCALYEAR.START("11/11/2020")`);
        setCellContent(model, "A2", `=ODOO.FISCALYEAR.END("11/11/2020")`);
        await waitForDataSourcesLoaded(model);
        assert.verifySteps(["get_fiscal_dates"]);
        assert.equal(getEvaluatedCell(model, "A1").formattedValue, "1/1/2020");
        assert.equal(getEvaluatedCell(model, "A2").formattedValue, "12/31/2020");
    });

    QUnit.test("with a given company id", async (assert) => {
        const model = await createModelWithDataSource({
            mockRPC: async function (route, args) {
                if (args.method === "get_fiscal_dates") {
                    assert.step("get_fiscal_dates");
                    assert.deepEqual(args.args, [
                        [
                            {
                                date: "2020-11-11",
                                company_id: 1,
                            },
                        ],
                    ]);
                    return [{ start: "2020-01-01", end: "2020-12-31" }];
                }
            },
        });
        setCellContent(model, "A1", `=ODOO.FISCALYEAR.START("11/11/2020", 1)`);
        setCellContent(model, "A2", `=ODOO.FISCALYEAR.END("11/11/2020", 1)`);
        await waitForDataSourcesLoaded(model);
        assert.verifySteps(["get_fiscal_dates"]);
        assert.equal(getEvaluatedCell(model, "A1").formattedValue, "1/1/2020");
        assert.equal(getEvaluatedCell(model, "A2").formattedValue, "12/31/2020");
    });

    QUnit.test("with a wrong company id", async (assert) => {
        const model = await createModelWithDataSource({
            mockRPC: async function (route, args) {
                if (args.method === "get_fiscal_dates") {
                    assert.step("get_fiscal_dates");
                    assert.deepEqual(args.args, [
                        [
                            {
                                date: "2020-11-11",
                                company_id: 100,
                            },
                        ],
                    ]);
                    return [false];
                }
            },
        });
        setCellContent(model, "A1", `=ODOO.FISCALYEAR.START("11/11/2020", 100)`);
        setCellContent(model, "A2", `=ODOO.FISCALYEAR.END("11/11/2020", 100)`);
        await waitForDataSourcesLoaded(model);
        assert.verifySteps(["get_fiscal_dates"]);
        assert.equal(
            getEvaluatedCell(model, "A1").error.message,
            "The company fiscal year could not be found."
        );
        assert.equal(
            getEvaluatedCell(model, "A2").error.message,
            "The company fiscal year could not be found."
        );
    });

    QUnit.test("with wrong input arguments", async (assert) => {
        const model = await createModelWithDataSource();
        setCellContent(model, "A1", `=ODOO.FISCALYEAR.START("not a number")`);
        setCellContent(model, "A2", `=ODOO.FISCALYEAR.END("11/11/2020", "not a number")`);
        assert.equal(
            getEvaluatedCell(model, "A1").error.message,
            "The function ODOO.FISCALYEAR.START expects a number value, but 'not a number' is a string, and cannot be coerced to a number."
        );
        assert.equal(
            getEvaluatedCell(model, "A2").error.message,
            "The function ODOO.FISCALYEAR.END expects a number value, but 'not a number' is a string, and cannot be coerced to a number."
        );
    });

    QUnit.test("Date format is locale dependant", async (assert) => {
        const model = await createModelWithDataSource({
            mockRPC: async function (route, args) {
                if (args.method === "get_fiscal_dates") {
                    return [{ start: "2020-01-01", end: "2020-12-31" }];
                }
            },
        });
        setCellContent(model, "A1", `=ODOO.FISCALYEAR.START("11/11/2020", 1)`);
        setCellContent(model, "A2", `=ODOO.FISCALYEAR.END("11/11/2020", 1)`);
        await waitForDataSourcesLoaded(model);

        assert.equal(getEvaluatedCell(model, "A1").format, "m/d/yyyy");
        assert.equal(getEvaluatedCell(model, "A2").format, "m/d/yyyy");

        model.dispatch("UPDATE_LOCALE", { locale: { ...DEFAULT_LOCALE, dateFormat: "d/m/yyyy" } });

        assert.equal(getEvaluatedCell(model, "A1").format, "d/m/yyyy");
        assert.equal(getEvaluatedCell(model, "A2").format, "d/m/yyyy");
    });
});
