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
import { getBasicPivotArch, getBasicServerData } from "@spreadsheet/../tests/utils/data";
import { CommandResult } from "@spreadsheet/o_spreadsheet/cancelled_reason";
import { addGlobalFilter, setCellContent } from "@spreadsheet/../tests/utils/commands";
import { createModelWithDataSource } from "@spreadsheet/../tests/utils/model";
import { makeDeferred, nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import {
    patchUserContextWithCleanup,
    patchUserWithCleanup,
} from "@web/../tests/helpers/mock_services";
import { user } from "@web/core/user";
import { session } from "@web/session";
import { makeServerError } from "@web/../tests/helpers/mock_server";
import { Model } from "@odoo/o-spreadsheet";
import { THIS_YEAR_GLOBAL_FILTER } from "@spreadsheet/../tests/utils/global_filter";

import * as spreadsheet from "@odoo/o-spreadsheet";
import { waitForDataLoaded } from "@spreadsheet/helpers/model";
const { DEFAULT_LOCALE } = spreadsheet.constants;

QUnit.module("spreadsheet > pivot plugin", {}, () => {
    QUnit.test("can get a pivotId from cell formula", async function (assert) {
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
        assert.strictEqual(pivotId, model.getters.getPivotId("1"));
    });

    QUnit.test(
        "can get a pivotId from cell formula with '-' before the formula",
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
                text: `=-PIVOT.VALUE("1","probability","bar","false","foo","2")`,
            });
            const sheetId = model.getters.getActiveSheetId();
            const pivotId = model.getters.getPivotIdFromPosition({ sheetId, col: 2, row: 2 });
            assert.strictEqual(pivotId, model.getters.getPivotId("1"));
        }
    );

    QUnit.test(
        "can get a pivotId from cell formula with other numerical values",
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
                text: `=3*PIVOT.VALUE("1","probability","bar","false","foo","2")+2`,
            });
            const sheetId = model.getters.getActiveSheetId();
            const pivotId = model.getters.getPivotIdFromPosition({ sheetId, col: 2, row: 2 });
            assert.strictEqual(pivotId, model.getters.getPivotId("1"));
        }
    );

    QUnit.test(
        "can get a pivotId from cell formula where pivot is in a function call",
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
                text: `=SUM(PIVOT.VALUE("1","probability","bar","false","foo","2"),PIVOT.VALUE("1","probability","bar","false","foo","2"))`,
            });
            const sheetId = model.getters.getActiveSheetId();
            const pivotId = model.getters.getPivotIdFromPosition({ sheetId, col: 2, row: 2 });
            assert.strictEqual(pivotId, model.getters.getPivotId("1"));
        }
    );

    QUnit.test(
        "can get a pivotId from cell formula where the id is a reference",
        async function (assert) {
            const { model } = await createSpreadsheetWithPivot();
            setCellContent(
                model,
                "C3",
                `=PIVOT.VALUE(G10,"probability","bar","false","foo","2")+2`
            );
            setCellContent(model, "G10", "1");
            const sheetId = model.getters.getActiveSheetId();
            const pivotId = model.getters.getPivotIdFromPosition({ sheetId, col: 2, row: 2 });
            assert.strictEqual(pivotId, model.getters.getPivotId("1"));
        }
    );

    QUnit.test(
        "can get a pivotId from cell formula (Mix of test scenarios above)",
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
                text: `=3*SUM(PIVOT.VALUE("1","probability","bar","false","foo","2"),PIVOT.VALUE("1","probability","bar","false","foo","2"))+2*PIVOT.VALUE("1","probability","bar","false","foo","2")`,
            });
            const sheetId = model.getters.getActiveSheetId();
            const pivotId = model.getters.getPivotIdFromPosition({ sheetId, col: 2, row: 2 });
            assert.strictEqual(pivotId, model.getters.getPivotId("1"));
        }
    );

    QUnit.test("Can remove a pivot with undo after editing a cell", async function (assert) {
        const { model } = await createSpreadsheetWithPivot();
        assert.ok(getCellContent(model, "B1").startsWith("=PIVOT.HEADER"));
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
        const { model, pivotId } = await createSpreadsheetWithPivot();
        const result = model.dispatch("RENAME_PIVOT", {
            pivotId,
            name: "",
        });
        assert.deepEqual(result.reasons, [CommandResult.EmptyName]);
    });

    QUnit.test("rename pivot with incorrect id is refused", async (assert) => {
        const { model } = await createSpreadsheetWithPivot();
        const result = model.dispatch("RENAME_PIVOT", {
            pivotId: "invalid",
            name: "name",
        });
        assert.deepEqual(result.reasons, [CommandResult.PivotIdNotFound]);
    });

    QUnit.test("Undo/Redo for RENAME_PIVOT", async function (assert) {
        const { model, pivotId } = await createSpreadsheetWithPivot();
        assert.equal(model.getters.getPivotName(pivotId), "Partner Pivot");
        model.dispatch("RENAME_PIVOT", { pivotId, name: "test" });
        assert.equal(model.getters.getPivotName(pivotId), "test");
        model.dispatch("REQUEST_UNDO");
        assert.equal(model.getters.getPivotName(pivotId), "Partner Pivot");
        model.dispatch("REQUEST_REDO");
        assert.equal(model.getters.getPivotName(pivotId), "test");
    });

    QUnit.test("Can delete pivot", async function (assert) {
        const { model, pivotId } = await createSpreadsheetWithPivot();
        model.dispatch("REMOVE_PIVOT", { pivotId });
        assert.strictEqual(model.getters.getPivotIds().length, 0);
        const B4 = getEvaluatedCell(model, "B4");
        assert.equal(B4.message, `There is no pivot with id "1"`);
        assert.equal(B4.value, `#ERROR`);
    });

    QUnit.test("Can undo/redo a delete pivot", async function (assert) {
        const { model, pivotId } = await createSpreadsheetWithPivot();
        const value = getEvaluatedCell(model, "B4").value;
        model.dispatch("REMOVE_PIVOT", { pivotId });
        model.dispatch("REQUEST_UNDO");
        assert.strictEqual(model.getters.getPivotIds().length, 1);
        let B4 = getEvaluatedCell(model, "B4");
        assert.equal(B4.value, value);
        model.dispatch("REQUEST_REDO");
        assert.strictEqual(model.getters.getPivotIds().length, 0);
        B4 = getEvaluatedCell(model, "B4");
        assert.equal(B4.message, `There is no pivot with id "1"`);
        assert.equal(B4.value, `#ERROR`);
    });

    QUnit.test("Format header displays an error for non-existing field", async function (assert) {
        const { model } = await createSpreadsheetWithPivot();
        setCellContent(model, "G10", `=PIVOT.HEADER("1", "measure", "non-existing")`);
        setCellContent(model, "G11", `=PIVOT.HEADER("1", "non-existing", "bla")`);
        await nextTick();
        assert.equal(getCellValue(model, "G10"), "#ERROR");
        assert.equal(getCellValue(model, "G11"), "#ERROR");
        assert.equal(getEvaluatedCell(model, "G10").message, "Field non-existing does not exist");
        assert.equal(getEvaluatedCell(model, "G11").message, "Field non-existing does not exist");
    });

    QUnit.test("invalid group dimensions", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="foo" type="col"/>
                    <field name="bar" type="col"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        const invalids = [
            '=PIVOT.VALUE(1,"probability", "product_id", 1, "bar", false, "foo", 1)', // inverted col dimensions
            '=PIVOT.VALUE(1,"probability", "product_id", 1, "bar", false, "f"&"oo", 1)', // inverted col dimensions, "foo" computed
            '=PIVOT.VALUE(1,"probability", "product_id", 1, "bar", false)', // missing first col dimension
            '=PIVOT.VALUE(1,"probability", "#product_id", 1, "#bar", 1, "#foo", 1)',
            '=PIVOT.VALUE(1,"probability", "bar", false, "foo", 1, "product_id", 1)', // columns before rows

            '=PIVOT.HEADER(1, "product_id", 1, "bar", false, "foo", 1)', // inverted col dimensions
            '=PIVOT.HEADER(1, "product_id", 1, "bar", false)', // missing first col dimension
            '=PIVOT.HEADER(1, "#product_id", 1, "#bar", 1, "#foo", 1)',
            '=PIVOT.HEADER(1, "bar", false, "foo", 1, "product_id", 47)', // columns before rows
        ];
        for (const formula of invalids) {
            setCellContent(model, "G10", formula);
            assert.equal(getCellValue(model, "G10"), "#ERROR", formula);
            assert.equal(
                getEvaluatedCell(model, "G10").message,
                "Dimensions don't match the pivot definition",
                formula
            );
        }
    });

    QUnit.test(
        "user context is combined with pivot context to fetch data",
        async function (assert) {
            const testSession = {
                user_companies: {
                    allowed_companies: {
                        15: { id: 15, name: "Hermit" },
                        16: { id: 16, name: "Craft" },
                    },
                    current_company: 15,
                },
            };
            patchWithCleanup(session, testSession);
            patchUserContextWithCleanup({
                allowed_company_ids: [15],
                tz: "bx",
                lang: "FR",
                uid: 4,
            });
            patchUserWithCleanup({ userId: 4 });
            const spreadsheetData = {
                sheets: [
                    {
                        id: "sheet1",
                        cells: {
                            A1: { content: `=PIVOT.VALUE(1, "probability")` },
                        },
                    },
                ],
                pivots: {
                    1: {
                        type: "ODOO",
                        columns: [{ name: "foo" }],
                        domain: [],
                        measures: [{ name: "probability" }],
                        model: "partner",
                        rows: [{ name: "bar" }],
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
            await waitForDataLoaded(model);
            assert.verifySteps(["read_group", "read_group", "read_group", "read_group"]);
        }
    );

    QUnit.test("fetch metadata only once per model", async function (assert) {
        const spreadsheetData = {
            sheets: [
                {
                    id: "sheet1",
                    cells: {
                        A1: { content: `=PIVOT.VALUE(1, "probability")` },
                        A2: { content: `=PIVOT.VALUE(2, "probability")` },
                    },
                },
            ],
            pivots: {
                1: {
                    type: "ODOO",
                    columns: [{ name: "foo" }],
                    domain: [],
                    measures: [{ name: "probability", aggregator: "sum" }],
                    model: "partner",
                    rows: [{ name: "bar" }],
                    context: {},
                },
                2: {
                    type: "ODOO",
                    columns: [{ name: "bar" }],
                    domain: [],
                    measures: [{ field: "probability", operator: "max" }],
                    model: "partner",
                    rows: [{ name: "foo" }],
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
        await waitForDataLoaded(model);
        assert.verifySteps(["partner/fields_get"]);
    });

    QUnit.test("don't fetch pivot data if no formula use it", async function (assert) {
        const spreadsheetData = {
            pivots: {
                1: {
                    type: "ODOO",
                    columns: [{ name: "foo" }],
                    domain: [],
                    measures: [{ name: "probability", aggregator: "sum" }],
                    model: "partner",
                    rows: [{ name: "bar" }],
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
        setCellContent(model, "A1", `=PIVOT.VALUE("1", "probability")`);
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
                    type: "ODOO",
                    columns: [{ name: "foo" }],
                    domain: [],
                    measures: [{ name: "probability", aggregator: "sum" }],
                    model: "partner",
                    rows: [{ name: "bar" }],
                },
                2: {
                    type: "ODOO",
                    columns: [{ name: "foo" }],
                    domain: [],
                    measures: [{ name: "probability", aggregator: "sum" }],
                    model: "partner",
                    rows: [{ name: "bar" }],
                },
            },
        };
        const model = await createModelWithDataSource({
            spreadsheetData,
        });
        model.config.custom.odooDataProvider.addEventListener("data-source-updated", () =>
            assert.step("data-source-notified")
        );
        setCellContent(model, "A1", '=PIVOT.VALUE("1", "probability")');
        setCellContent(model, "A2", '=PIVOT.VALUE("2", "probability")');
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
                    type: "ODOO",
                    columns: [{ name: "foo" }],
                    domain: [],
                    measures: [{ name: "probability", aggregator: "sum" }],
                    model: "partner",
                    rows: [{ name: "bar" }],
                },
            },
        };
        const model = await createModelWithDataSource({
            spreadsheetData,
        });
        // the data loads first here, when we insert the first pivot function
        setCellContent(model, "A1", '=PIVOT.VALUE("1", "probability")');
        assert.equal(getCellValue(model, "A1"), "Loading...");
        // concurrently reload the same pivot
        model.dispatch("REFRESH_ALL_DATA_SOURCES");
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
                        A1: { content: `=PIVOT.HEADER(1, "measure", "probability")` },
                        A2: { content: `=PIVOT.HEADER(1, "product_id", 37)` },
                        A3: { content: `=PIVOT.VALUE(1, "probability")` },
                    },
                },
            ],
            pivots: {
                1: {
                    type: "ODOO",
                    columns: [{ name: "product_id" }],
                    domain: [],
                    measures: [{ name: "probability", aggregator: "sum" }],
                    model: "partner",
                    rows: [],
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
            { id: 3, name: "14.0", probability: 16 },
        ];

        const { model } = await createSpreadsheetWithPivot({
            serverData,
            arch: /*xml*/ `
                <pivot>
                    <field name="name" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        assert.strictEqual(getCell(model, "A3").content, '=PIVOT.HEADER(1,"name","000111")');
        assert.strictEqual(getCell(model, "A4").content, '=PIVOT.HEADER(1,"name",111)');
        assert.strictEqual(getCell(model, "A5").content, '=PIVOT.HEADER(1,"name","14.0")');
        assert.strictEqual(getEvaluatedCell(model, "A3").value, "000111");
        assert.strictEqual(getEvaluatedCell(model, "A4").value, "111");
        assert.strictEqual(getEvaluatedCell(model, "A5").value, "14.0");
        assert.strictEqual(
            getCell(model, "B3").content,
            '=PIVOT.VALUE(1,"probability","name","000111")'
        );
        assert.strictEqual(
            getCell(model, "B4").content,
            '=PIVOT.VALUE(1,"probability","name",111)'
        );
        assert.strictEqual(
            getCell(model, "B5").content,
            '=PIVOT.VALUE(1,"probability","name","14.0")'
        );
        assert.strictEqual(getEvaluatedCell(model, "B3").value, 15);
        assert.strictEqual(getEvaluatedCell(model, "B4").value, 11);
        assert.strictEqual(getEvaluatedCell(model, "B5").value, 16);
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
            content: `=PIVOT.HEADER("1", "product_id", "1111111")`,
            sheetId,
        });
        await waitForDataLoaded(model);
        assert.equal(
            getEvaluatedCell(model, "E10").message,
            "Unable to fetch the label of 1111111 of model product"
        );
    });

    QUnit.test("relational PIVOT.HEADER with undefined id", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="product_id" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        setCellContent(model, "F10", `=PIVOT.HEADER("1", "product_id", A25)`);
        assert.equal(getCell(model, "A25"), null, "the cell should be empty");
        await waitForDataLoaded(model);
        const F10 = getEvaluatedCell(model, "F10");
        assert.strictEqual(F10.value, "#ERROR");
        assert.strictEqual(F10.message, "Unable to fetch the label of 0 of model product");
    });

    QUnit.test("Verify pivot measures are correctly computed :)", async function (assert) {
        assert.expect(4);

        const { model } = await createSpreadsheetWithPivot();
        assert.equal(getCellValue(model, "B4"), 11);
        assert.equal(getCellValue(model, "C3"), 15);
        assert.equal(getCellValue(model, "D4"), 10);
        assert.equal(getCellValue(model, "E4"), 95);
    });

    QUnit.test("__count measure", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /*xml*/ `
                <pivot>
                    <field name="product_id" type="row"/>
                    <field name="__count" type="measure"/>
                </pivot>`,
        });
        setCellContent(model, "F10", '=PIVOT.VALUE(1, "__count")');
        const F10 = getEvaluatedCell(model, "F10");
        assert.strictEqual(F10.value, 4);
        assert.strictEqual(F10.format, "0");
    });

    QUnit.test("invalid pivot measure", async function (assert) {
        const { model } = await createSpreadsheetWithPivot({
            arch: /* xml */ `
                <pivot>
                    <field name="product_id" type="col"/>
                    <field name="foo" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        const formula = '=PIVOT.VALUE(1, "count")';
        setCellContent(model, "F10", formula);
        assert.equal(getCellValue(model, "F10"), "#ERROR", formula);
        assert.equal(
            getEvaluatedCell(model, "F10").message,
            "The argument count is not a valid measure. Here are the measures: (probability)",
            formula
        );
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
        setCellContent(model, "A1", '=PIVOT.VALUE(1, "probability", "name", "A")');
        setCellContent(model, "A2", '=PIVOT.VALUE(1, "probability", "name", "B")');
        setCellContent(model, "A3", '=PIVOT.VALUE(1, "probability")');
        assert.strictEqual(getEvaluatedCell(model, "A1").value, 10);
        assert.strictEqual(getEvaluatedCell(model, "A2").value, -10);
        assert.strictEqual(getEvaluatedCell(model, "A3").value, 0);
    });

    QUnit.test("can import/export sorted pivot", async (assert) => {
        const spreadsheetData = {
            pivots: {
                1: {
                    type: "ODOO",
                    columns: [{ name: "foo" }],
                    domain: [],
                    measures: [{ name: "probability", aggregator: "sum" }],
                    model: "partner",
                    rows: [{ name: "bar" }],
                    sortedColumn: {
                        measure: "probability",
                        order: "asc",
                        groupId: [[], [1]],
                    },
                    name: "A pivot",
                    context: {},
                    fieldMatching: {},
                    formulaId: "1",
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
        const uid = user.userId;
        const spreadsheetData = {
            pivots: {
                1: {
                    type: "ODOO",
                    columns: [],
                    domain: '[("foo", "=", uid)]',
                    measures: [{ name: "probability", aggregator: "sum" }],
                    model: "partner",
                    rows: [],
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
        setCellContent(model, "A1", '=PIVOT.VALUE(1, "probability")'); // load the data (and check the rpc domain)
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
        assert.equal(getCellFormula(model, "A3"), '=PIVOT.HEADER(1,"tag_ids","false")');
        assert.equal(getCellFormula(model, "A4"), '=PIVOT.HEADER(1,"tag_ids",42)');
        assert.equal(getCellFormula(model, "A5"), '=PIVOT.HEADER(1,"tag_ids",67)');

        assert.equal(
            getCellFormula(model, "B3"),
            '=PIVOT.VALUE(1,"probability","tag_ids","false","foo",1)'
        );
        assert.equal(
            getCellFormula(model, "B4"),
            '=PIVOT.VALUE(1,"probability","tag_ids",42,"foo",1)'
        );
        assert.equal(
            getCellFormula(model, "B5"),
            '=PIVOT.VALUE(1,"probability","tag_ids",67,"foo",1)'
        );

        assert.equal(
            getCellFormula(model, "C3"),
            '=PIVOT.VALUE(1,"probability","tag_ids","false","foo",2)'
        );
        assert.equal(
            getCellFormula(model, "C4"),
            '=PIVOT.VALUE(1,"probability","tag_ids",42,"foo",2)'
        );
        assert.equal(
            getCellFormula(model, "C5"),
            '=PIVOT.VALUE(1,"probability","tag_ids",67,"foo",2)'
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
            setCellContent(model, "A1", `=PIVOT.HEADER(1, "date:${interval}", "false")`);
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

    QUnit.test("can edit pivot domain with UPDATE_ODOO_PIVOT_DOMAIN", async (assert) => {
        const { model } = await createSpreadsheetWithPivot();
        const [pivotId] = model.getters.getPivotIds();
        assert.deepEqual(model.getters.getPivotDefinition(pivotId).domain, []);
        assert.strictEqual(getCellValue(model, "B4"), 11);
        model.dispatch("UPDATE_ODOO_PIVOT_DOMAIN", {
            pivotId,
            domain: [["foo", "in", [55]]],
        });
        assert.deepEqual(model.getters.getPivotDefinition(pivotId).domain, [["foo", "in", [55]]]);
        await waitForDataLoaded(model);
        assert.strictEqual(getCellValue(model, "B4"), "");
        model.dispatch("REQUEST_UNDO");
        await waitForDataLoaded(model);
        assert.deepEqual(model.getters.getPivotDefinition(pivotId).domain, []);
        await waitForDataLoaded(model);
        assert.strictEqual(getCellValue(model, "B4"), 11);
        model.dispatch("REQUEST_REDO");
        assert.deepEqual(model.getters.getPivotDefinition(pivotId).domain, [["foo", "in", [55]]]);
        await waitForDataLoaded(model);
        assert.strictEqual(getCellValue(model, "B4"), "");
    });

    QUnit.test("can edit pivot domain with UPDATE_PIVOT", async (assert) => {
        const { model, pivotId } = await createSpreadsheetWithPivot();
        assert.deepEqual(model.getters.getPivotDefinition(pivotId).domain, []);
        assert.strictEqual(getCellValue(model, "B4"), 11);
        model.dispatch("UPDATE_PIVOT", {
            pivotId,
            pivot: {
                ...model.getters.getPivotDefinition(pivotId),
                domain: [["foo", "in", [55]]],
            },
        });
        assert.deepEqual(model.getters.getPivotDefinition(pivotId).domain, [["foo", "in", [55]]]);
        await waitForDataLoaded(model);
        assert.strictEqual(getCellValue(model, "B4"), "");
        model.dispatch("REQUEST_UNDO");
        await waitForDataLoaded(model);
        assert.deepEqual(model.getters.getPivotDefinition(pivotId).domain, []);
        await waitForDataLoaded(model);
        assert.strictEqual(getCellValue(model, "B4"), 11);
        model.dispatch("REQUEST_REDO");
        assert.deepEqual(model.getters.getPivotDefinition(pivotId).domain, [["foo", "in", [55]]]);
        await waitForDataLoaded(model);
        assert.strictEqual(getCellValue(model, "B4"), "");
    });

    QUnit.test("updating a pivot without changing anything rejects the command", async (assert) => {
        const { model, pivotId } = await createSpreadsheetWithPivot();
        const result = model.dispatch("UPDATE_PIVOT", {
            pivotId,
            pivot: {
                ...model.getters.getPivotDefinition(pivotId),
            },
        });
        assert.strictEqual(result.isSuccessful, false);
    });

    QUnit.test("edited domain is exported", async (assert) => {
        const { model } = await createSpreadsheetWithPivot();
        const [pivotId] = model.getters.getPivotIds();
        model.dispatch("UPDATE_ODOO_PIVOT_DOMAIN", {
            pivotId,
            domain: [["foo", "in", [55]]],
        });
        assert.deepEqual(model.exportData().pivots[pivotId].domain, [["foo", "in", [55]]]);
    });

    QUnit.test("can edit pivot groups", async (assert) => {
        const { model } = await createSpreadsheetWithPivot();
        const [pivotId] = model.getters.getPivotIds();
        let definition = model.getters.getPivotDefinition(pivotId);
        assert.deepEqual(definition.columns, [{ name: "foo" }]);
        assert.deepEqual(definition.rows, [{ name: "bar" }]);
        model.dispatch("UPDATE_PIVOT", {
            pivotId,
            pivot: {
                ...model.getters.getPivotDefinition(pivotId),
                columns: [],
                rows: [],
            },
        });
        definition = model.getters.getPivotDefinition(pivotId);
        assert.deepEqual(definition.columns, []);
        assert.deepEqual(definition.rows, []);
        model.dispatch("REQUEST_UNDO");
        definition = model.getters.getPivotDefinition(pivotId);
        assert.deepEqual(definition.columns, [{ name: "foo" }]);
        assert.deepEqual(definition.rows, [{ name: "bar" }]);
    });

    QUnit.test("field matching is removed when filter is deleted", async function (assert) {
        const { model, pivotId } = await createSpreadsheetWithPivot();
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
                pivot: { [pivotId]: { chain: "product_id", type: "many2one" } },
            }
        );
        const [filter] = model.getters.getGlobalFilters();
        const matching = {
            chain: "product_id",
            type: "many2one",
        };
        assert.deepEqual(model.getters.getPivotFieldMatching(pivotId, filter.id), matching);
        assert.deepEqual(model.getters.getPivot(pivotId).getComputedDomain(), [
            ["product_id", "in", [41]],
        ]);
        model.dispatch("REMOVE_GLOBAL_FILTER", {
            id: filter.id,
        });
        assert.deepEqual(
            model.getters.getPivotFieldMatching(pivotId, filter.id),
            undefined,
            "it should have removed the pivot and its fieldMatching and datasource altogether"
        );
        assert.deepEqual(model.getters.getPivot(pivotId).getComputedDomain(), []);
        model.dispatch("REQUEST_UNDO");
        assert.deepEqual(model.getters.getPivotFieldMatching(pivotId, filter.id), matching);
        assert.deepEqual(model.getters.getPivot(pivotId).getComputedDomain(), [
            ["product_id", "in", [41]],
        ]);
        model.dispatch("REQUEST_REDO");
        assert.deepEqual(model.getters.getPivotFieldMatching(pivotId, filter.id), undefined);
        assert.deepEqual(model.getters.getPivot(pivotId).getComputedDomain(), []);
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

            await waitForDataLoaded(model);
            headerCell = getEvaluatedCell(model, "A3");
            cell = getEvaluatedCell(model, "C3");
            assert.equal(headerCell.value, "No");
            assert.equal(cell.value, 15);

            hasAccessRights = false;
            model.dispatch("REFRESH_ALL_DATA_SOURCES");
            await waitForDataLoaded(model);
            headerCell = getEvaluatedCell(model, "A3");
            cell = getEvaluatedCell(model, "C3");
            assert.equal(headerCell.value, "#ERROR");
            assert.equal(headerCell.message, "ya done!");
            assert.equal(cell.value, "#ERROR");
            assert.equal(cell.message, "ya done!");
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

    QUnit.test("Can duplicate a pivot", async (assert) => {
        const { model, pivotId } = await createSpreadsheetWithPivot();
        const matching = { chain: "product_id", type: "many2one" };
        const filter = { ...THIS_YEAR_GLOBAL_FILTER, id: "42" };
        await addGlobalFilter(model, filter, {
            pivot: { [pivotId]: matching },
        });
        model.dispatch("DUPLICATE_PIVOT", { pivotId, newPivotId: "2" });

        const pivotIds = model.getters.getPivotIds();
        assert.equal(model.getters.getPivotIds().length, 2);

        assert.deepEqual(
            model.getters.getPivotDefinition(pivotIds[1]),
            model.getters.getPivotDefinition(pivotId)
        );

        assert.deepEqual(model.getters.getPivotFieldMatching(pivotId, "42"), matching);
        assert.deepEqual(model.getters.getPivotFieldMatching("2", "42"), matching);
    });

    QUnit.test("Duplicate pivot respects the formula id increment", async (assert) => {
        const { model, pivotId } = await createSpreadsheetWithPivot();
        model.dispatch("DUPLICATE_PIVOT", { pivotId, newPivotId: "second" });
        model.dispatch("DUPLICATE_PIVOT", { pivotId, newPivotId: "third" });
        assert.deepEqual(model.getters.getPivotDefinition("second").formulaId, "2");
        assert.deepEqual(model.getters.getPivotDefinition("third").formulaId, "3");
    });

    QUnit.test("Cannot duplicate unknown pivot", async (assert) => {
        const model = new Model();
        const result = model.dispatch("DUPLICATE_PIVOT", {
            pivotId: "hello",
            newPivotId: "new",
        });
        assert.deepEqual(result.reasons, [CommandResult.PivotIdNotFound]);
    });

    QUnit.test("isPivotUnused getter", async (assert) => {
        const { model, pivotId } = await createSpreadsheetWithPivot();
        const sheetId = model.getters.getActiveSheetId();
        assert.equal(model.getters.isPivotUnused(pivotId), false);

        model.dispatch("CREATE_SHEET", { sheetId: "2" });
        model.dispatch("DELETE_SHEET", { sheetId: sheetId });
        assert.equal(model.getters.isPivotUnused(pivotId), true);

        setCellContent(model, "A1", "=PIVOT.HEADER(1)");
        assert.equal(model.getters.isPivotUnused(pivotId), false);

        setCellContent(model, "A1", "=PIVOT.HEADER(A2)");
        assert.equal(model.getters.isPivotUnused(pivotId), true);

        setCellContent(model, "A2", "1");
        assert.equal(model.getters.isPivotUnused(pivotId), false);

        model.dispatch("REQUEST_UNDO", {});
        assert.equal(model.getters.isPivotUnused(pivotId), true);

        setCellContent(model, "A1", "=PIVOT(1)");
        assert.equal(model.getters.isPivotUnused(pivotId), false);
    });

    QUnit.test("Data are fetched with the correct aggregator", async (assert) => {
        await createSpreadsheetWithPivot({
            arch: /* xml */ `
                <pivot>
                    <field name="probability" type="measure"/>
                </pivot>`,
            mockRPC: async function (route, args) {
                if (args.method === "read_group") {
                    assert.deepEqual(args.kwargs.fields, ["probability:avg"]);
                    assert.step("read_group");
                }
            },
        });
        assert.verifySteps(["read_group"]);
    });

    QUnit.test("changing measure aggregates", async (assert) => {
        const { model, pivotId } = await createSpreadsheetWithPivot({
            arch: /* xml */ `
                <pivot>
                    <field name="probability" type="measure"/>
                </pivot>`,
            mockRPC: async function (route, args) {
                if (args.method === "read_group") {
                    assert.step(args.kwargs.fields.join());
                }
            },
        });
        assert.verifySteps(["probability:avg"]);
        model.dispatch("UPDATE_PIVOT", {
            pivotId,
            pivot: {
                ...model.getters.getPivotDefinition(pivotId),
                measures: [{ name: "probability", aggregator: "sum" }],
            },
        });
        await nextTick();
        assert.verifySteps(["probability:sum"]);
        model.dispatch("UPDATE_PIVOT", {
            pivotId,
            pivot: {
                ...model.getters.getPivotDefinition(pivotId),
                measures: [{ name: "foo", aggregator: "sum" }],
            },
        });
        await nextTick();
        assert.verifySteps(["foo:sum"]);
    });

    QUnit.test(
        "many2one measures are aggregated with count_distinct by default",
        async (assert) => {
            const { model, pivotId } = await createSpreadsheetWithPivot({
                arch: /* xml */ `
                <pivot>
                    <field name="probability" type="measure"/>
                </pivot>`,
                mockRPC: async function (route, args) {
                    if (args.method === "read_group") {
                        assert.step(args.kwargs.fields.join());
                    }
                },
            });
            assert.verifySteps(["probability:avg"]);
            model.dispatch("UPDATE_PIVOT", {
                pivotId,
                pivot: {
                    ...model.getters.getPivotDefinition(pivotId),
                    measures: [{ name: "product_id" }], // no aggregator specified
                },
            });
            setCellContent(model, "A1", '=PIVOT.VALUE(1, "product_id")');
            await nextTick();
            assert.strictEqual(getEvaluatedCell(model, "A1").value, 2);
            assert.verifySteps(["product_id:count_distinct"]);
        }
    );

    QUnit.test("changing measure aggregates changes the format", async (assert) => {
        const { model, pivotId } = await createSpreadsheetWithPivot({
            arch: /* xml */ `
                <pivot>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });
        setCellContent(model, "A1", '=PIVOT.VALUE(1, "probability")');
        assert.strictEqual(getEvaluatedCell(model, "A1").format, "#,##0.00");
        model.dispatch("UPDATE_PIVOT", {
            pivotId,
            pivot: {
                ...model.getters.getPivotDefinition(pivotId),
                measures: [{ name: "probability", aggregator: "count_distinct" }],
            },
        });
        await nextTick();
        assert.strictEqual(getEvaluatedCell(model, "A1").format, "0");
    });

    QUnit.test("changing order of group by", async (assert) => {
        const { model, pivotId } = await createSpreadsheetWithPivot({
            arch: /* xml */ `
                <pivot>
                    <field name="foo" type="col"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
            mockRPC: async function (route, args) {
                if (args.method === "read_group") {
                    assert.step(args.kwargs.orderby || "NO_ORDER");
                }
            },
        });
        assert.verifySteps(["NO_ORDER", "NO_ORDER"]);
        model.dispatch("UPDATE_PIVOT", {
            pivotId,
            pivot: {
                ...model.getters.getPivotDefinition(pivotId),
                columns: [{ name: "foo", order: "asc" }],
            },
        });
        assert.deepEqual(model.getters.getPivotDefinition(pivotId).columns, [
            { name: "foo", order: "asc" },
        ]);
        await nextTick();
        assert.verifySteps(["NO_ORDER", "foo asc"]);
        model.dispatch("UPDATE_PIVOT", {
            pivotId,
            pivot: {
                ...model.getters.getPivotDefinition(pivotId),
                columns: [{ name: "foo" }],
            },
        });
        await nextTick();
        assert.verifySteps(["NO_ORDER", "NO_ORDER"]);
    });

    QUnit.test("change date order", async (assert) => {
        const { model, pivotId } = await createSpreadsheetWithPivot({
            arch: /* xml */ `
                <pivot>
                    <field name="probability" type="measure"/>
                </pivot>`,
            mockRPC: async function (route, args) {
                if (args.method === "read_group") {
                    assert.step(args.kwargs.orderby || "NO_ORDER");
                }
            },
        });
        assert.verifySteps(["NO_ORDER"]);
        model.dispatch("UPDATE_PIVOT", {
            pivotId,
            pivot: {
                ...model.getters.getPivotDefinition(pivotId),
                columns: [
                    { name: "date", granularity: "year", order: "asc" },
                    { name: "date", granularity: "month", order: "desc" },
                ],
            },
        });
        await nextTick();
        assert.verifySteps(["NO_ORDER", "date:year asc", "date:year asc,date:month desc"]);
    });

    QUnit.test("duplicated dimension on col and row with different granularity", async (assert) => {
        const serverData = getBasicServerData();
        serverData.models.partner.records = [{ id: 1, date: "2024-03-30", probability: 11 }];
        const { model } = await createSpreadsheetWithPivot({
            serverData,
            arch: /* xml */ `
                <pivot>
                    <field name="date" type="col" interval="year"/>
                    <field name="date" type="row" interval="month"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
        });

        setCellContent(
            model,
            "A1",
            '=PIVOT.VALUE(1,"probability","date:month","3/2024","date:year",2024)'
        );
        setCellContent(model, "A2", '=PIVOT.VALUE(1,"probability","#date:month",1,"#date:year",1)'); // positional
        assert.strictEqual(getEvaluatedCell(model, "A1").value, 11);
        assert.strictEqual(getEvaluatedCell(model, "A2").value, 11);
    });

    QUnit.test("changing granularity of group by", async (assert) => {
        const { model, pivotId } = await createSpreadsheetWithPivot({
            arch: /* xml */ `
                <pivot>
                    <field name="date" type="col"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
            mockRPC: async function (route, args) {
                if (args.method === "read_group") {
                    const groupBys = args.kwargs.groupby;
                    if (groupBys.length) {
                        assert.step(args.kwargs.groupby.join(","));
                    }
                }
            },
        });
        assert.verifySteps(["date:month"]);
        model.dispatch("UPDATE_PIVOT", {
            pivotId,
            pivot: {
                ...model.getters.getPivotDefinition(pivotId),
                columns: [{ name: "date", granularity: "day" }],
            },
        });
        assert.deepEqual(model.getters.getPivotDefinition(pivotId).columns, [
            { name: "date", granularity: "day" },
        ]);
        await nextTick();
        assert.verifySteps(["date:day"]);
    });
});
