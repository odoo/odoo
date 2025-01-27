import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { describe, expect, test } from "@odoo/hoot";
import {
    defineSpreadsheetActions,
    defineSpreadsheetModels,
    getPyEnv,
} from "@spreadsheet/../tests/helpers/data";

import { selectCell, setCellContent, updatePivot } from "@spreadsheet/../tests/helpers/commands";
import { doMenuAction, getActionMenu } from "@spreadsheet/../tests/helpers/ui";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/helpers/pivot";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";

import * as spreadsheet from "@odoo/o-spreadsheet";
import { getCell, getCellFormula, getCellValue } from "@spreadsheet/../tests/helpers/getters";
import { mockService, onRpc } from "@web/../tests/web_test_helpers";

const { cellMenuRegistry } = spreadsheet.registries;

onRpc("ir.model", "display_name_for", (args) => {
    const models = args.args[0];
    const pyEnv = getPyEnv();
    const records = pyEnv["ir.model"]._records.filter((record) => models.includes(record.model));
    return records.map((record) => ({
        model: record.model,
        display_name: record.name,
    }));
});

describe.current.tags("headless");
defineSpreadsheetModels();
defineSpreadsheetActions();

const basicListAction = {
    type: "ir.actions.act_window",
    name: "Partner",
    res_model: "partner",
    views: [
        [false, "list"],
        [false, "form"],
    ],
    target: "current",
    domain: [],
    context: {},
};

test("Can open see records on headers col", async function () {
    const fakeActionService = {
        doAction: (actionRequest, options = {}) => {
            expect.step("doAction");
            expect(actionRequest).toEqual({
                ...basicListAction,
                domain: [["foo", "=", 1]],
            });
            expect(options.viewType).toBe("list");
        },
    };
    mockService("action", fakeActionService);
    const { env, model } = await createSpreadsheetWithPivot();
    selectCell(model, "B1");
    await animationFrame();
    await doMenuAction(cellMenuRegistry, ["pivot_see_records"], env);
    expect.verifySteps(["doAction"]);
});

test("Can open see records on headers row", async function () {
    const fakeActionService = {
        doAction: (actionRequest, options = {}) => {
            expect.step("doAction");
            expect(actionRequest).toEqual({
                ...basicListAction,
                domain: [["bar", "=", false]],
            });
            expect(options.viewType).toBe("list");
        },
    };
    mockService("action", fakeActionService);
    const { env, model } = await createSpreadsheetWithPivot();
    selectCell(model, "A3");
    await animationFrame();
    await doMenuAction(cellMenuRegistry, ["pivot_see_records"], env);
    expect.verifySteps(["doAction"]);
});

test("Can open see records on measure headers", async function () {
    const fakeActionService = {
        doAction: (actionRequest, options = {}) => {
            expect.step("doAction");
            expect(actionRequest).toEqual({
                ...basicListAction,
                domain: [["foo", "=", 1]],
            });
            expect(options.viewType).toBe("list");
        },
    };
    mockService("action", fakeActionService);
    const { env, model } = await createSpreadsheetWithPivot();
    selectCell(model, "B2");
    await animationFrame();
    await doMenuAction(cellMenuRegistry, ["pivot_see_records"], env);
    expect.verifySteps(["doAction"]);
});

test("Domain with granularity quarter_number are correctly computer", async function () {
    const fakeActionService = {
        doAction: (actionRequest) => {
            expect.step("doAction");
            expect.step(actionRequest.domain);
        },
    };
    mockService("action", fakeActionService);
    const { env, model, pivotId } = await createSpreadsheetWithPivot();

    updatePivot(model, pivotId, {
        rows: [{ fieldName: "date", granularity: "quarter_number", order: "asc" }],
    });
    await animationFrame();
    setCellContent(model, "A1", `=PIVOT.HEADER(1,"date:quarter_number",2)`);
    selectCell(model, "A1");
    await doMenuAction(cellMenuRegistry, ["pivot_see_records"], env);
    expect.verifySteps(["doAction", [[`date.quarter_number`, "=", 2]]]);
});

test("Domain with granularity iso_week_number are correctly computer", async function () {
    const fakeActionService = {
        doAction: (actionRequest) => {
            expect.step("doAction");
            expect.step(actionRequest.domain);
        },
    };
    mockService("action", fakeActionService);
    const { env, model, pivotId } = await createSpreadsheetWithPivot();

    updatePivot(model, pivotId, {
        rows: [{ fieldName: "date", granularity: "iso_week_number", order: "asc" }],
    });
    await animationFrame();
    setCellContent(model, "A1", `=PIVOT.HEADER(1,"date:iso_week_number",15)`);
    selectCell(model, "A1");
    await doMenuAction(cellMenuRegistry, ["pivot_see_records"], env);
    expect.verifySteps(["doAction", [[`date.iso_week_number`, "=", 15]]]);
});

test("Domain with granularity month_number are correctly computer", async function () {
    const fakeActionService = {
        doAction: (actionRequest) => {
            expect.step("doAction");
            expect.step(actionRequest.domain);
        },
    };
    mockService("action", fakeActionService);
    const { env, model, pivotId } = await createSpreadsheetWithPivot();

    updatePivot(model, pivotId, {
        rows: [{ fieldName: "date", granularity: "month_number", order: "asc" }],
    });
    await animationFrame();
    setCellContent(model, "A1", `=PIVOT.HEADER(1,"date:month_number",4)`);
    selectCell(model, "A1");
    await doMenuAction(cellMenuRegistry, ["pivot_see_records"], env);
    expect.verifySteps(["doAction", [[`date.month_number`, "=", 4]]]);
});

test("Domain with granularity day_of_month are correctly computer", async function () {
    const fakeActionService = {
        doAction: (actionRequest) => {
            expect.step("doAction");
            expect.step(actionRequest.domain);
        },
    };
    mockService("action", fakeActionService);
    const { env, model, pivotId } = await createSpreadsheetWithPivot();

    updatePivot(model, pivotId, {
        rows: [{ fieldName: "date", granularity: "day_of_month", order: "asc" }],
    });
    await animationFrame();
    setCellContent(model, "A1", `=PIVOT.HEADER(1,"date:day_of_month",11)`);
    selectCell(model, "A1");
    await doMenuAction(cellMenuRegistry, ["pivot_see_records"], env);
    expect.verifySteps(["doAction", [[`date.day_of_month`, "=", 11]]]);
});

test("Cannot open see records on the main PIVOT cell", async function () {
    const { env, model } = await createSpreadsheetWithPivot();
    model.dispatch("CREATE_SHEET", { sheetId: "42" });
    setCellContent(model, "A1", `=PIVOT("1")`, "42");
    selectCell(model, "A1", "42");
    const action = await getActionMenu(cellMenuRegistry, ["pivot_see_records"], env);
    expect(action.isVisible(env)).toBe(false);
});

test("Cannot open see records on the empty PIVOT cell below the main cell", async function () {
    const { env, model } = await createSpreadsheetWithPivot();
    model.dispatch("CREATE_SHEET", { sheetId: "42" });
    setCellContent(model, "A1", `=PIVOT("1")`, "42");
    selectCell(model, "A2", "42"); // A2 is always empty. It's the cell next to measure headers.
    const action = await getActionMenu(cellMenuRegistry, ["pivot_see_records"], env);
    expect(action.isVisible(env)).toBe(false);
});

test("Can see records on PIVOT cells", async function () {
    const actions = [];
    const fakeActionService = {
        doAction: (actionRequest, options = {}) => {
            expect.step("doAction");
            actions.push(actionRequest);
        },
    };
    mockService("action", fakeActionService);
    const { env, model } = await createSpreadsheetWithPivot();
    const firstSheetId = model.getters.getActiveSheetId();

    async function checkCells(cells) {
        // Let's check that clicking on a cell opens the same action on the first sheet
        // where the pivot is made of individual regular pivot formulas and on the second
        // sheet where the pivot is made of a single PIVOT formula.
        for (const [xc, formula] of Object.entries(cells)) {
            // let's check the cell formula is what we expect
            expect(getCell(model, xc, firstSheetId)?.content).toBe(formula, {
                message: `${xc} on the first sheet is ${formula}`,
            });

            // action on the first sheet, on regular pivot formula
            selectCell(model, xc, firstSheetId);
            await doMenuAction(cellMenuRegistry, ["pivot_see_records"], env);

            // action on the second sheet, on PIVOT
            selectCell(model, xc, "42");
            await doMenuAction(cellMenuRegistry, ["pivot_see_records"], env);

            expect(actions[0]).toEqual(actions[1], { message: "both actions are the same" });
            expect.verifySteps(["doAction", "doAction"]);
            actions.length = 0;
        }
    }
    model.dispatch("CREATE_SHEET", { sheetId: "42" });
    setCellContent(model, "A1", `=PIVOT("1")`, "42");

    // here is what the cells look like
    const header_cells = {
        // B1 is a column header
        B1: '=PIVOT.HEADER(1,"foo",1)',
        // B2 is a measure header
        B2: '=PIVOT.HEADER(1,"foo",1,"measure","probability:avg")',
        // A3 is a row header
        A3: '=PIVOT.HEADER(1,"bar",FALSE)',
        // A5 is a total header
        A5: "=PIVOT.HEADER(1)",
    };
    const data_cells = {
        // B3 is an empty value
        B3: '=PIVOT.VALUE(1,"probability:avg","bar",FALSE,"foo",1)',
        // B4 is an non-empty value
        B4: '=PIVOT.VALUE(1,"probability:avg","bar",TRUE,"foo",1)',
        // B5 is a column group total value
        B5: '=PIVOT.VALUE(1,"probability:avg","foo",1)',
        // F3 is a row group total value
        F3: '=PIVOT.VALUE(1,"probability:avg","bar",FALSE)',
        // F5 is the total
        F5: '=PIVOT.VALUE(1,"probability:avg")',
    };
    await checkCells({ ...header_cells, ...data_cells });

    // same but without the column headers
    // set the function in A3 such as the data cells matches the ones in the first sheet
    setCellContent(model, "A3", `=PIVOT("1",,,FALSE)`, "42");
    await checkCells(data_cells);
});

test("Cannot see records of pivot formula without value", async function () {
    const { env, model } = await createSpreadsheetWithPivot();
    expect(getCellFormula(model, "B3")).toBe(
        `=PIVOT.VALUE(1,"probability:avg","bar",FALSE,"foo",1)`
    );
    expect(getCellValue(model, "B3")).toBe("", { message: "B3 is empty" });
    selectCell(model, "B3");
    const action = await getActionMenu(cellMenuRegistry, ["pivot_see_records"], env);
    expect(action.isVisible(env)).toBe(false);
});

test("Cannot see records of spreadsheet pivot", async function () {
    const { model, env } = await createSpreadsheetWithPivot();
    setCellContent(model, "A11", "A");
    setCellContent(model, "A12", "1");
    setCellContent(model, "B11", "B");
    setCellContent(model, "B12", "2");

    model.dispatch("ADD_PIVOT", {
        pivotId: "2",
        pivot: {
            type: "SPREADSHEET",
            columns: [{ fieldName: "A", order: "asc" }],
            rows: [],
            measures: [{ id: "B:sum", fieldName: "B", aggregator: "sum" }],
            name: "Pivot2",
            dataSet: {
                sheetId: model.getters.getActiveSheetId(),
                zone: { top: 10, bottom: 11, left: 0, right: 1 },
            },
        },
    });
    setCellContent(model, "A13", `=PIVOT("2")`);
    expect(getCellValue(model, "B15")).toBe(2);
    selectCell(model, "B15");
    const action = await getActionMenu(cellMenuRegistry, ["pivot_see_records"], env);
    expect(action.isVisible(env)).toBe(false);
});

test("See records is not visible on an empty cell", async function () {
    const { env, model } = await createSpreadsheetWithPivot();
    expect(getCell(model, "A21")).toBe(undefined);
    selectCell(model, "A21");
    const action = cellMenuRegistry.getAll().find((item) => item.id === "pivot_see_records");
    expect(action.isVisible(env)).toBe(false);
});

test("Cannot see records of out of range positional pivot formula with calculated field", async function () {
    const { env, model, pivotId } = await createSpreadsheetWithPivot();
    updatePivot(model, pivotId, {
        measures: [
            {
                id: "calculated",
                fieldName: "calculated",
                aggregator: "sum",
                computedBy: {
                    formula: "=0",
                    sheetId: model.getters.getActiveSheetId(),
                },
            },
        ],
    });
    await waitForDataLoaded(model);
    setCellContent(model, "A1", `=PIVOT.VALUE(1,"calculated","bar",FALSE,"#foo",22)`);
    selectCell(model, "A1");
    const action = await getActionMenu(cellMenuRegistry, ["pivot_see_records"], env);
    expect(!!action.isVisible(env)).toBe(false);
});

test("See records is not visible if the pivot is not loaded, even if the cell has a value", async function () {
    let deferred = undefined;
    const { env, model } = await createSpreadsheetWithPivot({
        arch: /*xml*/ `
        <pivot>
            <field name="probability" type="measure"/>
        </pivot>
    `,
        mockRPC: async function (route, args) {
            if (deferred && args.method === "read_group" && args.model === "partner") {
                await deferred;
            }
        },
    });
    setCellContent(model, "A1", '=IFERROR(PIVOT.VALUE("1","probability"), 42)');
    deferred = new Deferred();
    model.dispatch("REFRESH_ALL_DATA_SOURCES");
    const action = cellMenuRegistry.getAll().find((item) => item.id === "pivot_see_records");
    expect(action.isVisible(env)).toBe(false);
    deferred.resolve();
    await animationFrame();
    expect(action.isVisible(env)).toBe(true);
});
