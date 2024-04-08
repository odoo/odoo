/** @odoo-module */
import { nextTick } from "@web/../tests/helpers/utils";

import { selectCell } from "@spreadsheet/../tests/utils/commands";
import { doMenuAction, getActionMenu } from "@spreadsheet/../tests/utils/ui";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/utils/pivot";

import * as spreadsheet from "@odoo/o-spreadsheet";
import { registry } from "@web/core/registry";
import { setCellContent } from "../utils/commands";
import { getCell, getCellFormula, getCellValue } from "../utils/getters";

const { cellMenuRegistry } = spreadsheet.registries;

registry.category("mock_server").add("ir.model/display_name_for", function (route, args) {
    const models = args.args[0];
    const records = this.models["ir.model"].records.filter((record) =>
        models.includes(record.model)
    );
    return records.map((record) => ({
        model: record.model,
        display_name: record.name,
    }));
});

QUnit.module("spreadsheet > see pivot records");

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
};

QUnit.test("Can open see records on headers col", async function (assert) {
    const fakeActionService = {
        dependencies: [],
        start: (env) => ({
            doAction: (actionRequest, options = {}) => {
                assert.step("doAction");
                assert.deepEqual(actionRequest, {
                    ...basicListAction,
                    domain: [["foo", "=", 1]],
                });
                assert.strictEqual(options.viewType, "list");
            },
        }),
    };
    registry.category("services").add("action", fakeActionService);
    const { env, model } = await createSpreadsheetWithPivot();
    selectCell(model, "B1");
    await nextTick();
    await doMenuAction(cellMenuRegistry, ["pivot_see_records"], env);
    assert.verifySteps(["doAction"]);
});

QUnit.test("Can open see records on headers row", async function (assert) {
    const fakeActionService = {
        dependencies: [],
        start: (env) => ({
            doAction: (actionRequest, options = {}) => {
                assert.step("doAction");
                assert.deepEqual(actionRequest, {
                    ...basicListAction,
                    domain: [["bar", "=", false]],
                });
                assert.strictEqual(options.viewType, "list");
            },
        }),
    };
    registry.category("services").add("action", fakeActionService);
    const { env, model } = await createSpreadsheetWithPivot();
    selectCell(model, "A3");
    await nextTick();
    await doMenuAction(cellMenuRegistry, ["pivot_see_records"], env);
    assert.verifySteps(["doAction"]);
});

QUnit.test("Can open see records on measure headers", async function (assert) {
    const fakeActionService = {
        dependencies: [],
        start: (env) => ({
            doAction: (actionRequest, options = {}) => {
                assert.step("doAction");
                assert.deepEqual(actionRequest, {
                    ...basicListAction,
                    domain: [["foo", "=", 1]],
                });
                assert.strictEqual(options.viewType, "list");
            },
        }),
    };
    registry.category("services").add("action", fakeActionService);
    const { env, model } = await createSpreadsheetWithPivot();
    selectCell(model, "B2");
    await nextTick();
    await doMenuAction(cellMenuRegistry, ["pivot_see_records"], env);
    assert.verifySteps(["doAction"]);
});

QUnit.test("Cannot open see records on the main PIVOT cell", async function (assert) {
    const { env, model } = await createSpreadsheetWithPivot();
    model.dispatch("CREATE_SHEET", { sheetId: "42" });
    setCellContent(model, "A1", `=PIVOT("1")`, "42");
    selectCell(model, "A1", "42");
    const action = await getActionMenu(cellMenuRegistry, ["pivot_see_records"], env);
    assert.strictEqual(action.isVisible(env), false);
});

QUnit.test(
    "Cannot open see records on the empty PIVOT cell below the main cell",
    async function (assert) {
        const { env, model } = await createSpreadsheetWithPivot();
        model.dispatch("CREATE_SHEET", { sheetId: "42" });
        setCellContent(model, "A1", `=PIVOT("1")`, "42");
        selectCell(model, "A2", "42"); // A2 is always empty. It's the cell next to measure headers.
        const action = await getActionMenu(cellMenuRegistry, ["pivot_see_records"], env);
        assert.strictEqual(action.isVisible(env), false);
    }
);

QUnit.test("Can see records on PIVOT cells", async function (assert) {
    const actions = [];
    const fakeActionService = {
        start: (env) => ({
            doAction: (actionRequest, options = {}) => {
                assert.step("doAction");
                actions.push(actionRequest);
            },
        }),
    };
    registry.category("services").add("action", fakeActionService);
    const { env, model } = await createSpreadsheetWithPivot();
    const firstSheetId = model.getters.getActiveSheetId();

    async function checkCells(cells) {
        // Let's check that clicking on a cell opens the same action on the first sheet
        // where the pivot is made of individual regular pivot formulas and on the second
        // sheet where the pivot is made of a single PIVOT formula.
        for (const [xc, formula] of Object.entries(cells)) {
            // let's check the cell formula is what we expect
            assert.strictEqual(
                getCell(model, xc, firstSheetId)?.content,
                formula,
                `${xc} on the first sheet is ${formula}`
            );

            // action on the first sheet, on regular pivot formula
            selectCell(model, xc, firstSheetId);
            await doMenuAction(cellMenuRegistry, ["pivot_see_records"], env);

            // action on the second sheet, on PIVOT
            selectCell(model, xc, "42");
            await doMenuAction(cellMenuRegistry, ["pivot_see_records"], env);

            assert.deepEqual(actions[0], actions[1], "both actions are the same");
            assert.verifySteps(["doAction", "doAction"]);
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
        B2: '=PIVOT.HEADER(1,"foo",1,"measure","probability")',
        // A3 is a row header
        A3: '=PIVOT.HEADER(1,"bar","false")',
        // A5 is a total header
        A5: "=PIVOT.HEADER(1)",
    };
    const data_cells = {
        // B3 is an empty value
        B3: '=PIVOT.VALUE(1,"probability","bar","false","foo",1)',
        // B4 is an non-empty value
        B4: '=PIVOT.VALUE(1,"probability","bar","true","foo",1)',
        // B5 is a column group total value
        B5: '=PIVOT.VALUE(1,"probability","foo",1)',
        // F3 is a row group total value
        F3: '=PIVOT.VALUE(1,"probability","bar","false")',
        // F5 is the total
        F5: '=PIVOT.VALUE(1,"probability")',
    };
    await checkCells({ ...header_cells, ...data_cells });

    // same but without the column headers
    // set the function in A3 such as the data cells matches the ones in the first sheet
    setCellContent(model, "A3", `=PIVOT("1",,,FALSE)`, "42");
    await checkCells(data_cells);
});

QUnit.test("Cannot see records of pivot formula without value", async function (assert) {
    const { env, model } = await createSpreadsheetWithPivot();
    assert.strictEqual(
        getCellFormula(model, "B3"),
        `=PIVOT.VALUE(1,"probability","bar","false","foo",1)`
    );
    assert.strictEqual(getCellValue(model, "B3"), "", "B3 is empty");
    selectCell(model, "B3");
    const action = await getActionMenu(cellMenuRegistry, ["pivot_see_records"], env);
    assert.notOk(action.isVisible(env));
});
