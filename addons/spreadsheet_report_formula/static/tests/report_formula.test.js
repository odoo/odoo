import { describe, expect, test } from "@odoo/hoot";
import { setCellContent } from "@spreadsheet/../tests/helpers/commands";
import { defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { getCellValue, getEvaluatedCell } from "@spreadsheet/../tests/helpers/getters";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";

describe.current.tags("headless");
defineSpreadsheetModels();

test("ODOO.REPORT sends the report, line, column and period it names", async () => {
    const requests = [];
    const { model } = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "spreadsheet_fetch_report_values") {
                requests.push(...args.args[0]);
                return args.args[0].map((request) => ({
                    value: request.line_code === "NEP" ? 1200 : 300,
                }));
            }
        },
    });
    setCellContent(
        model,
        "A1",
        `=ODOO.REPORT("account.profit_and_loss", "NEP", "balance", "2022")`,
    );
    setCellContent(
        model,
        "A2",
        `=ODOO.REPORT("7", "REV", "balance", "Q2/2022", -1, 3, TRUE)`,
    );
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A1")).toBe(1200);
    expect(getCellValue(model, "A2")).toBe(300);
    expect(requests).toEqual([
        {
            report: "account.profit_and_loss",
            line_code: "NEP",
            label: "balance",
            date_range: { range_type: "year", year: 2022 },
            company_id: null,
            include_unposted: false,
        },
        {
            report: 7,
            line_code: "REV",
            label: "balance",
            date_range: { range_type: "quarter", year: 2021, quarter: 2 },
            company_id: 3,
            include_unposted: true,
        },
    ]);
});

test("a line the report does not have is an evaluation error", async () => {
    const { model } = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "spreadsheet_fetch_report_values") {
                return [false];
            }
        },
    });
    setCellContent(
        model,
        "A1",
        `=ODOO.REPORT("account.profit_and_loss", "NOPE", "balance", "2022")`,
    );
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A1")).toBe("#ERROR");
    expect(getEvaluatedCell(model, "A1").message).toBe(
        "Report account.profit_and_loss has no line NOPE with a column balance.",
    );
});
