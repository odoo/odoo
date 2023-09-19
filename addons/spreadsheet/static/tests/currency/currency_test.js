/** @odoo-module */

import { setCellContent } from "@spreadsheet/../tests/utils/commands";
import { getCellValue, getEvaluatedCell } from "@spreadsheet/../tests/utils/getters";
import {
    createModelWithDataSource,
    waitForDataSourcesLoaded,
} from "@spreadsheet/../tests/utils/model";

QUnit.module("spreadsheet > Currency");

QUnit.test("Basic exchange formula", async (assert) => {
    const model = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "get_rates_for_spreadsheet") {
                const info = args.args[0][0];
                assert.equal(info.from, "EUR");
                assert.equal(info.to, "USD");
                assert.equal(info.date, undefined);
                assert.step("rate fetched");
                return [{ ...info, rate: 0.9 }];
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.CURRENCY.RATE("EUR","USD")`);
    assert.strictEqual(getCellValue(model, "A1"), "Loading...");
    await waitForDataSourcesLoaded(model);
    assert.strictEqual(getCellValue(model, "A1"), 0.9);
    assert.verifySteps(["rate fetched"]);
});

QUnit.test("rate formula at a given date(time)", async (assert) => {
    const model = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "get_rates_for_spreadsheet") {
                const [A1, A2] = args.args[0];
                assert.equal(A1.date, "2020-12-31");
                assert.equal(A2.date, "2020-11-30");
                assert.step("rate fetched");
                return [
                    { ...A1, rate: 0.9 },
                    { ...A2, rate: 0.9 },
                ];
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.CURRENCY.RATE("EUR","USD", "12-31-2020")`);
    setCellContent(model, "A2", `=ODOO.CURRENCY.RATE("EUR","USD", "11-30-2020 00:00:00")`);
    await waitForDataSourcesLoaded(model);
    assert.verifySteps(["rate fetched"]);
});

QUnit.test("invalid date", async (assert) => {
    const model = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "get_rates_for_spreadsheet") {
                throw new Error("Should not be called");
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.CURRENCY.RATE("EUR","USD", "hello")`);
    await waitForDataSourcesLoaded(model);
    assert.strictEqual(getCellValue(model, "A1"), "#ERROR");
    assert.strictEqual(
        getEvaluatedCell(model, "A1").error.message,
        "The function ODOO.CURRENCY.RATE expects a number value, but 'hello' is a string, and cannot be coerced to a number."
    );
});

QUnit.test("Currency rate throw with unknown currency", async (assert) => {
    const model = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "get_rates_for_spreadsheet") {
                const info = args.args[0][0];
                return [{ ...info, rate: false }];
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.CURRENCY.RATE("INVALID","USD")`);
    await waitForDataSourcesLoaded(model);
    assert.strictEqual(getEvaluatedCell(model, "A1").error.message, "Currency rate unavailable.");
});

QUnit.test("Currency rates are only loaded once", async (assert) => {
    const model = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "get_rates_for_spreadsheet") {
                assert.step("FETCH");
                const info = args.args[0][0];
                return [{ ...info, rate: 0.9 }];
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.CURRENCY.RATE("EUR","USD")`);
    await waitForDataSourcesLoaded(model);
    assert.verifySteps(["FETCH"]);
    setCellContent(model, "A2", `=ODOO.CURRENCY.RATE("EUR","USD")`);
    await waitForDataSourcesLoaded(model);
    assert.verifySteps([]);
});

QUnit.test("Currency rates are loaded once by clock", async (assert) => {
    const model = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "get_rates_for_spreadsheet") {
                assert.step("FETCH:" + args.args[0].length);
                const info1 = args.args[0][0];
                const info2 = args.args[0][1];
                return [
                    { ...info1, rate: 0.9 },
                    { ...info2, rate: 1 },
                ];
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.CURRENCY.RATE("EUR","USD")`);
    setCellContent(model, "A2", `=ODOO.CURRENCY.RATE("EUR","SEK")`);
    await waitForDataSourcesLoaded(model);
    assert.verifySteps(["FETCH:2"]);
});
