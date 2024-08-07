import { describe, expect, test } from "@odoo/hoot";
import { registries, constants } from "@odoo/o-spreadsheet";
import { selectCell, setCellContent } from "@spreadsheet/../tests/helpers/commands";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { doMenuAction } from "@spreadsheet/../tests/helpers/ui";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";
import {
    defineSpreadsheetAccountModels,
    getAccountingData,
} from "@spreadsheet_account/../tests/accounting_test_data";
import { mockService } from "@web/../tests/web_test_helpers";

describe.current.tags("headless");
defineSpreadsheetAccountModels();

const { cellMenuRegistry } = registries;
const { DEFAULT_LOCALE } = constants;

const serverData = getAccountingData();

test("Create drill down domain", async () => {
    const drillDownAction = {
        type: "ir.actions.act_window",
        res_model: "account.move.line",
        view_mode: "list",
        views: [[false, "list"]],
        target: "current",
        domain: [["account_id", "in", [1, 2]]],
        name: "my awesome action",
    };
    const fakeActionService = {
        doAction: async (action, options) => {
            expect.step("drill down action");
            expect(action).toEqual(drillDownAction);
            expect(options).toBe(undefined);
            return true;
        },
    };
    mockService("action", fakeActionService);

    const model = await createModelWithDataSource({
        serverData,
        mockRPC: async function (route, args) {
            if (args.method === "spreadsheet_move_line_action") {
                expect(args.args).toEqual([
                    {
                        codes: ["100"],
                        company_id: null,
                        include_unposted: false,
                        date_range: {
                            range_type: "year",
                            year: 2020,
                        },
                    },
                ]);
                return drillDownAction;
            }
        },
    });
    const env = model.config.custom.env;
    env.model = model;
    setCellContent(model, "A1", `=ODOO.BALANCE("100", 2020)`);
    setCellContent(model, "A2", `=ODOO.BALANCE("100", 0)`);
    setCellContent(model, "A3", `=ODOO.BALANCE("100", 2020, , , FALSE)`);
    setCellContent(model, "A4", `=ODOO.BALANCE("100", 2020, , , )`);
    // Does not affect non formula cells
    setCellContent(model, "A5", `5`);
    await waitForDataLoaded(model);
    selectCell(model, "A1");
    const root = cellMenuRegistry
        .getMenuItems()
        .find((item) => item.id === "move_lines_see_records");
    expect(root.isVisible(env)).toBe(true);
    await root.execute(env);
    expect.verifySteps(["drill down action"]);
    selectCell(model, "A2");
    expect(root.isVisible(env)).toBe(false);
    selectCell(model, "A3");
    expect(root.isVisible(env)).toBe(true);
    await root.execute(env);
    expect.verifySteps(["drill down action"]);
    selectCell(model, "A4");
    expect(root.isVisible(env)).toBe(true);
    await root.execute(env);
    expect.verifySteps(["drill down action"]);
    selectCell(model, "A5");
    expect(root.isVisible(env)).toBe(false);
});

test("Create drill down domain when month date is a reference", async () => {
    mockService("action", { doAction: () => {} });
    const model = await createModelWithDataSource({
        serverData,
        mockRPC: async function (route, args) {
            if (args.method === "spreadsheet_move_line_action") {
                expect.step("spreadsheet_move_line_action");
                expect(args.args).toEqual([
                    {
                        codes: ["100"],
                        company_id: null,
                        include_unposted: false,
                        date_range: {
                            month: 2,
                            range_type: "month",
                            year: 2024,
                        },
                    },
                ]);
                return {};
            }
        },
    });
    const env = model.config.custom.env;
    env.model = model;
    setCellContent(model, "A1", "02/2024");
    setCellContent(model, "A2", '=ODOO.BALANCE("100", A1)');
    await waitForDataLoaded(model);
    selectCell(model, "A2");
    await doMenuAction(cellMenuRegistry, ["move_lines_see_records"], env);
    expect.verifySteps(["spreadsheet_move_line_action"]);
});

test("Create drill down domain when date uses a non-standard locale", async () => {
    mockService("action", { doAction: () => {} });
    const model = await createModelWithDataSource({
        serverData,
        mockRPC: async function (route, args) {
            if (args.method === "spreadsheet_move_line_action") {
                expect.step("spreadsheet_move_line_action");
                expect(args.args).toEqual([
                    {
                        codes: ["100"],
                        company_id: null,
                        include_unposted: false,
                        date_range: {
                            range_type: "day",
                            year: 2002,
                            month: 2,
                            day: 1,
                        },
                    },
                ]);
                return {};
            }
        },
    });
    const env = model.config.custom.env;
    env.model = model;
    const myLocale = { ...DEFAULT_LOCALE, dateFormat: "d/mmm/yyyy" };
    model.dispatch("UPDATE_LOCALE", { locale: myLocale });
    setCellContent(model, "A1", '=ODOO.BALANCE("100", DATE(2002, 2, 1))');
    await waitForDataLoaded(model);
    await doMenuAction(cellMenuRegistry, ["move_lines_see_records"], env);
    expect.verifySteps(["spreadsheet_move_line_action"]);
});
