/** @odoo-module */

import { nextTick } from "@web/../tests/helpers/utils";
import { registries } from "@odoo/o-spreadsheet";
import { getCellValue, getCell, getEvaluatedGrid } from "@spreadsheet/../tests/utils/getters";
import { addGlobalFilter, selectCell, setCellContent } from "@spreadsheet/../tests/utils/commands";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/utils/pivot";
import { waitForDataSourcesLoaded } from "@spreadsheet/../tests/utils/model";

const { cellMenuRegistry } = registries;

const testGlobalFilter = {
    id: "42",
    type: "relation",
    defaultValue: [41],
};
const testFieldMatching = {
    pivot: { 1: { chain: "product_id", type: "many2one" } },
};

QUnit.module("spreadsheet_edition > Global filters model", {}, () => {
    QUnit.test("Can set a value from a pivot header context menu", async function (assert) {
        const { env, model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        assert.strictEqual(getCellValue(model, "B3"), 10);
        assert.strictEqual(getCellValue(model, "B4"), 121.0);
        await addGlobalFilter(
            model,
            {
                id: "42",
                type: "relation",
                defaultValue: [41],
            },
            {
                pivot: { 1: { chain: "product_id", type: "many2one" } },
            }
        );
        assert.strictEqual(getCellValue(model, "B3"), "");
        assert.strictEqual(getCellValue(model, "B4"), 121);
        selectCell(model, "A3");
        assert.strictEqual(
            getCell(model, "B3").content,
            '=ODOO.PIVOT(1,"probability","product_id",37)',
            "the formula field matches the filter"
        );
        const root = cellMenuRegistry
            .getMenuItems()
            .find((item) => item.id === "use_global_filter");
        assert.strictEqual(root.isVisible(env), true);
        await root.execute(env);
        await nextTick();
        assert.strictEqual(getCellValue(model, "B3"), 10);
        assert.strictEqual(getCellValue(model, "B4"), "");
        await root.execute(env);
        await nextTick();
        assert.strictEqual(getCellValue(model, "B3"), 10);
        assert.strictEqual(getCellValue(model, "B4"), 121);

        model.dispatch("CREATE_SHEET", { sheetId: "42" });
        setCellContent(model, "A1", `=ODOO.PIVOT.TABLE("1")`, "42");
        selectCell(model, "A3", "42");
        assert.strictEqual(root.isVisible(env), true);
        await root.execute(env);
        await nextTick();
        // prettier-ignore
        assert.deepEqual(getEvaluatedGrid(model, "A1:B4"), [
            ["(#1) Partner Pivot",  "Total"],
            ["",                    "Probability"],
            ["xphone",              10],
            ["Total",               10],
        ])
        await root.execute(env);
        await nextTick();
        // prettier-ignore
        assert.deepEqual(getEvaluatedGrid(model, "A1:B5"), [
            ["(#1) Partner Pivot",  "Total"],
            ["",                    "Probability"],
            ["xphone",              10],
            ["xpad",                121],
            ["Total",               131],
        ])
    });

    QUnit.test("Can open context menu with positional argument", async function (assert) {
        const { env, model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        setCellContent(model, "B3", '=ODOO.PIVOT.HEADER(1, "#product_id", 1)');
        await addGlobalFilter(
            model,
            {
                id: "42",
                type: "relation",
                defaultValue: [],
            },
            { pivot: { 1: { chain: "product_id", type: "many2one" } } }
        );
        selectCell(model, "B3");
        const root = cellMenuRegistry
            .getMenuItems()
            .find((item) => item.id === "use_global_filter");
        assert.strictEqual(root.isVisible(env), true);
    });

    QUnit.test("Can open context menu without argument", async function (assert) {
        const { env, model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        assert.strictEqual(getCell(model, "B5").content, '=ODOO.PIVOT(1,"probability")');
        await addGlobalFilter(
            model,
            {
                id: "42",
                type: "relation",
                defaultValue: [],
            },
            { pivot: { 1: { chain: "product_id", type: "many2one" } } }
        );
        selectCell(model, "B5");
        const root = cellMenuRegistry
            .getMenuItems()
            .find((item) => item.id === "use_global_filter");
        assert.strictEqual(root.isVisible(env), false);

        model.dispatch("CREATE_SHEET", { sheetId: "42" });
        setCellContent(model, "A1", `=ODOO.PIVOT.TABLE("1")`, "42");
        selectCell(model, "B5", "42");
        assert.strictEqual(root.isVisible(env), false);
    });

    QUnit.test(
        "Can open context menu when there is a filter with no field defined",
        async function (assert) {
            const { env, model } = await createSpreadsheetWithPivot({
                arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
            });
            await addGlobalFilter(model, {
                id: "42",
                type: "relation",
                defaultValue: [],
            });
            selectCell(model, "B3");
            const root = cellMenuRegistry
                .getMenuItems()
                .find((item) => item.id === "use_global_filter");
            assert.strictEqual(root.isVisible(env), false);

            model.dispatch("CREATE_SHEET", { sheetId: "42" });
            setCellContent(model, "A1", `=ODOO.PIVOT.TABLE("1")`, "42");
            selectCell(model, "B3", "42");
            assert.strictEqual(root.isVisible(env), false);
        }
    );

    QUnit.test(
        "Set as filter is not visible if there is no pivot formula",
        async function (assert) {
            const { env, model } = await createSpreadsheetWithPivot();
            selectCell(model, "A1");
            setCellContent(model, "A1", "=1");
            const root = cellMenuRegistry
                .getMenuItems()
                .find((item) => item.id === "use_global_filter");
            assert.strictEqual(root.isVisible(env), false);
        }
    );

    QUnit.test(
        "Set as filter is not visible on empty cells of ODOO.PIVOT.TABLE",
        async function (assert) {
            const { env, model } = await createSpreadsheetWithPivot();
            const root = cellMenuRegistry
                .getMenuItems()
                .find((item) => item.id === "use_global_filter");
            model.dispatch("CREATE_SHEET", { sheetId: "42" });
            setCellContent(model, "A1", `=ODOO.PIVOT.TABLE("1")`, "42");
            selectCell(model, "A1", "42");
            assert.strictEqual(root.isVisible(env), false);
            selectCell(model, "A2", "42");
            assert.strictEqual(root.isVisible(env), false);
        }
    );

    QUnit.test(
        "menu to set filter value is not visible if no filter matches",
        async function (assert) {
            const { env, model } = await createSpreadsheetWithPivot();
            await addGlobalFilter(
                model,
                {
                    id: "42",
                    type: "relation",
                    defaultValue: [41],
                },
                {
                    pivot: { 1: { chain: "product_id", type: "many2one" } },
                }
            );
            selectCell(model, "A30");
            const root = cellMenuRegistry
                .getMenuItems()
                .find((item) => item.id === "use_global_filter");
            assert.strictEqual(root.isVisible(env), false);
        }
    );

    QUnit.test(
        "menu to set filter value is only visible on the PIVOT.HEADER formulas",
        async function (assert) {
            const { env, model } = await createSpreadsheetWithPivot({
                arch: /*xml*/ `
                    <pivot>
                        <field name="product_id" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`,
            });
            await addGlobalFilter(model, testGlobalFilter, testFieldMatching);
            const root = cellMenuRegistry
                .getMenuItems()
                .find((item) => item.id === "use_global_filter");

            selectCell(model, "A3");
            assert.ok(getCell(model, "A3").content.includes("ODOO.PIVOT.HEADER("));
            assert.strictEqual(root.isVisible(env), true);

            selectCell(model, "B3");
            assert.ok(getCell(model, "B3").content.includes("ODOO.PIVOT("));
            assert.strictEqual(root.isVisible(env), false);
        }
    );

    QUnit.test(
        "menu to set filter value is only visible on the the header of a PIVOT.TABLE",
        async function (assert) {
            const { env, model } = await createSpreadsheetWithPivot({
                arch: /*xml*/ `
                    <pivot>
                        <field name="product_id" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`,
            });
            await addGlobalFilter(model, testGlobalFilter, testFieldMatching);
            const sheetIdFrom = model.getters.getActiveSheetId();
            model.dispatch("CREATE_SHEET", { sheetId: "42", position: 1 });
            model.dispatch("ACTIVATE_SHEET", { sheetIdFrom, sheetIdTo: "42" });
            setCellContent(model, "A1", '=ODOO.PIVOT.TABLE("1")');
            const root = cellMenuRegistry
                .getMenuItems()
                .find((item) => item.id === "use_global_filter");

            selectCell(model, "A3"); // Header cell
            assert.strictEqual(root.isVisible(env), true);

            selectCell(model, "B3"); // Not a header cell
            assert.strictEqual(root.isVisible(env), false);
        }
    );

    QUnit.test("UNDO/REDO filter creation with multiple field matchings", async function (assert) {
        const { model } = await createSpreadsheetWithPivot();
        assert.strictEqual(getCellValue(model, "B4"), 11);
        const filter = {
            id: "42",
            type: "relation",
            defaultValue: [2],
        };
        await addGlobalFilter(model, filter, {
            pivot: { 1: { chain: "product_id", type: "many2one" } },
        });
        model.dispatch("REQUEST_UNDO");
        assert.equal(model.getters.getGlobalFilters().length, 0);
        model.dispatch("REQUEST_REDO");
        assert.equal(model.getters.getGlobalFilters().length, 1);
    });

    QUnit.test(
        "UNDO/REDO filter creation reloads the related field matchings",
        async function (assert) {
            const { model } = await createSpreadsheetWithPivot();
            assert.strictEqual(getCellValue(model, "B4"), 11);
            const filter = {
                id: "42",
                type: "relation",
                defaultValue: [2],
            };
            await addGlobalFilter(model, filter, {
                pivot: { 1: { chain: "product_id", type: "many2one" } },
            });
            assert.strictEqual(getCellValue(model, "B4"), "");
            model.dispatch("REQUEST_UNDO");
            assert.equal(model.getters.getGlobalFilters().length, 0);
            await waitForDataSourcesLoaded(model);
            assert.strictEqual(getCellValue(model, "B4"), 11);
            model.dispatch("REQUEST_REDO");
            assert.equal(model.getters.getGlobalFilters().length, 1);
            await waitForDataSourcesLoaded(model);
            assert.strictEqual(getCellValue(model, "B4"), "");
        }
    );
});
