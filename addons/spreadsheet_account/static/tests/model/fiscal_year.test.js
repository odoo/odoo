import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { describe, expect, test } from "@odoo/hoot";
import { setCellContent } from "@spreadsheet/../tests/helpers/commands";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { getEvaluatedCell } from "@spreadsheet/../tests/helpers/getters";
import "@spreadsheet_account/index";

import * as spreadsheet from "@odoo/o-spreadsheet";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";

describe.current.tags("headless");
defineSpreadsheetModels();

const { DEFAULT_LOCALE } = spreadsheet.constants;

test("Basic evaluation", async () => {
    const { model } = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "get_fiscal_dates") {
                expect.step("get_fiscal_dates");
                expect(args.args).toEqual([
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
    await waitForDataLoaded(model);
    expect.verifySteps(["get_fiscal_dates"]);
    expect(getEvaluatedCell(model, "A1").formattedValue).toBe("1/1/2020");
    expect(getEvaluatedCell(model, "A2").formattedValue).toBe("12/31/2020");
});

test("with a given company id", async () => {
    const { model } = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "get_fiscal_dates") {
                expect.step("get_fiscal_dates");
                expect(args.args).toEqual([
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
    await waitForDataLoaded(model);
    expect.verifySteps(["get_fiscal_dates"]);
    expect(getEvaluatedCell(model, "A1").formattedValue).toBe("1/1/2020");
    expect(getEvaluatedCell(model, "A2").formattedValue).toBe("12/31/2020");
});

test("with a wrong company id", async () => {
    const { model } = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "get_fiscal_dates") {
                expect.step("get_fiscal_dates");
                expect(args.args).toEqual([
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
    await waitForDataLoaded(model);
    expect.verifySteps(["get_fiscal_dates"]);
    expect(getEvaluatedCell(model, "A1").message).toBe(
        "The company fiscal year could not be found."
    );
    expect(getEvaluatedCell(model, "A2").message).toBe(
        "The company fiscal year could not be found."
    );
});

test("with wrong input arguments", async () => {
    const { model } = await createModelWithDataSource();
    setCellContent(model, "A1", `=ODOO.FISCALYEAR.START("not a number")`);
    setCellContent(model, "A2", `=ODOO.FISCALYEAR.END("11/11/2020", "not a number")`);
    expect(getEvaluatedCell(model, "A1").message).toBe(
        "The function ODOO.FISCALYEAR.START expects a number value, but 'not a number' is a string, and cannot be coerced to a number."
    );
    expect(getEvaluatedCell(model, "A2").message).toBe(
        "The function ODOO.FISCALYEAR.END expects a number value, but 'not a number' is a string, and cannot be coerced to a number."
    );
});

test("Date format is locale dependant", async () => {
    const { model } = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "get_fiscal_dates") {
                return [{ start: "2020-01-01", end: "2020-12-31" }];
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.FISCALYEAR.START("11/11/2020", 1)`);
    setCellContent(model, "A2", `=ODOO.FISCALYEAR.END("11/11/2020", 1)`);
    await waitForDataLoaded(model);

    expect(getEvaluatedCell(model, "A1").format).toBe("m/d/yyyy");
    expect(getEvaluatedCell(model, "A2").format).toBe("m/d/yyyy");

    model.dispatch("UPDATE_LOCALE", { locale: { ...DEFAULT_LOCALE, dateFormat: "d/m/yyyy" } });

    expect(getEvaluatedCell(model, "A1").format).toBe("d/m/yyyy");
    expect(getEvaluatedCell(model, "A2").format).toBe("d/m/yyyy");
});
