/** @odoo-module */

import {
    getCell,
    getCellContent,
    getCellFormula,
    getCellValue,
    getEvaluatedCell,
    getBorders,
} from "@spreadsheet/../tests/utils/getters";
import { createSpreadsheetWithPivot } from "@spreadsheet/../tests/utils/pivot";
import { getBasicPivotArch } from "@spreadsheet/../tests/utils/data";
import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";
import { addGlobalFilter, setCellContent } from "@spreadsheet/../tests/utils/commands";
import {
    createModelWithDataSource,
    waitForDataSourcesLoaded,
} from "@spreadsheet/../tests/utils/model";
import { makeDeferred, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { session } from "@web/session";
import { makeServerError } from "@web/../tests/helpers/mock_server";
import { getBasicServerData } from "../../utils/data";

import * as spreadsheet from "@odoo/o-spreadsheet";
const { DEFAULT_LOCALE } = spreadsheet.constants;

QUnit.module("spreadsheet > pivot plugin", {}, () => {
    QUnit.test("can select a Pivot from cell formula", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /* xml */ `
                <pivot>
                    <field name="product_id" type="col"/>
                    <field name="foo" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        const sheetId = model.getters.getActiveSheetId();
        const pivotId = model.getters.getPivotIdFromPosition({ sheetId, col: 2, row: 2 });
        model.dispatch("SELECT_PIVOT", { pivotId });
        const selectedPivotId = model.getters.getSelectedPivotId();
        assert.strictEqual(selectedPivotId, "1");
    });

    QUnit.test(
        "can select a Pivot from cell formula with '-' before the formula",
        async function (assert) {
            const { model } = await createSpreadsheetWithPivot({
                arch: /* xml */ `
                <pivot>
                    <field name="product_id" type="col"/>
                    <field name="foo" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
            });
            model.dispatch("SET_VALUE", {
                xc: "C3",
                text: `=-PIVOT("1","probability","bar","false","foo","2")`,
            });
            const sheetId = model.getters.getActiveSheetId();
            const pivotId = model.getters.getPivotIdFromPosition({ sheetId, col: 2, row: 2 });
            model.dispatch("SELECT_PIVOT", { pivotId });
            const selectedPivotId = model.getters.getSelectedPivotId();
            assert.strictEqual(selectedPivotId, "1");
        }
    );

    QUnit.test(
        "can select a Pivot from cell formula with other numerical values",
        async function (assert) {
            const { model } = await createSpreadsheetWithPivot({
                arch: /* xml */ `
                <pivot>
                    <field name="product_id" type="col"/>
                    <field name="foo" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
            });
            model.dispatch("SET_VALUE", {
                xc: "C3",
                text: `=3*PIVOT("1","probability","bar","false","foo","2")+2`,
            });
            const sheetId = model.getters.getActiveSheetId();
            const pivotId = model.getters.getPivotIdFromPosition({ sheetId, col: 2, row: 2 });
            model.dispatch("SELECT_PIVOT", { pivotId });
            const selectedPivotId = model.getters.getSelectedPivotId();
            assert.strictEqual(selectedPivotId, "1");
        }
    );

    QUnit.test(
        "can select a Pivot from cell formula where pivot is in a function call",
        async function (assert) {
            const { model } = await createSpreadsheetWithPivot({
                arch: /* xml */ `
            <pivot>
                <field name="product_id" type="col"/>
                <field name="foo" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
            });
            model.dispatch("SET_VALUE", {
                xc: "C3",
                text: `=SUM(PIVOT("1","probability","bar","false","foo","2"),PIVOT("1","probability","bar","false","foo","2"))`,
            });
            const sheetId = model.getters.getActiveSheetId();
            const pivotId = model.getters.getPivotIdFromPosition({ sheetId, col: 2, row: 2 });
            model.dispatch("SELECT_PIVOT", { pivotId });
            const selectedPivotId = model.getters.getSelectedPivotId();
            assert.strictEqual(selectedPivotId, "1");
        }
    );

    QUnit.test(
        "can select a Pivot from cell formula where the id is a reference",
        async function (assert) {
            const { model } = await createSpreadsheetWithPivot();
            setCellContent(model, "C3", `=ODOO.PIVOT(G10,"probability","bar","false","foo","2")+2`);
            setCellContent(model, "G10", "1");
            const sheetId = model.getters.getActiveSheetId();
            const pivotId = model.getters.getPivotIdFromPosition({ sheetId, col: 2, row: 2 });
            model.dispatch("SELECT_PIVOT", { pivotId });
            const selectedPivotId = model.getters.getSelectedPivotId();
            assert.strictEqual(selectedPivotId, "1");
        }
    );

    QUnit.test(
        "can select a Pivot from cell formula (Mix of test scenarios above)",
        async function (assert) {
            const { model } = await createSpreadsheetWithPivot({
                arch: /*xml*/ `
                    <pivot>
                        <field name="product_id" type="col"/>
                        <field name="foo" type="row"/>
                        <field name="probability" type="measure"/>
                    </pivot>`,
            });
            model.dispatch("SET_VALUE", {
                xc: "C3",
                text: `=3*SUM(PIVOT("1","probability","bar","false","foo","2"),PIVOT("1","probability","bar","false","foo","2"))+2*PIVOT("1","probability","bar","false","foo","2")`,
            });
            const sheetId = model.getters.getActiveSheetId();
            const pivotId = model.getters.getPivotIdFromPosition({ sheetId, col: 2, row: 2 });
            model.dispatch("SELECT_PIVOT", { pivotId });
            const selectedPivotId = model.getters.getSelectedPivotId();
            assert.strictEqual(selectedPivotId, "1");
        }
    );

    QUnit.test("Can remove a pivot with undo after editing a cell", async function (assert) {
        const { model } = await createSpreadsheetWithPivot();
        assert.ok(getCellContent(model, "B1").startsWith("=ODOO.PIVOT.HEADER"));
        setCellContent(model, "G10", "should be undoable");
        model.dispatch("REQUEST_UNDO");
        assert.equal(getCellContent(model, "G10"), "");
        // 2 REQUEST_UNDO because of the AUTORESIZE feature
        model.dispatch("REQUEST_UNDO");
        model.dispatch("REQUEST_UNDO");
        assert.equal(getCellContent(model, "B1"), "");
        assert.equal(model.getters.getPivotIds().length, 0);
    });

    QUnit.test("rename pivot with empty name is refused", async (assert) => {
        const { model } = await createSpreadsheetWithPivot();
        const result = model.dispatch("RENAME_ODOO_PIVOT", {
            pivotId: "1",
            name: "",
        });
        assert.deepEqual(result.reasons, [CommandResult.EmptyName]);
    });

    QUnit.test("rename pivot with incorrect id is refused", async (assert) => {
        const { model } = await createSpreadsheetWithPivot();
        const result = model.dispatch("RENAME_ODOO_PIVOT", {
            pivotId: "invalid",
            name: "name",
        });
        assert.deepEqual(result.reasons, [CommandResult.PivotIdNotFound]);
    });

    QUnit.test("Undo/Redo for RENAME_ODOO_PIVOT", async function (assert) {
        const { model } = await createSpreadsheetWithPivot();
        assert.equal(model.getters.getPivotName("1"), "Partner Pivot");
        model.dispatch("RENAME_ODOO_PIVOT", { pivotId: "1", name: "test" });
        assert.equal(model.getters.getPivotName("1"), "test");
        model.dispatch("REQUEST_UNDO");
        assert.equal(model.getters.getPivotName("1"), "Partner Pivot");
        model.dispatch("REQUEST_REDO");
        assert.equal(model.getters.getPivotName("1"), "test");
    });

    QUnit.test("Can delete pivot", async function (assert) {
        const { model } = await createSpreadsheetWithPivot();
        model.dispatch("REMOVE_PIVOT", { pivotId: "1" });
        assert.strictEqual(model.getters.getPivotIds().length, 0);
        const B4 = getEvaluatedCell(model, "B4");
        assert.equal(B4.error.message, `There is no pivot with id "1"`);
        assert.equal(B4.value, `#ERROR`);
    });

    QUnit.test("Can undo/redo a delete pivot", async function (assert) {
        const { model } = await createSpreadsheetWithPivot();
        const value = getEvaluatedCell(model, "B4").value;
        model.dispatch("REMOVE_PIVOT", { pivotId: "1" });
        model.dispatch("REQUEST_UNDO");
        assert.strictEqual(model.getters.getPivotIds().length, 1);
        let B4 = getEvaluatedCell(model, "B4");
        assert.equal(B4.error, undefined);
        assert.equal(B4.value, value);
        model.dispatch("REQUEST_REDO");
        assert.strictEqual(model.getters.getPivotIds().length, 0);
        B4 = getEvaluatedCell(model, "B4");
        assert.equal(B4.error.message, `There is no pivot with id "1"`);
        assert.equal(B4.value, `#ERROR`);
    });

    QUnit.test("Format header displays an error for non-existing field", async function (assert) {
        const { model } = await createSpreadsheetWithPivot();
        setCellContent(model, "G10", `=ODOO.PIVOT.HEADER("1", "measure", "non-existing")`);
        setCellContent(model, "G11", `=ODOO.PIVOT.HEADER("1", "non-existing", "bla")`);
        await nextTick();
        assert.equal(getCellValue(model, "G10"), "#ERROR");
        assert.equal(getCellValue(model, "G11"), "#ERROR");
        assert.equal(
            getEvaluatedCell(model, "G10").error.message,
            "Field non-existing does not exist"
        );
        assert.equal(
            getEvaluatedCell(model, "G11").error.message,
            "Field non-existing does not exist"
        );
    });

    QUnit.test(
        "user context is combined with pivot context to fetch data",
        async function (assert) {
            const context = {
                allowed_company_ids: [15],
                tz: "bx",
                lang: "FR",
                uid: 4,
            };
            const testSession = {
                uid: 4,
                user_companies: {
                    allowed_companies: {
                        15: { id: 15, name: "Hermit" },
                        16: { id: 16, name: "Craft" },
                    },
                    current_company: 15,
                },
                user_context: context,
            };
            const spreadsheetData = {
                sheets: [
                    {
                        id: "sheet1",
                        cells: {
                            A1: { content: `=ODOO.PIVOT(1, "probability")` },
                        },
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
                        context: {
                            allowed_company_ids: [16],
                            default_stage_id: 9,
                            search_default_stage_id: 90,
                            tz: "nz",
                            lang: "EN",
                            uid: 40,
                        },
                    },
                },
            };
            const expectedFetchContext = {
                allowed_company_ids: [15],
                default_stage_id: 9,
                search_default_stage_id: 90,
                tz: "bx",
                lang: "FR",
                uid: 4,
            };
            patchWithCleanup(session, testSession);
            const model = await createModelWithDataSource({
                spreadsheetData,
                mockRPC: function (route, { model, method, kwargs }) {
                    if (model !== "partner") {
                        return;
                    }
                    switch (method) {
                        case "read_group":
                            assert.step("read_group");
                            assert.deepEqual(kwargs.context, expectedFetchContext, "read_group");
                            break;
                    }
                },
            });
            await waitForDataSourcesLoaded(model);
            assert.verifySteps(["read_group", "read_group", "read_group", "read_group"]);
        }
    );

    QUnit.test("fetch metadata only once per model", async function (assert) {
        const spreadsheetData = {
            sheets: [
                {
                    id: "sheet1",
                    cells: {
                        A1: { content: `=ODOO.PIVOT(1, "probability")` },
                        A2: { content: `=ODOO.PIVOT(2, "probability")` },
                    },
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
                2: {
                    id: 2,
                    colGroupBys: ["bar"],
                    domain: [],
                    measures: [{ field: "probability", operator: "max" }],
                    model: "partner",
                    rowGroupBys: ["foo"],
                    context: {},
                },
            },
        };
        const model = await createModelWithDataSource({
            spreadsheetData,
            mockRPC: function (route, { model, method, kwargs }) {
                if (model === "partner" && method === "fields_get") {
                    assert.step(`${model}/${method}`);
                } else if (model === "ir.model" && method === "search_read") {
                    assert.step(`${model}/${method}`);
                }
            },
        });
        await waitForDataSourcesLoaded(model);
        assert.verifySteps(["partner/fields_get"]);
    });

    QUnit.test("don't fetch pivot data if no formula use it", async function (assert) {
        const spreadsheetData = {
            pivots: {
                1: {
                    id: 1,
                    colGroupBys: ["foo"],
                    domain: [],
                    measures: [{ field: "probability", operator: "avg" }],
                    model: "partner",
                    rowGroupBys: ["bar"],
                },
            },
        };
        const model = await createModelWithDataSource({
            spreadsheetData,
            mockRPC: function (route, { model, method, kwargs }) {
                if (!["partner", "ir.model"].includes(model)) {
                    return;
                }
                assert.step(`${model}/${method}`);
            },
        });
        assert.verifySteps([]);
        setCellContent(model, "A1", `=ODOO.PIVOT("1", "probability")`);
        assert.equal(getCellValue(model, "A1"), "Loading...");
        await nextTick();
        assert.verifySteps([
            "partner/fields_get",
            "partner/read_group",
            "partner/read_group",
            "partner/read_group",
            "partner/read_group",
        ]);
        assert.equal(getCellValue(model, "A1"), 131);
    });

    QUnit.test("evaluates only once when two pivots are loading", async function (assert) {
        const spreadsheetData = {
            sheets: [{ id: "sheet1" }],
            pivots: {
                1: {
                    id: 1,
                    colGroupBys: ["foo"],
                    domain: [],
                    measures: [{ field: "probability", operator: "avg" }],
                    model: "partner",
                    rowGroupBys: ["bar"],
                },
                2: {
                    id: 2,
                    colGroupBys: ["foo"],
                    domain: [],
                    measures: [{ field: "probability", operator: "avg" }],
                    model: "partner",
                    rowGroupBys: ["bar"],
                },
            },
        };
        const model = await createModelWithDataSource({
            spreadsheetData,
        });
        model.config.custom.dataSources.addEventListener("data-source-updated", () =>
            assert.step("data-source-notified")
        );
        setCellContent(model, "A1", '=ODOO.PIVOT("1", "probability")');
        setCellContent(model, "A2", '=ODOO.PIVOT("2", "probability")');
        assert.equal(getCellValue(model, "A1"), "Loading...");
        assert.equal(getCellValue(model, "A2"), "Loading...");
        await nextTick();
        assert.equal(getCellValue(model, "A1"), 131);
        assert.equal(getCellValue(model, "A2"), 131);
        assert.verifySteps(["data-source-notified"], "evaluation after both pivots are loaded");
    });

    QUnit.test("concurrently load the same pivot twice", async function (assert) {
        const spreadsheetData = {
            sheets: [{ id: "sheet1" }],
            pivots: {
                1: {
                    id: 1,
                    colGroupBys: ["foo"],
                    domain: [],
                    measures: [{ field: "probability", operator: "avg" }],
                    model: "partner",
                    rowGroupBys: ["bar"],
                },
            },
        };
        const model = await createModelWithDataSource({
            spreadsheetData,
        });
        // the data loads first here, when we insert the first pivot function
        setCellContent(model, "A1", '=ODOO.PIVOT("1", "probability")');
        assert.equal(getCellValue(model, "A1"), "Loading...");
        // concurrently reload the same pivot
        model.dispatch("REFRESH_PIVOT", { id: 1 });
        await nextTick();
        assert.equal(getCellValue(model, "A1"), 131);
    });

    QUnit.test("display loading while data is not fully available", async function (assert) {
        const metadataPromise = makeDeferred();
        const dataPromise = makeDeferred();
        const spreadsheetData = {
            sheets: [
                {
                    id: "sheet1",
                    cells: {
                        A1: { content: `=ODOO.PIVOT.HEADER(1, "measure", "probability")` },
                        A2: { content: `=ODOO.PIVOT.HEADER(1, "product_id", 37)` },
                        A3: { content: `=ODOO.PIVOT(1, "probability")` },
                    },
                },
            ],
            pivots: {
                1: {
                    id: 1,
                    colGroupBys: ["product_id"],
                    domain: [],
                    measures: [{ field: "probability", operator: "avg" }],
                    model: "partner",
                    rowGroupBys: [],
                },
            },
        };
        const model = await createModelWithDataSource({
            spreadsheetData,
            mockRPC: async function (route, args, performRPC) {
                const { model, method, kwargs } = args;
                const result = await performRPC(route, args);
                if (model === "partner" && method === "fields_get") {
                    assert.step(`${model}/${method}`);
                    await metadataPromise;
                }
                if (
                    model === "partner" &&
                    method === "read_group" &&
                    kwargs.groupby[0] === "product_id"
                ) {
                    assert.step(`${model}/${method}`);
                    await dataPromise;
                }
                if (model === "product" && method === "read") {
                    assert.ok(false, "should not be called because data is put in cache");
                }
                return result;
            },
        });
        assert.strictEqual(getCellValue(model, "A1"), "Loading...");
        assert.strictEqual(getCellValue(model, "A2"), "Loading...");
        assert.strictEqual(getCellValue(model, "A3"), "Loading...");
        metadataPromise.resolve();
        await nextTick();
        setCellContent(model, "A10", "1"); // trigger a new evaluation (might also be caused by other async formulas resolving)
        assert.strictEqual(getCellValue(model, "A1"), "Loading...");
        assert.strictEqual(getCellValue(model, "A2"), "Loading...");
        assert.strictEqual(getCellValue(model, "A3"), "Loading...");
        dataPromise.resolve();
        await nextTick();
        setCellContent(model, "A10", "2");
        assert.strictEqual(getCellValue(model, "A1"), "Probability");
        assert.strictEqual(getCellValue(model, "A2"), "xphone");
        assert.strictEqual(getCellValue(model, "A3"), 131);
        assert.verifySteps(["partner/fields_get", "partner/read_group"]);
    });

    QUnit.test("pivot grouped by char field which represents numbers", async function (assert) {
        const serverData = getBasicServerData();
        serverData.models.partner.records = [
            { id: 1, name: "111", probability: 11 },
            { id: 2, name: "000111", probability: 15 },
        ];

        const { model } = await createSpreadsheetWithPivot({
            serverData,
            arch: /*xml*/ `
                <pivot>
                    <field name="name" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        assert.strictEqual(getCell(model, "A3").content, '=ODOO.PIVOT.HEADER(1,"name","000111")');
        assert.strictEqual(getCell(model, "A4").content, '=ODOO.PIVOT.HEADER(1,"name",111)');
        assert.strictEqual(getEvaluatedCell(model, "A3").value, "000111");
        assert.strictEqual(getEvaluatedCell(model, "A4").value, "111");
        assert.strictEqual(
            getCell(model, "B3").content,
            '=ODOO.PIVOT(1,"probability","name","000111")'
        );
        assert.strictEqual(getCell(model, "B4").content, '=ODOO.PIVOT(1,"probability","name",111)');
        assert.strictEqual(getEvaluatedCell(model, "B3").value, 15);
        assert.strictEqual(getEvaluatedCell(model, "B4").value, 11);
    });

    QUnit.test("relational PIVOT.HEADER with missing id", async function (assert) {
        assert.expect(1);

        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="col"/>
                    <field name="bar" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        const sheetId = model.getters.getActiveSheetId();
        model.dispatch("UPDATE_CELL", {
            col: 4,
            row: 9,
            content: `=ODOO.PIVOT.HEADER("1", "product_id", "1111111")`,
            sheetId,
        });
        await waitForDataSourcesLoaded(model);
        assert.equal(
            getEvaluatedCell(model, "E10").error.message,
            "Unable to fetch the label of 1111111 of model product"
        );
    });

    QUnit.test("relational PIVOT.HEADER with undefined id", async function (assert) {
        assert.expect(2);

        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        setCellContent(model, "F10", `=ODOO.PIVOT.HEADER("1", "product_id", A25)`);
        assert.equal(getCell(model, "A25"), null, "the cell should be empty");
        await waitForDataSourcesLoaded(model);
        assert.equal(getCellValue(model, "F10"), "None");
    });

    QUnit.test("Verify pivot measures are correctly computed :)", async function (assert) {
        assert.expect(4);

        const { model } = await createSpreadsheetWithPivot();
        assert.equal(getCellValue(model, "B4"), 11);
        assert.equal(getCellValue(model, "C3"), 15);
        assert.equal(getCellValue(model, "D4"), 10);
        assert.equal(getCellValue(model, "E4"), 95);
    });

    QUnit.test("aggregate to 0", async function (assert) {
        const serverData = getBasicServerData();
        serverData.models.partner.records = [
            { id: 1, name: "A", probability: 10 },
            { id: 2, name: "B", probability: -10 },
        ];

        const { model } = await createSpreadsheetWithPivot({
            serverData,
            arch: /*xml*/ `
                <pivot>
                    <field name="name" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        setCellContent(model, "A1", '=ODOO.PIVOT(1, "probability", "name", "A")');
        setCellContent(model, "A2", '=ODOO.PIVOT(1, "probability", "name", "B")');
        setCellContent(model, "A3", '=ODOO.PIVOT(1, "probability")');
        assert.strictEqual(getEvaluatedCell(model, "A1").value, 10);
        assert.strictEqual(getEvaluatedCell(model, "A2").value, -10);
        assert.strictEqual(getEvaluatedCell(model, "A3").value, 0);
    });

    QUnit.test("can import/export sorted pivot", async (assert) => {
        const spreadsheetData = {
            pivots: {
                1: {
                    id: "1",
                    colGroupBys: ["foo"],
                    domain: [],
                    measures: [{ field: "probability" }],
                    model: "partner",
                    rowGroupBys: ["bar"],
                    sortedColumn: {
                        measure: "probability",
                        order: "asc",
                        groupId: [[], [1]],
                    },
                    name: "A pivot",
                    context: {},
                    fieldMatching: {},
                },
            },
        };
        const model = await createModelWithDataSource({ spreadsheetData });
        assert.deepEqual(model.getters.getPivotDefinition(1).sortedColumn, {
            measure: "probability",
            order: "asc",
            groupId: [[], [1]],
        });
        assert.deepEqual(model.exportData().pivots, spreadsheetData.pivots);
    });

    QUnit.test("can import (export) contextual domain", async (assert) => {
        const uid = session.user_context.uid;
        const spreadsheetData = {
            pivots: {
                1: {
                    id: "1",
                    colGroupBys: [],
                    domain: '[("foo", "=", uid)]',
                    measures: [{ field: "probability" }],
                    model: "partner",
                    rowGroupBys: [],
                    name: "A pivot",
                },
            },
        };
        const model = await createModelWithDataSource({
            spreadsheetData,
            mockRPC: function (route, args) {
                if (args.method === "read_group") {
                    assert.deepEqual(args.kwargs.domain, [["foo", "=", uid]]);
                    assert.step("read_group");
                }
            },
        });
        setCellContent(model, "A1", '=ODOO.PIVOT(1, "probability")'); // load the data (and check the rpc domain)
        await nextTick();
        assert.strictEqual(
            model.exportData().pivots[1].domain,
            '[("foo", "=", uid)]',
            "the domain is exported with the dynamic parts"
        );
        assert.verifySteps(["read_group"]);
    });

    QUnit.test("Can group by many2many field ", async (assert) => {
        const { model } = await createSpreadsheetWithPivot({
            arch: /* xml */ `
            <pivot>
                <field name="foo" type="col"/>
                <field name="tag_ids" type="row"/>
                <field name="probability" type="measure"/>
            </pivot>`,
        });
        assert.equal(getCellFormula(model, "A3"), '=ODOO.PIVOT.HEADER(1,"tag_ids","false")');
        assert.equal(getCellFormula(model, "A4"), '=ODOO.PIVOT.HEADER(1,"tag_ids",42)');
        assert.equal(getCellFormula(model, "A5"), '=ODOO.PIVOT.HEADER(1,"tag_ids",67)');

        assert.equal(
            getCellFormula(model, "B3"),
            '=ODOO.PIVOT(1,"probability","tag_ids","false","foo",1)'
        );
        assert.equal(
            getCellFormula(model, "B4"),
            '=ODOO.PIVOT(1,"probability","tag_ids",42,"foo",1)'
        );
        assert.equal(
            getCellFormula(model, "B5"),
            '=ODOO.PIVOT(1,"probability","tag_ids",67,"foo",1)'
        );

        assert.equal(
            getCellFormula(model, "C3"),
            '=ODOO.PIVOT(1,"probability","tag_ids","false","foo",2)'
        );
        assert.equal(
            getCellFormula(model, "C4"),
            '=ODOO.PIVOT(1,"probability","tag_ids",42,"foo",2)'
        );
        assert.equal(
            getCellFormula(model, "C5"),
            '=ODOO.PIVOT(1,"probability","tag_ids",67,"foo",2)'
        );

        assert.equal(getCellValue(model, "A3"), "None");
        assert.equal(getCellValue(model, "A4"), "isCool");
        assert.equal(getCellValue(model, "A5"), "Growing");
        assert.equal(getCellValue(model, "B3"), "");
        assert.equal(getCellValue(model, "B4"), "11");
        assert.equal(getCellValue(model, "B5"), "11");
        assert.equal(getCellValue(model, "C3"), "");
        assert.equal(getCellValue(model, "C4"), "15");
        assert.equal(getCellValue(model, "C5"), "");
    });

    QUnit.test("PIVOT.HEADER grouped by date field without value", async function (assert) {
        for (const interval of ["day", "week", "month", "quarter", "year"]) {
            const { model } = await createSpreadsheetWithPivot({
                arch: /* xml */ `
                    <pivot>
                        <field name="date" interval="${interval}" type="col"/>
                        <field name="foo" type="measure"/>
                    </pivot>`,
            });
            setCellContent(model, "A1", `=ODOO.PIVOT.HEADER(1, "date:${interval}", "false")`);
            assert.equal(getCellValue(model, "A1"), "None");
        }
    });

    QUnit.test("PIVOT formulas are correctly formatted at evaluation", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /* xml */ `
                <pivot>
                    <field name="product_id" type="col"/>
                    <field name="name" type="row"/>
                    <field name="foo" type="measure"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        assert.strictEqual(getEvaluatedCell(model, "B3").format, "0");
        assert.strictEqual(getEvaluatedCell(model, "C3").format, "#,##0.00");
    });

    QUnit.test(
        "PIVOT formulas with monetary measure are correctly formatted at evaluation",
        async function (assert) {
            const { model } = await createSpreadsheetWithPivot({
                arch: /* xml */ `
                <pivot>
                    <field name="product_id" type="col"/>
                    <field name="name" type="row"/>
                    <field name="pognon" type="measure"/>
                </pivot>`,
            });
            assert.strictEqual(getEvaluatedCell(model, "B3").format, "#,##0.00[$€]");
        }
    );

    QUnit.test("PIVOT.HEADER day are correctly formatted at evaluation", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /* xml */ `
                <pivot>
                    <field name="date" interval="day" type="col"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
        });
        assert.strictEqual(getEvaluatedCell(model, "B1").format, "m/d/yyyy");
        assert.strictEqual(getEvaluatedCell(model, "B1").value, 42474);
        assert.strictEqual(getEvaluatedCell(model, "B1").formattedValue, "4/14/2016");
    });

    QUnit.test("PIVOT.HEADER week are correctly formatted at evaluation", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /* xml */ `
                <pivot>
                    <field name="date" interval="week" type="col"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
        });
        assert.strictEqual(getEvaluatedCell(model, "B1").format, undefined);
        assert.strictEqual(getEvaluatedCell(model, "B1").value, "W15 2016");
        assert.strictEqual(getEvaluatedCell(model, "B1").formattedValue, "W15 2016");
    });

    QUnit.test("PIVOT.HEADER month are correctly formatted at evaluation", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /* xml */ `
                <pivot>
                    <field name="date" interval="month" type="col"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
        });
        assert.strictEqual(getEvaluatedCell(model, "B1").format, "mmmm yyyy");
        assert.strictEqual(getEvaluatedCell(model, "B1").value, 42461);
        assert.strictEqual(getEvaluatedCell(model, "B1").formattedValue, "April 2016");
    });

    QUnit.test(
        "PIVOT.HEADER quarter are correctly formatted at evaluation",
        async function (assert) {
            const { model } = await createSpreadsheetWithPivot({
                arch: /* xml */ `
                <pivot>
                    <field name="date" interval="quarter" type="col"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
            });
            assert.strictEqual(getEvaluatedCell(model, "B1").format, undefined);
            assert.strictEqual(getEvaluatedCell(model, "B1").value, "Q2 2016");
            assert.strictEqual(getEvaluatedCell(model, "B1").formattedValue, "Q2 2016");
        }
    );

    QUnit.test("PIVOT.HEADER year are correctly formatted at evaluation", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /* xml */ `
                <pivot>
                    <field name="date" interval="year" type="col"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
        });
        assert.strictEqual(getEvaluatedCell(model, "B1").format, "0");
        assert.strictEqual(getEvaluatedCell(model, "B1").value, 2016);
        assert.strictEqual(getEvaluatedCell(model, "B1").formattedValue, "2016");
    });

    QUnit.test(
        "PIVOT.HEADER formulas are correctly formatted at evaluation",
        async function (assert) {
            const { model } = await createSpreadsheetWithPivot({
                arch: /* xml */ `
                <pivot>
                    <field name="date" interval="day" type="col"/>
                    <field name="probability" type="row"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
            });
            assert.strictEqual(getEvaluatedCell(model, "A3").format, "#,##0.00");
            assert.strictEqual(getEvaluatedCell(model, "B1").format, "m/d/yyyy");
            assert.strictEqual(getEvaluatedCell(model, "B2").format, undefined);
        }
    );

    QUnit.test("PIVOT.HEADER date formats are locale dependant", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /* xml */ `
                <pivot>
                    <field name="date" interval="day" type="col"/>
                    <field name="probability" type="row"/>
                    <field name="foo" type="measure"/>
                </pivot>`,
        });
        model.dispatch("UPDATE_LOCALE", {
            locale: { ...DEFAULT_LOCALE, dateFormat: "dd/mm/yyyy" },
        });
        assert.strictEqual(getEvaluatedCell(model, "B1").format, "dd/mm/yyyy");
    });

    QUnit.test(
        "Pivot header zone and total row will have correct borders",
        async function (assert) {
            const { model } = await createSpreadsheetWithPivot({
                arch: getBasicPivotArch(),
            });
            const leftBorder = { left: { style: "thin", color: "#2D7E84" } };
            const rightBorder = { right: { style: "thin", color: "#2D7E84" } };
            const topBorder = { top: { style: "thin", color: "#2D7E84" } };
            const bottomBorder = { bottom: { style: "thin", color: "#2D7E84" } };
            assert.deepEqual(getBorders(model, "A1"), { ...leftBorder, ...topBorder });
            assert.deepEqual(getBorders(model, "A2"), { ...leftBorder, ...bottomBorder });
            assert.deepEqual(getBorders(model, "A3"), { ...leftBorder, ...topBorder });
            assert.deepEqual(getBorders(model, "B1"), topBorder);
            assert.deepEqual(getBorders(model, "B2"), bottomBorder);
            assert.deepEqual(getBorders(model, "C3"), topBorder);
            assert.deepEqual(getBorders(model, "F1"), { ...rightBorder, ...topBorder });
            assert.deepEqual(getBorders(model, "F2"), { ...rightBorder, ...bottomBorder });
            assert.deepEqual(getBorders(model, "F3"), { ...rightBorder, ...topBorder });
            assert.deepEqual(getBorders(model, "A5"), {
                ...leftBorder,
                ...bottomBorder,
                ...topBorder,
            });
            assert.deepEqual(getBorders(model, "B5"), { ...topBorder, ...bottomBorder });
            assert.deepEqual(getBorders(model, "F5"), {
                ...rightBorder,
                ...bottomBorder,
                ...topBorder,
            });
        }
    );

    QUnit.test("can edit pivot domain", async (assert) => {
        const { model } = await createSpreadsheetWithPivot();
        const [pivotId] = model.getters.getPivotIds();
        assert.deepEqual(model.getters.getPivotDefinition(pivotId).domain, []);
        assert.strictEqual(getCellValue(model, "B4"), 11);
        model.dispatch("UPDATE_ODOO_PIVOT_DOMAIN", {
            pivotId,
            domain: [["foo", "in", [55]]],
        });
        assert.deepEqual(model.getters.getPivotDefinition(pivotId).domain, [["foo", "in", [55]]]);
        await waitForDataSourcesLoaded(model);
        assert.strictEqual(getCellValue(model, "B4"), "");
        model.dispatch("REQUEST_UNDO");
        await waitForDataSourcesLoaded(model);
        assert.deepEqual(model.getters.getPivotDefinition(pivotId).domain, []);
        await waitForDataSourcesLoaded(model);
        assert.strictEqual(getCellValue(model, "B4"), 11);
        model.dispatch("REQUEST_REDO");
        assert.deepEqual(model.getters.getPivotDefinition(pivotId).domain, [["foo", "in", [55]]]);
        await waitForDataSourcesLoaded(model);
        assert.strictEqual(getCellValue(model, "B4"), "");
    });

    QUnit.test("edited domain is exported", async (assert) => {
        const { model } = await createSpreadsheetWithPivot();
        const [pivotId] = model.getters.getPivotIds();
        model.dispatch("UPDATE_ODOO_PIVOT_DOMAIN", {
            pivotId,
            domain: [["foo", "in", [55]]],
        });
        assert.deepEqual(model.exportData().pivots["1"].domain, [["foo", "in", [55]]]);
    });

    QUnit.test("field matching is removed when filter is deleted", async function (assert) {
        const { model } = await createSpreadsheetWithPivot();
        await addGlobalFilter(
            model,
            {
                id: "42",
                type: "relation",
                label: "test",
                defaultValue: [41],
                modelName: undefined,
                rangeType: undefined,
            },
            {
                pivot: { 1: { chain: "product_id", type: "many2one" } },
            }
        );
        const [filter] = model.getters.getGlobalFilters();
        const matching = {
            chain: "product_id",
            type: "many2one",
        };
        assert.deepEqual(model.getters.getPivotFieldMatching("1", filter.id), matching);
        assert.deepEqual(model.getters.getPivotDataSource("1").getComputedDomain(), [
            ["product_id", "in", [41]],
        ]);
        model.dispatch("REMOVE_GLOBAL_FILTER", {
            id: filter.id,
        });
        assert.deepEqual(
            model.getters.getPivotFieldMatching("1", filter.id),
            undefined,
            "it should have removed the pivot and its fieldMatching and datasource altogether"
        );
        assert.deepEqual(model.getters.getPivotDataSource("1").getComputedDomain(), []);
        model.dispatch("REQUEST_UNDO");
        assert.deepEqual(model.getters.getPivotFieldMatching("1", filter.id), matching);
        assert.deepEqual(model.getters.getPivotDataSource("1").getComputedDomain(), [
            ["product_id", "in", [41]],
        ]);
        model.dispatch("REQUEST_REDO");
        assert.deepEqual(model.getters.getPivotFieldMatching("1", filter.id), undefined);
        assert.deepEqual(model.getters.getPivotDataSource("1").getComputedDomain(), []);
    });

    QUnit.test(
        "Load pivot spreadsheet with models that cannot be accessed",
        async function (assert) {
            let hasAccessRights = true;
            const { model } = await createSpreadsheetWithPivot({
                mockRPC: async function (route, args) {
                    if (
                        args.model === "partner" &&
                        args.method === "read_group" &&
                        !hasAccessRights
                    ) {
                        throw makeServerError({ description: "ya done!" });
                    }
                },
            });
            let headerCell;
            let cell;

            await waitForDataSourcesLoaded(model);
            headerCell = getEvaluatedCell(model, "A3");
            cell = getEvaluatedCell(model, "C3");
            assert.equal(headerCell.value, "No");
            assert.equal(cell.value, 15);

            hasAccessRights = false;
            model.dispatch("REFRESH_PIVOT", { id: "1" });
            await waitForDataSourcesLoaded(model);
            headerCell = getEvaluatedCell(model, "A3");
            cell = getEvaluatedCell(model, "C3");
            assert.equal(headerCell.value, "#ERROR");
            assert.equal(headerCell.error.message, "ya done!");
            assert.equal(cell.value, "#ERROR");
            assert.equal(cell.error.message, "ya done!");
        }
    );

    QUnit.test("Title of the first row is inserted as row title", async (assert) => {
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="bar" type="row"/>
                </pivot>`,
        });
        assert.strictEqual(getCellContent(model, "A2"), "Bar");
    });

    QUnit.test(
        "Title of the first row is not inserted if there is no row group bys",
        async (assert) => {
            const { model } = await createSpreadsheetWithPivot({
                arch: /*xml*/ `
                <pivot>
                    <field name="bar" type="col"/>
                </pivot>`,
            });
            assert.strictEqual(getCellContent(model, "A2"), "");
        }
    );
});
