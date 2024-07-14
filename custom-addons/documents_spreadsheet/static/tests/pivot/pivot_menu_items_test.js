/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";
import { nextTick, getFixture } from "@web/../tests/helpers/utils";
import { createSpreadsheet } from "../spreadsheet_test_utils";
import {
    getBasicData,
    getBasicPivotArch,
    getBasicServerData,
} from "@spreadsheet/../tests/utils/data";
import {
    getCell,
    getCellFormula,
    getCellValue,
    getEvaluatedCell,
} from "@spreadsheet/../tests/utils/getters";
import {
    addGlobalFilter,
    selectCell,
    setCellContent,
    setGlobalFilterValue,
} from "@spreadsheet/../tests/utils/commands";
import { createSpreadsheetFromPivotView } from "../utils/pivot_helpers";
import {
    createSpreadsheetWithPivot,
    insertPivotInSpreadsheet,
} from "@spreadsheet/../tests/utils/pivot";
import { session } from "@web/session";

const { toCartesian, toZone } = spreadsheet.helpers;
const { cellMenuRegistry, topbarMenuRegistry } = spreadsheet.registries;
import { doMenuAction } from "@spreadsheet/../tests/utils/ui";

let target;

const reinsertPivotPath = ["data", "insert_pivot", "reinsert_pivot", "reinsert_pivot_1"];

QUnit.module(
    "documents_spreadsheet > Pivot Menu Items",
    {
        beforeEach: function () {
            target = getFixture();
        },
    },
    function () {
        QUnit.test("Reinsert a pivot", async function (assert) {
            const { model, env } = await createSpreadsheetWithPivot();
            selectCell(model, "D8");
            await doMenuAction(topbarMenuRegistry, reinsertPivotPath, env);
            assert.equal(
                getCellFormula(model, "E10"),
                `=ODOO.PIVOT(1,"probability","bar","false","foo",1)`,
                "It should contain a pivot formula"
            );
        });

        QUnit.test("Reinsert a pivot with a contextual search domain", async function (assert) {
            const serverData = getBasicServerData();
            const uid = session.user_context.uid;
            serverData.models.partner.records = [{ id: 1, probability: 0.5, foo: uid }];
            serverData.views["partner,false,search"] = /* xml */ `
                <search>
                    <filter string="Filter" name="filter" domain="[('foo', '=', uid)]"/>
                </search>
            `;
            const { model, env } = await createSpreadsheetFromPivotView({
                serverData,
                additionalContext: { search_default_filter: 1 },
            });

            selectCell(model, "D8");
            await doMenuAction(topbarMenuRegistry, reinsertPivotPath, env);
            assert.equal(
                getCellFormula(model, "E10"),
                `=ODOO.PIVOT(1,"probability","bar","false","foo",${uid})`,
                "It should contain a pivot formula"
            );
        });

        QUnit.test("Reinsert a pivot in a too small sheet", async function (assert) {
            const { model, env } = await createSpreadsheetWithPivot();
            const sheetId = model.getters.getActiveSheetId();
            model.dispatch("CREATE_SHEET", { cols: 1, rows: 1, sheetId: "111" });
            model.dispatch("ACTIVATE_SHEET", {
                sheetIdFrom: sheetId,
                sheetIdTo: "111",
            });
            selectCell(model, "A1");
            await doMenuAction(topbarMenuRegistry, reinsertPivotPath, env);
            assert.equal(model.getters.getNumberCols("111"), 6);
            assert.equal(model.getters.getNumberRows("111"), 5);
            assert.equal(
                getCellFormula(model, "B3"),
                `=ODOO.PIVOT(1,"probability","bar","false","foo",1)`,
                "It should contain a pivot formula"
            );
        });

        QUnit.test("Reinsert a pivot with new data", async function (assert) {
            const data = getBasicData();

            const { model, env } = await createSpreadsheetWithPivot({
                serverData: {
                    models: data,
                    views: getBasicServerData().views,
                },
            });
            data.partner.records.push({
                active: true,
                id: 5,
                foo: 25, // <- New value inserted
                bar: false,
                date: "2016-12-11",
                product_id: 41,
                probability: 15,
                field_with_array_agg: 4,
                create_date: "2016-12-11",
                tag_ids: [],
            });
            selectCell(model, "D8");
            await doMenuAction(topbarMenuRegistry, reinsertPivotPath, env);
            assert.equal(getCellFormula(model, "I8"), `=ODOO.PIVOT.HEADER(1,"foo",25)`);
            assert.equal(
                getCellFormula(model, "I10"),
                `=ODOO.PIVOT(1,"probability","bar","false","foo",25)`
            );
        });

        QUnit.test("Reinsert a pivot with an updated record", async function (assert) {
            const data = getBasicData();

            const { model, env } = await createSpreadsheetWithPivot({
                serverData: {
                    models: data,
                    views: getBasicServerData().views,
                },
            });
            assert.equal(getCellValue(model, "B1"), 1);
            assert.equal(getCellValue(model, "C1"), 2);
            assert.equal(getCellValue(model, "D1"), 12);
            data.partner.records[0].foo = 99;
            data.partner.records[1].foo = 99;
            // updated measures
            data.partner.records[0].probability = 88;
            data.partner.records[1].probability = 77;
            await doMenuAction(topbarMenuRegistry, reinsertPivotPath, env);
            await nextTick();
            assert.equal(getCellValue(model, "D1"), 99, "The header should have been updated");
            assert.equal(getCellValue(model, "D4"), 77 + 88, "The value should have been updated");
        });

        QUnit.test(
            "Reinsert a pivot which has no formula on the sheet (meaning the data is not loaded)",
            async function (assert) {
                const spreadsheetData = {
                    sheets: [
                        {
                            id: "sheet1",
                        },
                    ],
                    pivots: {
                        1: {
                            id: 1,
                            colGroupBys: ["foo"],
                            domain: [],
                            measures: [{ field: "probability", operator: "avg" }],
                            model: "partner",
                            rowGroupBys: ["bar"],
                            context: {},
                        },
                    },
                };
                const serverData = getBasicServerData();
                serverData.models["documents.document"].records.push({
                    id: 45,
                    spreadsheet_data: JSON.stringify(spreadsheetData),
                    name: "Spreadsheet",
                    handler: "spreadsheet",
                });
                const { model, env } = await createSpreadsheet({
                    serverData,
                    spreadsheetId: 45,
                });
                await doMenuAction(topbarMenuRegistry, reinsertPivotPath, env);
                assert.equal(getCellFormula(model, "C1"), `=ODOO.PIVOT.HEADER(1,"foo",2)`);
                assert.equal(
                    getCellFormula(model, "C2"),
                    `=ODOO.PIVOT.HEADER(1,"foo",2,"measure","probability")`
                );
                assert.equal(
                    getCellFormula(model, "C3"),
                    `=ODOO.PIVOT(1,"probability","bar","false","foo",2)`
                );
                await nextTick();
                assert.equal(getCellValue(model, "C1"), 2);
                assert.equal(getCellValue(model, "C2"), "Probability");
                assert.equal(getCellValue(model, "C3"), 15);
            }
        );

        QUnit.test("Keep applying filter when pivot is re-inserted", async function (assert) {
            const { model, env } = await createSpreadsheetWithPivot({
                arch: /*xml*/ `
                    <pivot>
                        <field name="bar" type="col"/>
                        <field name="product_id" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`,
            });
            await addGlobalFilter(
                model,
                {
                    id: "42",
                    type: "relation",
                    label: "Filter",
                },
                {
                    pivot: {
                        1: {
                            chain: "product_id",
                            type: "many2one",
                        },
                    },
                }
            );
            await nextTick();
            await setGlobalFilterValue(model, {
                id: "42",
                value: [41],
            });
            await nextTick();
            assert.equal(getCellValue(model, "B3"), "", "The value should have been filtered");
            assert.equal(getCellValue(model, "C3"), "", "The value should have been filtered");
            await doMenuAction(topbarMenuRegistry, reinsertPivotPath, env);
            await nextTick();
            assert.equal(getCellValue(model, "B3"), "", "The value should still be filtered");
            assert.equal(getCellValue(model, "C3"), "", "The value should still be filtered");
        });

        QUnit.test("undo pivot reinsert", async function (assert) {
            const { model, env } = await createSpreadsheetWithPivot();
            selectCell(model, "D8");
            await doMenuAction(topbarMenuRegistry, reinsertPivotPath, env);
            assert.equal(
                getCellFormula(model, "E10"),
                `=ODOO.PIVOT(1,"probability","bar","false","foo",1)`,
                "It should contain a pivot formula"
            );
            model.dispatch("REQUEST_UNDO");
            assert.notOk(getCell(model, "E10"), "It should have removed the re-inserted pivot");
        });

        QUnit.test("reinsert pivot with anchor on merge but not top left", async function (assert) {
            const { model, env } = await createSpreadsheetWithPivot();
            const sheetId = model.getters.getActiveSheetId();
            assert.equal(
                getCellFormula(model, "B2"),
                `=ODOO.PIVOT.HEADER(1,"foo",1,"measure","probability")`,
                "It should contain a pivot formula"
            );
            model.dispatch("ADD_MERGE", {
                sheetId,
                target: [{ top: 0, bottom: 1, left: 0, right: 0 }],
                force: true,
            });
            selectCell(model, "A2"); // A1 and A2 are merged; select A2
            const { col, row } = toCartesian("A2");
            assert.ok(model.getters.isInMerge({ sheetId, col, row }));
            await doMenuAction(topbarMenuRegistry, reinsertPivotPath, env);
            assert.equal(
                getCellFormula(model, "B2"),
                `=ODOO.PIVOT.HEADER(1,"foo",1,"measure","probability")`,
                "It should contain a pivot formula"
            );
        });

        QUnit.test("Verify presence of pivot properties on pivot cell", async function (assert) {
            const { model, env } = await createSpreadsheetWithPivot();
            selectCell(model, "B2");
            const root = cellMenuRegistry.getAll().find((item) => item.id === "pivot_properties");
            assert.ok(root.isVisible(env));
        });

        QUnit.test("Verify absence of pivot properties on non-pivot cell", async function (assert) {
            const { model, env } = await createSpreadsheetWithPivot();
            selectCell(model, "Z26");
            const root = cellMenuRegistry.getAll().find((item) => item.id === "pivot_properties");
            assert.notOk(root.isVisible(env));
        });

        QUnit.test("Verify absence of pivot properties on formula with invalid pivot Id", async function (assert) {
            const { model, env } = await createSpreadsheetWithPivot();
            setCellContent(model, "A1", `=ODOO.PIVOT.HEADER("fakeId")`);
            const root = cellMenuRegistry.getAll().find((item) => item.id === "pivot_properties");
            assert.notOk(root.isVisible(env));
            setCellContent(model, "A1", `=ODOO.PIVOT("fakeId", "probability", "foo", 2)`);
            assert.notOk(root.isVisible(env));
        });

        QUnit.test(
            "verify absence of pivots in top menu bar in a spreadsheet without a pivot",
            async function (assert) {
                await createSpreadsheet();
                assert.containsNone(target, "div[data-id='pivots']");
            }
        );

        QUnit.test(
            "Verify presence of pivots in top menu bar in a spreadsheet with a pivot",
            async function (assert) {
                const { model, env } = await createSpreadsheetFromPivotView();
                await insertPivotInSpreadsheet(model, { arch: getBasicPivotArch() });
                assert.ok(
                    target.querySelector("div[data-id='data']"),
                    "The 'Pivots' menu should be in the dom"
                );

                const root = topbarMenuRegistry.getMenuItems().find((item) => item.id === "data");
                const children = root.children(env);
                assert.ok(children.find((c) => c.name(env) === "(#1) Partners by Foo"));
                assert.ok(children.find((c) => c.name(env) === "(#2) Partner Pivot"));
                // bottom children
                assert.ok(children.find((c) => c.name(env) === "Refresh all data"));
                assert.ok(children.find((c) => c.name(env) === "Insert pivot"));
                assert.ok(children.find((c) => c.name(env) === "Re-insert list"));

                const insertPivotChildren = children
                    .find((c) => c.name(env) === "Insert pivot")
                    .children(env);
                assert.ok(insertPivotChildren.find((c) => c.name(env) === "Re-insert pivot"));
                assert.ok(insertPivotChildren.find((c) => c.name(env) === "Insert pivot cell"));
            }
        );

        QUnit.test("Pivot focus changes on top bar menu click", async function (assert) {
            const { model, env } = await createSpreadsheetFromPivotView();
            await insertPivotInSpreadsheet(model, { arch: getBasicPivotArch() });

            env.openSidePanel("PIVOT_PROPERTIES_PANEL", {});
            assert.notOk(model.getters.getSelectedPivotId(), "No pivot should be selected");
            await doMenuAction(topbarMenuRegistry, ["data", "item_pivot_1"], env);
            assert.equal(
                model.getters.getSelectedPivotId(),
                "1",
                "The selected pivot should have id 1"
            );
            await doMenuAction(topbarMenuRegistry, ["data", "item_pivot_2"], env);
            assert.equal(
                model.getters.getSelectedPivotId(),
                "2",
                "The selected pivot should have id 2"
            );
        });

        QUnit.test(
            "Can rebuild the Odoo domain of records based on the according merged pivot cell",
            async function (assert) {
                const { webClient, model } = await createSpreadsheetFromPivotView();
                const env = {
                    ...webClient.env,
                    model,
                    services: {
                        ...model.config.custom.env.services,
                        action: {
                            doAction: (params) => {
                                assert.step(params.res_model);
                                assert.step(JSON.stringify(params.domain));
                            },
                        },
                    },
                };
                model.dispatch("ADD_MERGE", {
                    sheetId: model.getters.getActiveSheetId(),
                    target: [toZone("C3:D3")],
                    force: true, // there are data in D3
                });
                selectCell(model, "D3");
                await nextTick();
                const root = cellMenuRegistry
                    .getAll()
                    .find((item) => item.id === "pivot_see_records");
                await root.execute(env);
                assert.verifySteps(["partner", `[["foo","=",2],["bar","=",false]]`]);
            }
        );

        QUnit.test(
            "See records is visible even if the formula is lowercase",
            async function (assert) {
                const { env, model } = await createSpreadsheetWithPivot();
                selectCell(model, "B4");
                await nextTick();
                const root = cellMenuRegistry
                    .getAll()
                    .find((item) => item.id === "pivot_see_records");
                assert.ok(root.isVisible(env));
                setCellContent(
                    model,
                    "B4",
                    getCellFormula(model, "B4").replace("ODOO.PIVOT", "odoo.pivot")
                );
                assert.ok(root.isVisible(env));
            }
        );

        QUnit.test(
            "See records is not visible if the formula is in error",
            async function (assert) {
                const { env, model } = await createSpreadsheetWithPivot();
                selectCell(model, "B4");
                await nextTick();
                const root = cellMenuRegistry
                    .getAll()
                    .find((item) => item.id === "pivot_see_records");
                assert.ok(root.isVisible(env));
                setCellContent(
                    model,
                    "B4",
                    getCellFormula(model, "B4").replace(`ODOO.PIVOT(1`, `ODOO.PIVOT("5)`)
                ); //Invalid id
                assert.ok(getEvaluatedCell(model, "B4").error.message);
                assert.notOk(root.isVisible(env));
            }
        );
    }
);
