import { describe, expect, test } from "@odoo/hoot";
import { setCellContent } from "@spreadsheet/../tests/helpers/commands";
import { getCellValue, getEvaluatedCell } from "@spreadsheet/../tests/helpers/getters";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { camelToSnakeObject } from "@spreadsheet/helpers/helpers";
import {
    defineSpreadsheetAccountModels,
    getAccountingData,
} from "@spreadsheet_account/../tests/accounting_test_data";
import { parseAccountingDate } from "@spreadsheet_account/accounting_functions";
import { makeServerError } from "@web/../tests/web_test_helpers";
import { sprintf } from "@web/core/utils/strings";

import * as spreadsheet from "@odoo/o-spreadsheet";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";

describe.current.tags("headless");
defineSpreadsheetAccountModels();

const { DEFAULT_LOCALE: locale } = spreadsheet.constants;

const serverData = getAccountingData();

test("Basic evaluation", async () => {
    const model = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "spreadsheet_fetch_debit_credit") {
                expect.step("spreadsheet_fetch_debit_credit");
                return [{ debit: 42, credit: 16 }];
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.CREDIT("100", "2022")`);
    setCellContent(model, "A2", `=ODOO.DEBIT("100", "2022")`);
    setCellContent(model, "A3", `=ODOO.BALANCE("100", "2022")`);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A1")).toBe(16);
    expect(getCellValue(model, "A2")).toBe(42);
    expect(getCellValue(model, "A3")).toBe(26);
    expect.verifySteps(["spreadsheet_fetch_debit_credit"]);
});

test("evaluation with reference to a month period", async () => {
    const model = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "spreadsheet_fetch_debit_credit") {
                expect(args.args[0]).toEqual([
                    {
                        codes: ["100"],
                        company_id: null,
                        date_range: {
                            month: 2,
                            range_type: "month",
                            year: 2022,
                        },
                        include_unposted: false,
                    },
                ]);
                expect.step("spreadsheet_fetch_debit_credit");
                return [{ debit: 42, credit: 16 }];
            }
        },
    });
    setCellContent(model, "B1", "02/2022");
    setCellContent(model, "A1", `=ODOO.CREDIT("100", B1)`);
    setCellContent(model, "A2", `=ODOO.DEBIT("100", B1)`);
    setCellContent(model, "A3", `=ODOO.BALANCE("100", B1)`);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A1")).toBe(16);
    expect(getCellValue(model, "A2")).toBe(42);
    expect(getCellValue(model, "A3")).toBe(26);
    expect(getCellValue(model, "B1")).toBe(44593);
    expect.verifySteps(["spreadsheet_fetch_debit_credit"]);
});

test("Functions are correctly formatted", async () => {
    const model = await createModelWithDataSource();
    setCellContent(model, "A1", `=ODOO.CREDIT("100", "2022")`);
    setCellContent(model, "A2", `=ODOO.DEBIT("100", "2022")`);
    setCellContent(model, "A3", `=ODOO.BALANCE("100", "2022")`);
    await waitForDataLoaded(model);
    expect(getEvaluatedCell(model, "A1").format).toBe("#,##0.00[$€]");
    expect(getEvaluatedCell(model, "A2").format).toBe("#,##0.00[$€]");
    expect(getEvaluatedCell(model, "A3").format).toBe("#,##0.00[$€]");
});

test("Functions with a wrong company id is correctly in error", async () => {
    const model = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "get_company_currency_for_spreadsheet") {
                return false;
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.CREDIT("100", "2022", 0, 123456)`);
    await waitForDataLoaded(model);
    expect(getEvaluatedCell(model, "A1").message).toBe("Currency not available for this company.");
});

test("formula with invalid date", async () => {
    const model = await createModelWithDataSource();
    setCellContent(model, "A1", `=ODOO.CREDIT("100",)`);
    setCellContent(model, "A2", `=ODOO.DEBIT("100", 0)`);
    setCellContent(model, "A3", `=ODOO.BALANCE("100", -1)`);
    setCellContent(model, "A4", `=ODOO.BALANCE("100", "not a valid period")`);
    setCellContent(model, "A5", `=ODOO.BALANCE("100", 1900)`); // this should be ok
    setCellContent(model, "A6", `=ODOO.BALANCE("100", 1900, -1)`);
    setCellContent(model, "A7", `=ODOO.DEBIT("100", 1899)`);
    await waitForDataLoaded(model);
    const errorMessage = `'%s' is not a valid period. Supported formats are "21/12/2022", "Q1/2022", "12/2022", and "2022".`;
    expect(getEvaluatedCell(model, "A1").message).toBe("0 is not a valid year.");
    expect(getEvaluatedCell(model, "A2").message).toBe("0 is not a valid year.");
    expect(getEvaluatedCell(model, "A3").message).toBe("-1 is not a valid year.");
    expect(getEvaluatedCell(model, "A4").message).toBe(sprintf(errorMessage, "not a valid period"));
    expect(getEvaluatedCell(model, "A5").value).toBe(0);
    expect(getEvaluatedCell(model, "A6").message).toBe("1899 is not a valid year.");
    expect(getEvaluatedCell(model, "A7").message).toBe("1899 is not a valid year.");
});

test("Evaluation with multiple account codes", async () => {
    const model = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "spreadsheet_fetch_debit_credit") {
                expect.step("spreadsheet_fetch_debit_credit");
                return [{ debit: 142, credit: 26 }];
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.CREDIT("100,200", "2022")`);
    setCellContent(model, "A2", `=ODOO.DEBIT("100,200", "2022")`);
    setCellContent(model, "A3", `=ODOO.BALANCE("100,200", "2022")`);

    // with spaces
    setCellContent(model, "B1", `=ODOO.CREDIT("100 , 200", "2022")`);
    setCellContent(model, "B2", `=ODOO.DEBIT("100 , 200", "2022")`);
    setCellContent(model, "B3", `=ODOO.BALANCE("100 , 200", "2022")`);

    await waitForDataLoaded(model);
    expect(getCellValue(model, "A1")).toBe(26);
    expect(getCellValue(model, "A2")).toBe(142);
    expect(getCellValue(model, "A3")).toBe(116);

    expect(getCellValue(model, "B1")).toBe(26);
    expect(getCellValue(model, "B2")).toBe(142);
    expect(getCellValue(model, "B3")).toBe(116);
    expect.verifySteps(["spreadsheet_fetch_debit_credit"]);
});

test("Handle error evaluation", async () => {
    const model = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "spreadsheet_fetch_debit_credit") {
                throw makeServerError({ description: "a nasty error" });
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.CREDIT("100", "2022")`);
    await waitForDataLoaded(model);
    const cell = getEvaluatedCell(model, "A1");
    expect(cell.value).toBe("#ERROR");
    expect(cell.message).toBe("a nasty error");
});

test("Server requests", async () => {
    const model = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "spreadsheet_fetch_debit_credit") {
                const blobs = args.args[0];
                for (const blob of blobs) {
                    expect.step(JSON.stringify(blob));
                }
                return new Array(blobs.length).fill({ credit: 0, debit: 0 });
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.BALANCE("100", "2022")`);
    setCellContent(model, "A2", `=ODOO.CREDIT("100", "01/2022")`);
    setCellContent(model, "A3", `=ODOO.DEBIT("100","Q2/2022")`);
    setCellContent(model, "A4", `=ODOO.BALANCE("10", "2021")`);
    setCellContent(model, "A5", `=ODOO.CREDIT("10", "2022", -1)`); // same payload as A4: should only be called once
    setCellContent(model, "A6", `=ODOO.DEBIT("5", "2021", 0, 2)`);
    setCellContent(model, "A7", `=ODOO.DEBIT("5", "05/04/2021", 1)`);
    setCellContent(model, "A8", `=ODOO.BALANCE("5", "2022",,,FALSE)`);
    setCellContent(model, "A9", `=ODOO.BALANCE("100", "05/05/2022",,,TRUE)`);
    setCellContent(model, "A10", `=ODOO.BALANCE(33,2021,-2)`);
    await waitForDataLoaded(model);

    expect.verifySteps([
        JSON.stringify(
            camelToSnakeObject({
                dateRange: parseAccountingDate({ value: "2022" }, locale),
                codes: ["100"],
                companyId: null,
                includeUnposted: false,
            })
        ),
        JSON.stringify(
            camelToSnakeObject({
                dateRange: parseAccountingDate({ value: "01/2022" }, locale),
                codes: ["100"],
                companyId: null,
                includeUnposted: false,
            })
        ),
        JSON.stringify(
            camelToSnakeObject({
                dateRange: parseAccountingDate({ value: "Q2/2022" }, locale),
                codes: ["100"],
                companyId: null,
                includeUnposted: false,
            })
        ),
        JSON.stringify(
            camelToSnakeObject({
                dateRange: parseAccountingDate({ value: "2021" }, locale),
                codes: ["10"],
                companyId: null,
                includeUnposted: false,
            })
        ),
        JSON.stringify(
            camelToSnakeObject({
                dateRange: parseAccountingDate({ value: "2021" }, locale),
                codes: ["5"],
                companyId: 2,
                includeUnposted: false,
            })
        ),
        JSON.stringify(
            camelToSnakeObject({
                dateRange: parseAccountingDate({ value: "05/04/2022" }, locale),
                codes: ["5"],
                companyId: null,
                includeUnposted: false,
            })
        ),
        JSON.stringify(
            camelToSnakeObject({
                dateRange: parseAccountingDate({ value: "2022" }, locale),
                codes: ["5"],
                companyId: null,
                includeUnposted: false,
            })
        ),
        JSON.stringify(
            camelToSnakeObject({
                dateRange: parseAccountingDate({ value: "05/05/2022" }, locale),
                codes: ["100"],
                companyId: null,
                includeUnposted: true,
            })
        ),
        JSON.stringify(
            camelToSnakeObject({
                dateRange: parseAccountingDate({ value: "2019" }, locale),
                codes: ["33"],
                companyId: null,
                includeUnposted: false,
            })
        ),
    ]);
});

test("Server requests with multiple account codes", async () => {
    const model = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "spreadsheet_fetch_debit_credit") {
                expect.step("spreadsheet_fetch_debit_credit");
                const blobs = args.args[0];
                for (const blob of blobs) {
                    expect.step(JSON.stringify(blob));
                }
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.BALANCE("100,200", "2022")`);
    setCellContent(model, "A2", `=ODOO.CREDIT("100,200", "2022")`);
    setCellContent(model, "A3", `=ODOO.DEBIT("100,200","2022")`);
    await waitForDataLoaded(model);

    expect.verifySteps([
        "spreadsheet_fetch_debit_credit",
        JSON.stringify(
            camelToSnakeObject({
                dateRange: parseAccountingDate({ value: "2022"}, locale),
                codes: ["100", "200"],
                companyId: null,
                includeUnposted: false,
            })
        ),
    ]);
});

test("account group formula as input to balance formula", async () => {
    const model = await createModelWithDataSource({
        serverData,
        mockRPC: async function (route, args) {
            if (args.method === "spreadsheet_fetch_debit_credit") {
                expect.step("spreadsheet_fetch_debit_credit");
                const blobs = args.args[0];
                for (const blob of blobs) {
                    expect.step(JSON.stringify(blob));
                }
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.ACCOUNT.GROUP("income")`);
    setCellContent(model, "A2", `=ODOO.BALANCE(A1, 2022)`);
    expect(getCellValue(model, "A1")).toBe("Loading...");
    expect(getCellValue(model, "A2")).toBe("Loading...");
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A1")).toBe("100104,200104");
    expect(getCellValue(model, "A2")).toBe(0);
    expect.verifySteps([
        "spreadsheet_fetch_debit_credit",
        JSON.stringify(
            camelToSnakeObject({
                dateRange: parseAccountingDate({ value: "2022"}, locale),
                codes: ["100104", "200104"],
                companyId: null,
                includeUnposted: false,
            })
        ),
    ]);
});

test("two concurrent requests on different accounts", async () => {
    const model = await createModelWithDataSource({
        serverData,
        mockRPC: async function (route, args) {
            if (args.method === "spreadsheet_fetch_debit_credit") {
                expect.step("spreadsheet_fetch_debit_credit");
                const blobs = args.args[0];
                for (const blob of blobs) {
                    expect.step(JSON.stringify(blob));
                }
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.ACCOUNT.GROUP("income")`);
    setCellContent(model, "A2", `=ODOO.BALANCE(A1, 2022)`); // batched only when A1 resolves
    setCellContent(model, "A3", `=ODOO.BALANCE("100", 2022)`); // batched directly
    expect(getCellValue(model, "A1")).toBe("Loading...");
    expect(getCellValue(model, "A2")).toBe("Loading...");
    expect(getCellValue(model, "A3")).toBe("Loading...");
    // A lot happens within the next tick.
    // Because cells are evaluated given their order in the sheet,
    // A1's request is done first, meaning it's also resolved first, which add A2 to the next batch (synchronously)
    // Only then A3 is resolved. => A2 is batched while A3 is pending
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A1")).toBe("100104,200104");
    expect(getCellValue(model, "A2")).toBe(0);
    expect(getCellValue(model, "A3")).toBe(0);
    expect.verifySteps([
        "spreadsheet_fetch_debit_credit",
        JSON.stringify(
            camelToSnakeObject({
                dateRange: parseAccountingDate({ value: "2022" }, locale),
                codes: ["100"],
                companyId: null,
                includeUnposted: false,
            })
        ),
        "spreadsheet_fetch_debit_credit",
        JSON.stringify(
            camelToSnakeObject({
                dateRange: parseAccountingDate({ value: "2022" }, locale),
                codes: ["100104", "200104"],
                companyId: null,
                includeUnposted: false,
            })
        ),
    ]);
});

test("date with non-standard locale", async () => {
    const model = await createModelWithDataSource({
        mockRPC: async function (route, { method, args }) {
            if (method === "spreadsheet_fetch_debit_credit") {
                expect.step("spreadsheet_fetch_debit_credit");
                expect(args).toEqual([
                    [
                        {
                            codes: ["100"],
                            company_id: null,
                            date_range: {
                                range_type: "day",
                                year: 2002,
                                month: 2,
                                day: 1,
                            },
                            include_unposted: false,
                        },
                    ],
                ]);
                return [{ debit: 142, credit: 26 }];
            }
        },
    });
    const myLocale = { ...locale, dateFormat: "d/mmm/yyyy" };
    model.dispatch("UPDATE_LOCALE", { locale: myLocale });
    setCellContent(model, "A1", "=DATE(2002, 2, 1)");
    setCellContent(model, "A2", "=ODOO.BALANCE(100, A1)");
    setCellContent(model, "A3", "=ODOO.CREDIT(100, A1)");
    setCellContent(model, "A4", "=ODOO.DEBIT(100, A1)");
    await waitForDataLoaded(model);
    expect(getEvaluatedCell(model, "A1").formattedValue).toBe("1/Feb/2002");
    expect(getCellValue(model, "A2")).toBe(116);
    expect(getCellValue(model, "A3")).toBe(26);
    expect(getCellValue(model, "A4")).toBe(142);
    expect.verifySteps(["spreadsheet_fetch_debit_credit"]);
});

test("parseAccountingDate", () => {
    expect(parseAccountingDate({ value: "2022" }, locale)).toEqual({
        rangeType: "year",
        year: 2022,
    });
    expect(parseAccountingDate({ value: "11/10/2022" }, locale)).toEqual({
        rangeType: "day",
        year: 2022,
        month: 11,
        day: 10,
    });
    expect(parseAccountingDate({ value: "10/2022" }, locale)).toEqual({
        rangeType: "month",
        year: 2022,
        month: 10,
    });
    expect(parseAccountingDate({ value: "Q1/2022" }, locale)).toEqual({
        rangeType: "quarter",
        year: 2022,
        quarter: 1,
    });
    expect(parseAccountingDate({ value: "q4/2022" }, locale)).toEqual({
        rangeType: "quarter",
        year: 2022,
        quarter: 4,
    });
    // A number below 3000 is interpreted as a year.
    // It's interpreted as a regular spreadsheet date otherwise
    expect(parseAccountingDate({ value: "3005" }, locale)).toEqual({
        rangeType: "day",
        year: 1908,
        month: 3,
        day: 23,
    });
});
