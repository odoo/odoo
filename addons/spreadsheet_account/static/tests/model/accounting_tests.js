/** @odoo-module */

import { setCellContent } from "@spreadsheet/../tests/utils/commands";
import {
    createModelWithDataSource,
    waitForDataSourcesLoaded,
} from "@spreadsheet/../tests/utils/model";
import { parseAccountingDate } from "../../src/accounting_functions";
import { getCellValue, getEvaluatedCell } from "@spreadsheet/../tests/utils/getters";
import { getAccountingData } from "../accounting_test_data";
import { camelToSnakeObject } from "@spreadsheet/helpers/helpers";
import { sprintf } from "@web/core/utils/strings";

import * as spreadsheet from "@odoo/o-spreadsheet";
const { DEFAULT_LOCALE: locale } = spreadsheet.constants;

let serverData;

function beforeEach() {
    serverData = getAccountingData();
}

QUnit.module("spreadsheet_account > Accounting", { beforeEach }, () => {
    QUnit.module("Formulas");
    QUnit.test("Basic evaluation", async (assert) => {
        const model = await createModelWithDataSource({
            mockRPC: async function (route, args) {
                if (args.method === "spreadsheet_fetch_debit_credit") {
                    assert.step("spreadsheet_fetch_debit_credit");
                    return [{ debit: 42, credit: 16 }];
                }
            },
        });
        setCellContent(model, "A1", `=ODOO.CREDIT("100", "2022")`);
        setCellContent(model, "A2", `=ODOO.DEBIT("100", "2022")`);
        setCellContent(model, "A3", `=ODOO.BALANCE("100", "2022")`);
        await waitForDataSourcesLoaded(model);
        assert.equal(getCellValue(model, "A1"), 16);
        assert.equal(getCellValue(model, "A2"), 42);
        assert.equal(getCellValue(model, "A3"), 26);
        assert.verifySteps(["spreadsheet_fetch_debit_credit"]);
    });

    QUnit.test("evaluation with reference to a month period", async (assert) => {
        const model = await createModelWithDataSource({
            mockRPC: async function (route, args) {
                if (args.method === "spreadsheet_fetch_debit_credit") {
                    assert.deepEqual(args.args[0], [
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
                    assert.step("spreadsheet_fetch_debit_credit");
                    return [{ debit: 42, credit: 16 }];
                }
            },
        });
        setCellContent(model, "B1", "02/2022");
        setCellContent(model, "A1", `=ODOO.CREDIT("100", B1)`);
        setCellContent(model, "A2", `=ODOO.DEBIT("100", B1)`);
        setCellContent(model, "A3", `=ODOO.BALANCE("100", B1)`);
        await waitForDataSourcesLoaded(model);
        assert.equal(getCellValue(model, "A1"), 16);
        assert.equal(getCellValue(model, "A2"), 42);
        assert.equal(getCellValue(model, "A3"), 26);
        assert.equal(getCellValue(model, "B1"), 44593);
        assert.verifySteps(["spreadsheet_fetch_debit_credit"]);
    });

    QUnit.test("Functions are correctly formatted", async (assert) => {
        const model = await createModelWithDataSource();
        setCellContent(model, "A1", `=ODOO.CREDIT("100", "2022")`);
        setCellContent(model, "A2", `=ODOO.DEBIT("100", "2022")`);
        setCellContent(model, "A3", `=ODOO.BALANCE("100", "2022")`);
        await waitForDataSourcesLoaded(model);
        assert.strictEqual(getEvaluatedCell(model, "A1").format, "#,##0.00[$€]");
        assert.strictEqual(getEvaluatedCell(model, "A2").format, "#,##0.00[$€]");
        assert.strictEqual(getEvaluatedCell(model, "A3").format, "#,##0.00[$€]");
    });

    QUnit.test("Functions with a wrong company id is correctly in error", async (assert) => {
        const model = await createModelWithDataSource({
            mockRPC: async function (route, args) {
                if (args.method === "get_company_currency_for_spreadsheet") {
                    return false;
                }
            },
        });
        setCellContent(model, "A1", `=ODOO.CREDIT("100", "2022", 0, 123456)`);
        await waitForDataSourcesLoaded(model);
        assert.strictEqual(
            getEvaluatedCell(model, "A1").error.message,
            "Currency not available for this company."
        );
    });

    QUnit.test("formula with invalid date", async (assert) => {
        const model = await createModelWithDataSource();
        setCellContent(model, "A1", `=ODOO.CREDIT("100",)`);
        setCellContent(model, "A2", `=ODOO.DEBIT("100", 0)`);
        setCellContent(model, "A3", `=ODOO.BALANCE("100", -1)`);
        setCellContent(model, "A4", `=ODOO.BALANCE("100", "not a valid period")`);
        setCellContent(model, "A5", `=ODOO.BALANCE("100", 1900)`); // this should be ok
        setCellContent(model, "A6", `=ODOO.BALANCE("100", 1900, -1)`);
        setCellContent(model, "A7", `=ODOO.DEBIT("100", 1899)`);
        await waitForDataSourcesLoaded(model);
        const errorMessage = `'%s' is not a valid period. Supported formats are "21/12/2022", "Q1/2022", "12/2022", and "2022".`;
        assert.equal(getEvaluatedCell(model, "A1").error.message, "0 is not a valid year.");
        assert.equal(getEvaluatedCell(model, "A2").error.message, "0 is not a valid year.");
        assert.equal(getEvaluatedCell(model, "A3").error.message, "-1 is not a valid year.");
        assert.equal(
            getEvaluatedCell(model, "A4").error.message,
            sprintf(errorMessage, "not a valid period")
        );
        assert.equal(getEvaluatedCell(model, "A5").value, 0);
        assert.equal(getEvaluatedCell(model, "A6").error.message, "1899 is not a valid year.");
        assert.equal(getEvaluatedCell(model, "A7").error.message, "1899 is not a valid year.");
    });

    QUnit.test("Evaluation with multiple account codes", async (assert) => {
        const model = await createModelWithDataSource({
            mockRPC: async function (route, args) {
                if (args.method === "spreadsheet_fetch_debit_credit") {
                    assert.step("spreadsheet_fetch_debit_credit");
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

        await waitForDataSourcesLoaded(model);
        assert.equal(getCellValue(model, "A1"), 26);
        assert.equal(getCellValue(model, "A2"), 142);
        assert.equal(getCellValue(model, "A3"), 116);

        assert.equal(getCellValue(model, "B1"), 26);
        assert.equal(getCellValue(model, "B2"), 142);
        assert.equal(getCellValue(model, "B3"), 116);
        assert.verifySteps(["spreadsheet_fetch_debit_credit"]);
    });

    QUnit.test("Handle error evaluation", async (assert) => {
        const model = await createModelWithDataSource({
            mockRPC: async function (route, args) {
                if (args.method === "spreadsheet_fetch_debit_credit") {
                    throw new Error("a nasty error");
                }
            },
        });
        setCellContent(model, "A1", `=ODOO.CREDIT("100", "2022")`);
        await waitForDataSourcesLoaded(model);
        const cell = getEvaluatedCell(model, "A1");
        assert.equal(cell.value, "#ERROR");
        assert.equal(cell.error.message, "a nasty error");
    });

    QUnit.test("Server requests", async (assert) => {
        const model = await createModelWithDataSource({
            mockRPC: async function (route, args) {
                if (args.method === "spreadsheet_fetch_debit_credit") {
                    const blobs = args.args[0];
                    for (const blob of blobs) {
                        assert.step(JSON.stringify(blob));
                    }
                }
                return [];
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
        await waitForDataSourcesLoaded(model);

        assert.verifySteps([
            JSON.stringify(
                camelToSnakeObject({
                    dateRange: parseAccountingDate("2022", locale),
                    codes: ["100"],
                    companyId: null,
                    includeUnposted: false,
                })
            ),
            JSON.stringify(
                camelToSnakeObject({
                    dateRange: parseAccountingDate("01/2022", locale),
                    codes: ["100"],
                    companyId: null,
                    includeUnposted: false,
                })
            ),
            JSON.stringify(
                camelToSnakeObject({
                    dateRange: parseAccountingDate("Q2/2022", locale),
                    codes: ["100"],
                    companyId: null,
                    includeUnposted: false,
                })
            ),
            JSON.stringify(
                camelToSnakeObject({
                    dateRange: parseAccountingDate("2021", locale),
                    codes: ["10"],
                    companyId: null,
                    includeUnposted: false,
                })
            ),
            JSON.stringify(
                camelToSnakeObject({
                    dateRange: parseAccountingDate("2021", locale),
                    codes: ["5"],
                    companyId: 2,
                    includeUnposted: false,
                })
            ),
            JSON.stringify(
                camelToSnakeObject({
                    dateRange: parseAccountingDate("05/04/2022", locale),
                    codes: ["5"],
                    companyId: null,
                    includeUnposted: false,
                })
            ),
            JSON.stringify(
                camelToSnakeObject({
                    dateRange: parseAccountingDate("2022", locale),
                    codes: ["5"],
                    companyId: null,
                    includeUnposted: false,
                })
            ),
            JSON.stringify(
                camelToSnakeObject({
                    dateRange: parseAccountingDate("05/05/2022", locale),
                    codes: ["100"],
                    companyId: null,
                    includeUnposted: true,
                })
            ),
        ]);
    });

    QUnit.test("Server requests with multiple account codes", async (assert) => {
        const model = await createModelWithDataSource({
            mockRPC: async function (route, args) {
                if (args.method === "spreadsheet_fetch_debit_credit") {
                    assert.step("spreadsheet_fetch_debit_credit");
                    const blobs = args.args[0];
                    for (const blob of blobs) {
                        assert.step(JSON.stringify(blob));
                    }
                }
            },
        });
        setCellContent(model, "A1", `=ODOO.BALANCE("100,200", "2022")`);
        setCellContent(model, "A2", `=ODOO.CREDIT("100,200", "2022")`);
        setCellContent(model, "A3", `=ODOO.DEBIT("100,200","2022")`);
        await waitForDataSourcesLoaded(model);

        assert.verifySteps([
            "spreadsheet_fetch_debit_credit",
            JSON.stringify(
                camelToSnakeObject({
                    dateRange: parseAccountingDate("2022", locale),
                    codes: ["100", "200"],
                    companyId: null,
                    includeUnposted: false,
                })
            ),
        ]);
    });

    QUnit.test("account group formula as input to balance formula", async (assert) => {
        const model = await createModelWithDataSource({
            serverData,
            mockRPC: async function (route, args) {
                if (args.method === "spreadsheet_fetch_debit_credit") {
                    assert.step("spreadsheet_fetch_debit_credit");
                    const blobs = args.args[0];
                    for (const blob of blobs) {
                        assert.step(JSON.stringify(blob));
                    }
                }
            },
        });
        setCellContent(model, "A1", `=ODOO.ACCOUNT.GROUP("income")`);
        setCellContent(model, "A2", `=ODOO.BALANCE(A1, 2022)`);
        assert.equal(getCellValue(model, "A1"), "Loading...");
        assert.equal(getCellValue(model, "A2"), "Loading...");
        await waitForDataSourcesLoaded(model);
        assert.equal(getCellValue(model, "A1"), "100104,200104");
        assert.equal(getCellValue(model, "A2"), 0);
        assert.verifySteps([
            "spreadsheet_fetch_debit_credit",
            JSON.stringify(
                camelToSnakeObject({
                    dateRange: parseAccountingDate("2022", locale),
                    codes: ["100104", "200104"],
                    companyId: null,
                    includeUnposted: false,
                })
            ),
        ]);
    });

    QUnit.test("two concurrent requests on different accounts", async (assert) => {
        const model = await createModelWithDataSource({
            serverData,
            mockRPC: async function (route, args) {
                if (args.method === "spreadsheet_fetch_debit_credit") {
                    assert.step("spreadsheet_fetch_debit_credit");
                    const blobs = args.args[0];
                    for (const blob of blobs) {
                        assert.step(JSON.stringify(blob));
                    }
                }
            },
        });
        setCellContent(model, "A1", `=ODOO.ACCOUNT.GROUP("income")`);
        setCellContent(model, "A2", `=ODOO.BALANCE(A1, 2022)`); // batched only when A1 resolves
        setCellContent(model, "A3", `=ODOO.BALANCE("100", 2022)`); // batched directly
        assert.equal(getCellValue(model, "A1"), "Loading...");
        assert.equal(getCellValue(model, "A2"), "Loading...");
        assert.equal(getCellValue(model, "A3"), "Loading...");
        // A lot happens within the next tick.
        // Because cells are evaluated given their order in the sheet,
        // A1's request is done first, meaning it's also resolved first, which add A2 to the next batch (synchronously)
        // Only then A3 is resolved. => A2 is batched while A3 is pending
        await waitForDataSourcesLoaded(model);
        assert.equal(getCellValue(model, "A1"), "100104,200104");
        assert.equal(getCellValue(model, "A2"), 0);
        assert.equal(getCellValue(model, "A3"), 0);
        assert.verifySteps([
            "spreadsheet_fetch_debit_credit",
            JSON.stringify(
                camelToSnakeObject({
                    dateRange: parseAccountingDate("2022", locale),
                    codes: ["100"],
                    companyId: null,
                    includeUnposted: false,
                })
            ),
            "spreadsheet_fetch_debit_credit",
            JSON.stringify(
                camelToSnakeObject({
                    dateRange: parseAccountingDate("2022", locale),
                    codes: ["100104", "200104"],
                    companyId: null,
                    includeUnposted: false,
                })
            ),
        ]);
    });

    QUnit.test("parseAccountingDate", (assert) => {
        assert.deepEqual(parseAccountingDate("2022", locale), {
            rangeType: "year",
            year: 2022,
        });
        assert.deepEqual(parseAccountingDate("11/10/2022", locale), {
            rangeType: "day",
            year: 2022,
            month: 11,
            day: 10,
        });
        assert.deepEqual(parseAccountingDate("10/2022", locale), {
            rangeType: "month",
            year: 2022,
            month: 10,
        });
        assert.deepEqual(parseAccountingDate("Q1/2022", locale), {
            rangeType: "quarter",
            year: 2022,
            quarter: 1,
        });
        assert.deepEqual(parseAccountingDate("q4/2022", locale), {
            rangeType: "quarter",
            year: 2022,
            quarter: 4,
        });
        // A number below 3000 is interpreted as a year.
        // It's interpreted as a regular spreadsheet date otherwise
        assert.deepEqual(parseAccountingDate("3005", locale), {
            rangeType: "day",
            year: 1908,
            month: 3,
            day: 23,
        });
    });
});
