/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";
import { nextTick, click } from "@web/../tests/helpers/utils";
import { getBasicData } from "@spreadsheet/../tests/utils/data";
import { getCell, getCellFormula } from "@spreadsheet/../tests/utils/getters";
import { selectCell } from "@spreadsheet/../tests/utils/commands";
import { createSpreadsheetFromPivotView } from "../../utils/pivot_helpers";
import { doMenuAction } from "@spreadsheet/../tests/utils/ui";

const { topbarMenuRegistry } = spreadsheet.registries;

const insertPivotCellPath = ["data", "insert_pivot", "insert_pivot_cell", "insert_pivot_cell_1"];

QUnit.module("documents_spreadsheet > Pivot missing values", {}, function () {
    QUnit.test("Open pivot dialog and insert a value, with UNDO/REDO", async function (assert) {
        assert.expect(4);

        const { model, env } = await createSpreadsheetFromPivotView();
        selectCell(model, "D8");
        await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
        await nextTick();
        assert.containsOnce(document.body, ".o_pivot_table_dialog");
        await click(document.body.querySelectorAll(".o_pivot_table_dialog tr th")[1]);
        assert.equal(getCellFormula(model, "D8"), getCellFormula(model, "B1"));
        model.dispatch("REQUEST_UNDO");
        assert.equal(getCell(model, "D8"), undefined);
        model.dispatch("REQUEST_REDO");
        assert.equal(getCellFormula(model, "D8"), getCellFormula(model, "B1"));
    });

    QUnit.test("pivot dialog with row date field (day)", async function (assert) {
        const { env } = await createSpreadsheetFromPivotView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,pivot": /*xml*/ `
                        <pivot>
                            <field name="date" interval="day" type="row"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                    "partner,false,search": `<search/>`,
                },
            },
        });
        await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
        await nextTick();
        const firstRowHeader = document.body.querySelectorAll(".o_pivot_table_dialog tr th")[3];
        assert.strictEqual(firstRowHeader.textContent, "4/14/2016");
    });

    QUnit.test("pivot dialog with col date field (day)", async function (assert) {
        const { env } = await createSpreadsheetFromPivotView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,pivot": /*xml*/ `
                        <pivot>
                            <field name="date" interval="day" type="col"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                    "partner,false,search": `<search/>`,
                },
            },
        });
        await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
        await nextTick();
        const firstRowHeader = document.body.querySelectorAll(".o_pivot_table_dialog tr th")[1];
        assert.strictEqual(firstRowHeader.textContent, "4/14/2016");
    });

    QUnit.test(
        "Insert missing value modal can show only the values not used in the current sheet",
        async function (assert) {
            assert.expect(4);

            const { model, env } = await createSpreadsheetFromPivotView();
            const missingValue = getCellFormula(model, "B3");
            selectCell(model, "B3");
            model.dispatch("DELETE_CONTENT", {
                sheetId: model.getters.getActiveSheetId(),
                target: model.getters.getSelectedZones(),
            });
            selectCell(model, "D8");
            await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
            await nextTick();
            assert.containsOnce(document.body, ".o_missing_value");
            await click(document.body.querySelector("input#missing_values"));
            await nextTick();
            assert.containsOnce(document.body, ".o_missing_value");
            assert.containsN(document.body, ".o_pivot_table_dialog th", 4);
            await click(document.body.querySelector(".o_missing_value"));
            assert.equal(getCellFormula(model, "D8"), missingValue);
        }
    );

    QUnit.test("Insert missing pivot value with two level of grouping", async function (assert) {
        assert.expect(4);

        const { model, env } = await createSpreadsheetFromPivotView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,pivot": `
                            <pivot string="Partners">
                                <field name="foo" type="col"/>
                                <field name="bar" type="row"/>
                                <field name="product_id" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
                    "partner,false,search": `<search/>`,
                },
            },
        });
        selectCell(model, "B5");
        model.dispatch("DELETE_CONTENT", {
            sheetId: model.getters.getActiveSheetId(),
            target: model.getters.getSelectedZones(),
        });
        selectCell(model, "D8");
        await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
        await nextTick();
        assert.containsOnce(document.body, ".o_missing_value");
        await click(document.body.querySelector("input#missing_values"));
        await nextTick();
        assert.containsOnce(document.body, ".o_missing_value");
        assert.containsN(document.body, ".o_pivot_table_dialog td", 1);
        assert.containsN(document.body, ".o_pivot_table_dialog th", 4);
    });

    QUnit.test(
        "Insert missing value modal can show only the values not used in the current sheet with multiple levels",
        async function (assert) {
            assert.expect(4);

            const { model, env } = await createSpreadsheetFromPivotView({
                serverData: {
                    models: getBasicData(),
                    views: {
                        "partner,false,pivot": `
                            <pivot string="Partners">
                                <field name="foo" type="col"/>
                                <field name="product_id" type="col"/>
                                <field name="bar" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
                        "partner,false,search": `<search/>`,
                    },
                },
            });
            const missingValue = getCellFormula(model, "C4");
            selectCell(model, "C4");
            model.dispatch("DELETE_CONTENT", {
                sheetId: model.getters.getActiveSheetId(),
                target: model.getters.getSelectedZones(),
            });
            selectCell(model, "J10");
            await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
            await nextTick();
            assert.containsOnce(document.body, ".o_missing_value");
            await click(document.body.querySelector("input#missing_values"));
            await nextTick();
            assert.containsOnce(document.body, ".o_missing_value");
            assert.containsN(document.body, ".o_pivot_table_dialog th", 5);
            await click(document.body.querySelector(".o_missing_value"));
            assert.equal(getCellFormula(model, "J10"), missingValue);
        }
    );

    QUnit.test(
        "Insert missing pivot value give the focus to the grid hidden input when model is closed",
        async function (assert) {
            const { model, env } = await createSpreadsheetFromPivotView({
                serverData: {
                    models: getBasicData(),
                    views: {
                        "partner,false,pivot": `
                            <pivot string="Partners">
                                <field name="foo" type="col"/>
                                <field name="bar" type="row"/>
                                <field name="product_id" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
                        "partner,false,search": `<search/>`,
                    },
                },
            });
            selectCell(model, "D8");
            await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
            await nextTick();
            assert.containsOnce(document.body, ".o_pivot_table_dialog");
            await click(document.body.querySelectorAll(".o_pivot_table_dialog tr th")[1]);
            assert.strictEqual(document.activeElement, document.querySelector(".o-grid div.o-composer"));
        }
    );

    QUnit.test("One col header as missing value should be displayed", async function (assert) {
        assert.expect(1);

        const { model, env } = await createSpreadsheetFromPivotView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,pivot": `
                            <pivot string="Partners">
                                <field name="foo" type="col"/>
                                <field name="bar" type="row"/>
                                <field name="product_id" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
                    "partner,false,search": `<search/>`,
                },
            },
        });
        selectCell(model, "B1");
        model.dispatch("DELETE_CONTENT", {
            sheetId: model.getters.getActiveSheetId(),
            target: model.getters.getSelectedZones(),
        });
        await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
        await nextTick();
        await click(document.body.querySelector("input#missing_values"));
        await nextTick();
        assert.containsOnce(document.body, ".o_missing_value");
    });

    QUnit.test("One row header as missing value should be displayed", async function (assert) {
        assert.expect(1);

        const { model, env } = await createSpreadsheetFromPivotView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,pivot": `
                            <pivot string="Partners">
                                <field name="foo" type="col"/>
                                <field name="bar" type="row"/>
                                <field name="product_id" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
                    "partner,false,search": `<search/>`,
                },
            },
        });
        selectCell(model, "A3");
        model.dispatch("DELETE_CONTENT", {
            sheetId: model.getters.getActiveSheetId(),
            target: model.getters.getSelectedZones(),
        });
        await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
        await nextTick();
        await click(document.body.querySelector("input#missing_values"));
        await nextTick();
        assert.containsOnce(document.body, ".o_missing_value");
    });

    QUnit.test(
        "A missing col in the total measures with a pivot of two GB of cols",
        async function (assert) {
            assert.expect(2);

            const { model, env } = await createSpreadsheetFromPivotView({
                serverData: {
                    models: getBasicData(),
                    views: {
                        "partner,false,pivot": `
                            <pivot string="Partners">
                                <field name="bar" type="col"/>
                                <field name="product_id" type="col"/>
                                <field name="probability" type="measure"/>
                                <field name="foo" type="measure"/>
                            </pivot>`,
                        "partner,false,search": `<search/>`,
                    },
                },
            });
            await nextTick();
            await nextTick();
            selectCell(model, "F4");
            model.dispatch("DELETE_CONTENT", {
                sheetId: model.getters.getActiveSheetId(),
                target: model.getters.getSelectedZones(),
            });
            await doMenuAction(topbarMenuRegistry, insertPivotCellPath, env);
            await nextTick();
            await click(document.body.querySelector("input#missing_values"));
            await nextTick();
            assert.containsOnce(document.body, ".o_missing_value");
            assert.containsN(document.body, ".o_pivot_table_dialog th", 5);
        }
    );
});
