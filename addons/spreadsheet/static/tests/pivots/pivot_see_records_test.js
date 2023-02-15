/** @odoo-module */
import { nextTick } from "@web/../tests/helpers/utils";

import { selectCell } from "@spreadsheet/../tests/utils/commands";
import { doMenuAction } from "@spreadsheet/../tests/utils/ui";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/utils/pivot";

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { registry } from "@web/core/registry";

const { cellMenuRegistry } = spreadsheet.registries;

QUnit.module("spreadsheet > see pivot records");

const basicListAction = {
    type: "ir.actions.act_window",
    name: "Partner",
    res_model: "partner",
    view_mode: "list",
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
