/** @odoo-module */
import { makeDeferred, nextTick } from "@web/../tests/helpers/utils";

import { selectCell } from "@spreadsheet/../tests/utils/commands";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/utils/pivot";

import spreadsheet from "@spreadsheet/o_spreadsheet/o_spreadsheet_extended";
import { registry } from "@web/core/registry";
import { setCellContent } from "../utils/commands";
import { getCell } from "../utils/getters";

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
    const root = cellMenuRegistry.getAll().find((item) => item.id === "pivot_see_records");
    await root.action(env);
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
    const root = cellMenuRegistry.getAll().find((item) => item.id === "pivot_see_records");
    await root.action(env);
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
    const root = cellMenuRegistry.getAll().find((item) => item.id === "pivot_see_records");
    await root.action(env);
    assert.verifySteps(["doAction"]);
});

QUnit.test(
    "See records is not visible if the pivot is not loaded, even if the cell has a value",
    async function (assert) {
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
        setCellContent(model, "A1", '=IFERROR(ODOO.PIVOT("1","probability"), 42)');
        deferred = makeDeferred();
        model.dispatch("REFRESH_ALL_DATA_SOURCES");
        const action = cellMenuRegistry.getAll().find((item) => item.id === "pivot_see_records");
        assert.strictEqual(action.isVisible(env), false);
        deferred.resolve();
        await nextTick();
        assert.strictEqual(action.isVisible(env), true);
    }
);
QUnit.test("See records is not visible if the formula has an weird IF", async function (assert) {
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
    setCellContent(
        model,
        "A1",
        '=if(false, ODOO.PIVOT("1","probability","user_id",2,"partner_id", "#Error"), "test")'
    );
    deferred = makeDeferred();
    model.dispatch("REFRESH_ALL_DATA_SOURCES");
    const action = cellMenuRegistry.getAll().find((item) => item.id === "pivot_see_records");
    assert.strictEqual(action.isVisible(env), false);
    deferred.resolve();
    await nextTick();
    assert.strictEqual(action.isVisible(env), false);
});

QUnit.test("See records is not visible on an empty cell", async function (assert) {
    const { env, model } = await createSpreadsheetWithPivot();
    assert.strictEqual(getCell(model, "A21"), undefined);
    selectCell(model, "A21");
    const action = cellMenuRegistry.getAll().find((item) => item.id === "pivot_see_records");
    assert.strictEqual(action.isVisible(env), false);
});
