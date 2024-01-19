import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { describe, expect, test } from "@odoo/hoot";
import { setCellContent } from "@spreadsheet/../tests/helpers/commands";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { getEvaluatedCell } from "@spreadsheet/../tests/helpers/getters";
import {
    defineSpreadsheetAccountModels,
} from "@spreadsheet_account/../tests/accounting_test_data";

import { waitForDataLoaded } from "@spreadsheet/helpers/model";

describe.current.tags("headless");
defineSpreadsheetModels();
defineSpreadsheetAccountModels();

test("Basic evaluation", async () => {
    const model = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "get_residual_amount") {
                expect.step("get_residual_amount");
                expect(args.args).toEqual([
                    [
                        {
                            codes: [
                                "112",
                            ],
                            date_from: {
                                range_type: "year",
                                year: 2023,
                            },
                            date_to: {
                                range_type: "year",
                                year: 2023,
                            },
                            company_id: 0,
                            include_unposted: false,
                        }
                    ],
                ]);
                return [111.11];
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.RESIDUAL("112", 2023)`);
    await waitForDataLoaded(model);
    expect.verifySteps(["get_residual_amount"]);
    expect(getEvaluatedCell(model, "A1").value).toBe(111.11);
});

test("with wrong date format", async () => {
    const model = await createModelWithDataSource();
    setCellContent(model, "A1", `=ODOO.RESIDUAL("112", "This is not a valid date")`);
    await waitForDataLoaded(model);
    expect(getEvaluatedCell(model, "A1").message).toBe(
        "'This is not a valid date' is not a valid period. Supported formats are \"21/12/2022\", \"Q1/2022\", \"12/2022\", and \"2022\"."
    );
});

test("with no date", async () => {
    const d = new Date();
    const model = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "get_residual_amount") {
                expect.step("get_residual_amount");
                expect(args.args).toEqual([
                    [
                        {
                            codes: [
                                "112",
                            ],
                            date_from: {
                                range_type: "year",
                                year: d.getFullYear(),
                            },
                            date_to: {
                                range_type: "year",
                                year: d.getFullYear(),
                            },
                            company_id: 0,
                            include_unposted: false,
                        }
                    ],
                ]);
                return [111.11];
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.RESIDUAL("112")`);
    await waitForDataLoaded(model);
    expect.verifySteps(["get_residual_amount"]);
    expect(getEvaluatedCell(model, "A1").value).toBe(111.11);
});
