/** @odoo-module */

import { setCellContent } from "@spreadsheet/../tests/utils/commands";
import { getCell, getCellValue } from "@spreadsheet/../tests/utils/getters";
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
                return [{ ...info, rate: 0.9 }];
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.CURRENCY.RATE("EUR","USD")`);
    assert.strictEqual(getCellValue(model, "A1"), "Loading...");
    await waitForDataSourcesLoaded(model);
    assert.strictEqual(getCellValue(model, "A1"), 0.9);
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
    assert.strictEqual(getCell(model, "A1").evaluated.error.message, "Currency rate unavailable.");
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

QUnit.test("Currency rates per date", async (assert) => {
    const model = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "get_rates_for_spreadsheet") {
                assert.step("FETCH");
                const [info1, info2] = args.args[0];
                assert.step(new Date(info1.date).toLocaleString("en-US", { timeZone: "UTC" }));
                assert.step(new Date(info2.date).toLocaleString("en-US", { timeZone: "UTC" }));
                return [
                    { ...info1, rate: 0.9 },
                    { ...info2, rate: 0.8 },
                ];
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.CURRENCY.RATE("EUR","USD", "2/10/2023")`);
    setCellContent(model, "A2", `=ODOO.CURRENCY.RATE("EUR","USD", " 2/11/2023")`);
    await waitForDataSourcesLoaded(model);
    assert.verifySteps(["FETCH", "2/9/2023, 11:00:00 PM", "2/10/2023, 11:00:00 PM"]);
    assert.equal(getCell(model, "A1").evaluated.value, 0.9);
    assert.equal(getCell(model, "A1").evaluated.error, undefined);
    assert.equal(getCell(model, "A2").evaluated.value, 0.8);
    assert.equal(getCell(model, "A2").evaluated.error, undefined);
});
