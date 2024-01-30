/** @odoo-module */

import { nextTick } from "@web/../tests/helpers/utils";
import { createModelWithDataSource } from "../utils/model";

QUnit.module("spreadsheet currency plugin");

QUnit.test("get default currency format when it's in the config", async (assert) => {
    const model = await createModelWithDataSource({
        modelConfig: {
            defaultCurrencyFormat: "#,##0.00[$θ]",
        },
        mockRPC: async function (route, args) {
            throw new Error("Should not make any RPC");
        },
    });
    assert.strictEqual(model.getters.getCompanyCurrencyFormat(), "#,##0.00[$θ]");
});

QUnit.test("get default currency format when it's not in the config", async (assert) => {
    const model = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "get_company_currency_for_spreadsheet") {
                return {
                    code: "Odoo",
                    symbol: "θ",
                    position: "after",
                    decimalPlaces: 2,
                };
            }
        },
    });
    assert.throws(() => model.getters.getCompanyCurrencyFormat(), "Data is loading");
    await nextTick();
    assert.strictEqual(model.getters.getCompanyCurrencyFormat(), "#,##0.00[$θ]");
    assert.verifySteps([]);
});

QUnit.test("get specific currency format", async (assert) => {
    const model = await createModelWithDataSource({
        modelConfig: {
            defaultCurrencyFormat: "#,##0.00[$θ]",
        },
        mockRPC: async function (route, args) {
            if (args.method === "get_company_currency_for_spreadsheet" && args.args[0] === 42) {
                return {
                    code: "Odoo",
                    symbol: "O",
                    position: "after",
                    decimalPlaces: 2,
                };
            }
        },
    });
    assert.throws(() => model.getters.getCompanyCurrencyFormat(42), "Data is loading");
    await nextTick();
    assert.strictEqual(model.getters.getCompanyCurrencyFormat(42), "#,##0.00[$O]");
});
