import { describe, expect, test } from "@odoo/hoot";
import { setCellContent } from "@spreadsheet/../tests/helpers/commands";
import { getCellValue, getEvaluatedCell } from "@spreadsheet/../tests/helpers/getters";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";
import { defineSpreadsheetActions, defineSpreadsheetModels } from "../helpers/data";
import { RPCError } from "@web/core/network/rpc";

describe.current.tags("headless");

defineSpreadsheetModels();
defineSpreadsheetActions();

test("Basic exchange formula", async () => {
    const { model } = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "get_rates_for_spreadsheet") {
                const info = args.args[0][0];
                expect(info.from).toBe("EUR");
                expect(info.to).toBe("USD");
                expect(info.date).toBe(undefined);
                expect.step("rate fetched");
                return [{ ...info, rate: 0.9 }];
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.CURRENCY.RATE("EUR","USD")`);
    expect(getCellValue(model, "A1")).toBe("Loading...");
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A1")).toBe(0.9);
    expect.verifySteps(["rate fetched"]);
});

test("rate formula at a given date(time)", async () => {
    const { model } = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "get_rates_for_spreadsheet") {
                const [A1, A2] = args.args[0];
                expect(A1.date).toBe("2020-12-31");
                expect(A2.date).toBe("2020-11-30");
                expect.step("rate fetched");
                return [
                    { ...A1, rate: 0.9 },
                    { ...A2, rate: 0.9 },
                ];
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.CURRENCY.RATE("EUR","USD", "12-31-2020")`);
    setCellContent(model, "A2", `=ODOO.CURRENCY.RATE("EUR","USD", "11-30-2020 00:00:00")`);
    await waitForDataLoaded(model);
    expect.verifySteps(["rate fetched"]);
});

test("invalid date", async () => {
    const { model } = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "get_rates_for_spreadsheet") {
                throw new Error("Should not be called");
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.CURRENCY.RATE("EUR","USD", "hello")`);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A1")).toBe("#ERROR");
    expect(getEvaluatedCell(model, "A1").message).toBe(
        "The function ODOO.CURRENCY.RATE expects a number value, but 'hello' is a string, and cannot be coerced to a number."
    );
});

test("rate formula at a given company", async () => {
    const { model } = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "get_rates_for_spreadsheet") {
                const [A1, A2] = args.args[0];
                expect(A1.company_id).toBe(1);
                expect(A2.company_id).toBe(2);
                expect.step("rate fetched");
                return [
                    { ...A1, rate: 0.7 },
                    { ...A2, rate: 0.9 },
                ];
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.CURRENCY.RATE("EUR","USD",, 1)`);
    setCellContent(model, "A2", `=ODOO.CURRENCY.RATE("EUR","USD",, 2)`);
    await waitForDataLoaded(model);
    expect.verifySteps(["rate fetched"]);
    expect(getCellValue(model, "A1")).toBe(0.7);
    expect(getCellValue(model, "A2")).toBe(0.9);
});

test("invalid company id", async () => {
    const { model } = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "get_rates_for_spreadsheet") {
                const error = new RPCError();
                error.data = { message: "Invalid company id." };
                throw error;
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.CURRENCY.RATE("EUR","USD",, 45)`);
    await waitForDataLoaded(model);
    expect(getCellValue(model, "A1")).toBe("#ERROR");
    expect(getEvaluatedCell(model, "A1").message).toBe("Invalid company id.");
});

test("Currency rate throw with unknown currency", async () => {
    const { model } = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "get_rates_for_spreadsheet") {
                const info = args.args[0][0];
                return [{ ...info, rate: false }];
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.CURRENCY.RATE("INVALID","USD")`);
    await waitForDataLoaded(model);
    expect(getEvaluatedCell(model, "A1").message).toBe("Currency rate unavailable.");
});

test("Currency rates are only loaded once", async () => {
    const { model } = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "get_rates_for_spreadsheet") {
                expect.step("FETCH");
                const info = args.args[0][0];
                return [{ ...info, rate: 0.9 }];
            }
        },
    });
    setCellContent(model, "A1", `=ODOO.CURRENCY.RATE("EUR","USD")`);
    await waitForDataLoaded(model);
    expect.verifySteps(["FETCH"]);
    setCellContent(model, "A2", `=ODOO.CURRENCY.RATE("EUR","USD")`);
    await waitForDataLoaded(model);
    expect.verifySteps([]);
});

test("Currency rates are loaded once by clock", async () => {
    const { model } = await createModelWithDataSource({
        mockRPC: async function (route, args) {
            if (args.method === "get_rates_for_spreadsheet") {
                expect.step("FETCH:" + args.args[0].length);
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
    await waitForDataLoaded(model);
    expect.verifySteps(["FETCH:2"]);
});
