/** @odoo-module */

import {
    click,
    nextTick,
    getFixture,
    patchWithCleanup,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { SpreadsheetAction } from "@documents_spreadsheet/bundle/actions/spreadsheet_action";
import {
    setupControlPanelServiceRegistry,
    toggleMenu,
    toggleMenuItem,
} from "@web/../tests/search/helpers";
import { makeView } from "@web/../tests/views/helpers";

import { waitForDataSourcesLoaded } from "@spreadsheet/../tests/utils/model";
import {
    createSpreadsheetFromPivotView,
    spawnPivotViewForSpreadsheet,
} from "../../utils/pivot_helpers";
import { getBasicData, getBasicServerData } from "@spreadsheet/../tests/utils/data";
import {
    getSpreadsheetActionModel,
    prepareWebClientForSpreadsheet,
} from "@spreadsheet_edition/../tests/utils/webclient_helpers";
import {
    getCell,
    getEvaluatedCell,
    getCellContent,
    getCells,
    getCellValue,
} from "@spreadsheet/../tests/utils/getters";
import { session } from "@web/session";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { Model } from "@odoo/o-spreadsheet";

QUnit.module("spreadsheet pivot view", {}, () => {
    QUnit.test("simple pivot export", async (assert) => {
        const { model } = await createSpreadsheetFromPivotView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,pivot": /* xml */ `
                        <pivot>
                            <field name="foo" type="measure"/>
                        </pivot>`,
                    "partner,false,search": /* xml */ `<search/>`,
                },
            },
        });
        assert.strictEqual(Object.values(getCells(model)).length, 6);
        assert.strictEqual(getCellContent(model, "A1"), "");
        assert.strictEqual(getCellContent(model, "A2"), "");
        assert.strictEqual(getCellContent(model, "A3"), "=ODOO.PIVOT.HEADER(1)");
        assert.strictEqual(getCellContent(model, "B1"), "=ODOO.PIVOT.HEADER(1)");
        assert.strictEqual(getCellContent(model, "B2"), '=ODOO.PIVOT.HEADER(1,"measure","foo")');
        assert.strictEqual(getCellContent(model, "B3"), '=ODOO.PIVOT(1,"foo")');
    });

    QUnit.test("simple pivot export with two measures", async (assert) => {
        const { model } = await createSpreadsheetFromPivotView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,pivot": /* xml */ `
                        <pivot>
                            <field name="foo" type="measure"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                    "partner,false,search": /* xml */ `<search/>`,
                },
            },
        });
        assert.strictEqual(Object.values(getCells(model)).length, 9);
        assert.strictEqual(getCellContent(model, "B1"), "=ODOO.PIVOT.HEADER(1)");
        assert.strictEqual(getCellContent(model, "B2"), '=ODOO.PIVOT.HEADER(1,"measure","foo")');
        assert.strictEqual(getCell(model, "B2").style.bold, undefined);
        assert.strictEqual(
            getCellContent(model, "C2"),
            '=ODOO.PIVOT.HEADER(1,"measure","probability")'
        );
        assert.strictEqual(getCellContent(model, "B3"), '=ODOO.PIVOT(1,"foo")');
        assert.strictEqual(getCellContent(model, "C3"), '=ODOO.PIVOT(1,"probability")');
    });

    QUnit.test("Insert in spreadsheet is disabled when data is empty", async (assert) => {
        assert.expect(1);

        setupControlPanelServiceRegistry();

        const data = getBasicData();
        data.partner.records = [];
        data.product.records = [];
        const serverData = {
            models: data,
        };

        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="measure"/>
                </pivot>`,
            mockRPC: async function (route, args) {
                if (args.method === "has_group") {
                    return true;
                }
            },
        });
        assert.ok(document.body.querySelector("button.o_pivot_add_spreadsheet").disabled);
    });

    QUnit.test("Insert in spreadsheet is disabled when no measure is specified", async (assert) => {
        assert.expect(1);

        setupControlPanelServiceRegistry();
        const serverData = {
            models: getBasicData(),
        };
        await makeView({
            type: "pivot",
            resModel: "partner",
            serverData,
            arch: /*xml*/ `
                <pivot>
                    <field name="foo" type="measure"/>
                </pivot>`,
            mockRPC: function (route, args) {
                if (args.method === "has_group") {
                    return Promise.resolve(true);
                }
            },
        });

        const target = getFixture();
        await toggleMenu(target, "Measures");
        await toggleMenuItem(target, "Foo");
        assert.ok(target.querySelector("button.o_pivot_add_spreadsheet").disabled);
    });

    QUnit.test(
        "Insert in spreadsheet is disabled when same groupby occurs in both columns and rows",
        async (assert) => {
            setupControlPanelServiceRegistry();
            const serverData = {
                models: getBasicData(),
            };
            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
                arch: /*xml*/ `
            <pivot>
                <field name="id" type="col"/>
                <field name="id" type="row"/>
                <field name="foo" type="measure"/>
            </pivot>`,
                mockRPC: function (route, args) {
                    if (args.method === "has_group") {
                        return Promise.resolve(true);
                    }
                },
            });

            const target = getFixture();
            const insertButton = target.querySelector("button.o_pivot_add_spreadsheet");
            assert.ok(insertButton.disabled);
            assert.strictEqual(
                insertButton.parentElement.dataset.tooltip,
                "Pivot contains duplicate groupbys"
            );
        }
    );

    QUnit.test(
        "Insert in spreadsheet is disabled when columns and rows both contains same groupby with different aggregator",
        async (assert) => {
            setupControlPanelServiceRegistry();
            const serverData = {
                models: getBasicData(),
            };
            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
                arch: /*xml*/ `
                <pivot>
                    <field name="date" interval="year" type="col"/>
                    <field name="date" interval="month" type="row"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
                mockRPC: function (route, args) {
                    if (args.method === "has_group") {
                        return Promise.resolve(true);
                    }
                },
            });

            const target = getFixture();
            assert.ok(target.querySelector("button.o_pivot_add_spreadsheet").disabled);
        }
    );

    QUnit.test(
        "Can insert in spreadsheet when group by the same date fields with different aggregates",
        async (assert) => {
            setupControlPanelServiceRegistry();
            const serverData = {
                models: getBasicData(),
            };
            await makeView({
                type: "pivot",
                resModel: "partner",
                serverData,
                arch: /*xml*/ `
                <pivot>
                    <field name="date" interval="year" type="col"/>
                    <field name="date" interval="month" type="col"/>
                    <field name="probability" type="measure"/>
                </pivot>`,
                mockRPC: function (route, args) {
                    if (args.method === "has_group") {
                        return Promise.resolve(true);
                    }
                },
            });

            const target = getFixture();
            assert.notOk(target.querySelector("button.o_pivot_add_spreadsheet").disabled);
        }
    );

    QUnit.test("groupby date field without interval defaults to month", async (assert) => {
        const { model } = await createSpreadsheetFromPivotView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,pivot": /* xml */ `
                        <pivot string="Partners">
                            <field name="foo" type="col"/>
                            <!-- no interval specified -->
                            <field name="date" type="row"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                    "partner,false,search": /* xml */ `<search/>`,
                },
            },
        });
        const pivot = model.getters.getPivotDefinition("1");
        assert.deepEqual(pivot, {
            colGroupBys: ["foo"],
            context: {},
            domain: [],
            id: "1",
            measures: ["probability"],
            model: "partner",
            rowGroupBys: ["date"],
            name: "Partners by Foo",
            sortedColumn: null,
        });
        assert.equal(getCellContent(model, "A3"), '=ODOO.PIVOT.HEADER(1,"date","04/2016")');
        assert.equal(getCellContent(model, "A4"), '=ODOO.PIVOT.HEADER(1,"date","10/2016")');
        assert.equal(getCellContent(model, "A5"), '=ODOO.PIVOT.HEADER(1,"date","12/2016")');
        assert.equal(
            getCellContent(model, "B3"),
            '=ODOO.PIVOT(1,"probability","date","04/2016","foo",1)'
        );
        assert.equal(
            getCellContent(model, "B4"),
            '=ODOO.PIVOT(1,"probability","date","10/2016","foo",1)'
        );
        assert.equal(
            getCellContent(model, "B5"),
            '=ODOO.PIVOT(1,"probability","date","12/2016","foo",1)'
        );
        assert.equal(getEvaluatedCell(model, "A3").formattedValue, "April 2016");
        assert.equal(getEvaluatedCell(model, "A4").formattedValue, "October 2016");
        assert.equal(getEvaluatedCell(model, "A5").formattedValue, "December 2016");
        assert.equal(getEvaluatedCell(model, "B3").formattedValue, "");
        assert.equal(getEvaluatedCell(model, "B4").formattedValue, "11.00");
        assert.equal(getEvaluatedCell(model, "B5").formattedValue, "");
    });

    QUnit.test("pivot with one level of group bys", async (assert) => {
        assert.expect(7);
        const { model } = await createSpreadsheetFromPivotView();
        assert.strictEqual(Object.values(getCells(model)).length, 30);
        assert.strictEqual(getCellContent(model, "A3"), '=ODOO.PIVOT.HEADER(1,"bar","false")');
        assert.strictEqual(getCellContent(model, "A4"), '=ODOO.PIVOT.HEADER(1,"bar","true")');
        assert.strictEqual(getCellContent(model, "A5"), "=ODOO.PIVOT.HEADER(1)");
        assert.strictEqual(
            getCellContent(model, "B2"),
            '=ODOO.PIVOT.HEADER(1,"foo",1,"measure","probability")'
        );
        assert.strictEqual(
            getCellContent(model, "C3"),
            '=ODOO.PIVOT(1,"probability","bar","false","foo",2)'
        );
        assert.strictEqual(getCellContent(model, "F5"), '=ODOO.PIVOT(1,"probability")');
    });

    QUnit.test("groupby date field on row gives correct name", async (assert) => {
        const { model } = await createSpreadsheetFromPivotView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,pivot": /* xml */ `
                        <pivot string="Partners">
                            <field name="date" type="row"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                    "partner,false,search": /* xml */ `<search/>`,
                },
            },
        });
        const pivot = model.getters.getPivotDefinition("1");
        assert.deepEqual(pivot, {
            colGroupBys: [],
            context: {},
            domain: [],
            id: "1",
            measures: ["probability"],
            model: "partner",
            rowGroupBys: ["date"],
            name: "Partners by Date",
            sortedColumn: null,
        });
    });

    QUnit.test("pivot with two levels of group bys in rows", async (assert) => {
        assert.expect(9);
        const { model } = await createSpreadsheetFromPivotView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,pivot": /* xml */ `
                        <pivot>
                            <field name="bar" type="row"/>
                            <field name="product_id" type="row"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                    "partner,false,search": /* xml */ `<search/>`,
                },
            },
        });
        assert.strictEqual(Object.values(getCells(model)).length, 16);
        assert.strictEqual(getCellContent(model, "A3"), '=ODOO.PIVOT.HEADER(1,"bar","false")');
        assert.deepEqual(getCell(model, "A3").style, { fillColor: "#E6F2F3", bold: true });
        assert.strictEqual(
            getCellContent(model, "A4"),
            '=ODOO.PIVOT.HEADER(1,"bar","false","product_id",41)'
        );
        assert.deepEqual(getCell(model, "A4").style, { fillColor: "#E6F2F3" });
        assert.strictEqual(getCellContent(model, "A5"), '=ODOO.PIVOT.HEADER(1,"bar","true")');
        assert.strictEqual(
            getCellContent(model, "A6"),
            '=ODOO.PIVOT.HEADER(1,"bar","true","product_id",37)'
        );
        assert.strictEqual(
            getCellContent(model, "A7"),
            '=ODOO.PIVOT.HEADER(1,"bar","true","product_id",41)'
        );
        assert.strictEqual(getCellContent(model, "A8"), "=ODOO.PIVOT.HEADER(1)");
    });

    QUnit.test("verify that there is a record for an undefined many2one header", async (assert) => {
        assert.expect(1);

        const data = getBasicData();

        data.partner.records = [
            {
                id: 1,
                foo: 12,
                bar: true,
                date: "2016-04-14",
                product_id: false,
                probability: 10,
            },
        ];

        const { model } = await createSpreadsheetFromPivotView({
            serverData: {
                models: data,
                views: {
                    "partner,false,pivot": /* xml */ `
                        <pivot>
                            <field name="product_id" type="row"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                    "partner,false,search": /* xml */ `<search/>`,
                },
            },
        });
        assert.strictEqual(
            getCellContent(model, "A3"),
            '=ODOO.PIVOT.HEADER(1,"product_id","false")'
        );
    });

    QUnit.test("undefined date is inserted in pivot", async (assert) => {
        assert.expect(1);

        const data = getBasicData();
        data.partner.records = [
            {
                id: 1,
                foo: 12,
                bar: true,
                date: false,
                product_id: 37,
                probability: 10,
            },
        ];

        const { model } = await createSpreadsheetFromPivotView({
            serverData: {
                models: data,
                views: {
                    "partner,false,pivot": /* xml */ `
                        <pivot>
                            <field name="date" interval="day" type="row"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                    "partner,false,search": /* xml */ `<search/>`,
                },
            },
        });
        assert.strictEqual(getCellContent(model, "A3"), '=ODOO.PIVOT.HEADER(1,"date:day","false")');
    });

    QUnit.test("pivot with two levels of group bys in cols", async (assert) => {
        assert.expect(12);
        const { model } = await createSpreadsheetFromPivotView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,pivot": /* xml */ `
                        <pivot>
                            <field name="bar" type="col"/>
                            <field name="product_id" type="col"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                    "partner,false,search": /* xml */ `<search/>`,
                },
            },
        });
        assert.strictEqual(Object.values(getCells(model)).length, 20);
        assert.strictEqual(getCellContent(model, "A1"), "");
        assert.deepEqual(getCell(model, "A4").style, { fillColor: "#E6F2F3", bold: true });
        assert.strictEqual(getCellContent(model, "B1"), '=ODOO.PIVOT.HEADER(1,"bar","false")');
        assert.strictEqual(
            getCellContent(model, "B2"),
            '=ODOO.PIVOT.HEADER(1,"bar","false","product_id",41)'
        );
        assert.strictEqual(
            getCellContent(model, "B3"),
            '=ODOO.PIVOT.HEADER(1,"bar","false","product_id",41,"measure","probability")'
        );
        assert.deepEqual(getCell(model, "C2").style, { fillColor: "#E6F2F3", bold: true });
        assert.strictEqual(getCellContent(model, "C1"), '=ODOO.PIVOT.HEADER(1,"bar","true")');
        assert.strictEqual(
            getCellContent(model, "C2"),
            '=ODOO.PIVOT.HEADER(1,"bar","true","product_id",37)'
        );
        assert.strictEqual(
            getCellContent(model, "C3"),
            '=ODOO.PIVOT.HEADER(1,"bar","true","product_id",37,"measure","probability")'
        );
        assert.strictEqual(
            getCellContent(model, "D2"),
            '=ODOO.PIVOT.HEADER(1,"bar","true","product_id",41)'
        );
        assert.strictEqual(
            getCellContent(model, "D3"),
            '=ODOO.PIVOT.HEADER(1,"bar","true","product_id",41,"measure","probability")'
        );
    });

    QUnit.test("pivot with count as measure", async (assert) => {
        assert.expect(3);

        const { model } = await createSpreadsheetFromPivotView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,pivot": /* xml */ `
                        <pivot>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                    "partner,false,search": /* xml */ `<search/>`,
                },
            },
            actions: async (target) => {
                await toggleMenu(target, "Measures");
                await toggleMenuItem(target, "Count");
            },
        });
        assert.strictEqual(Object.keys(getCells(model)).length, 9);
        assert.strictEqual(
            getCellContent(model, "C2"),
            '=ODOO.PIVOT.HEADER(1,"measure","__count")'
        );
        assert.strictEqual(getCellContent(model, "C3"), '=ODOO.PIVOT(1,"__count")');
    });

    QUnit.test(
        "pivot with two levels of group bys in cols with not enough cols",
        async (assert) => {
            assert.expect(1);

            const data = getBasicData();
            // add many values in a subgroup
            for (let i = 0; i < 70; i++) {
                data.product.records.push({
                    id: i + 9999,
                    display_name: i.toString(),
                });
                data.partner.records.push({
                    id: i + 9999,
                    bar: i % 2 === 0,
                    product_id: i + 9999,
                    probability: i,
                });
            }
            const { model } = await createSpreadsheetFromPivotView({
                serverData: {
                    models: data,
                    views: {
                        "partner,false,pivot": /* xml */ `
                            <pivot>
                                <field name="bar" type="col"/>
                                <field name="product_id" type="col"/>
                                <field name="foo" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
                        "partner,false,search": /* xml */ `<search/>`,
                    },
                },
            });
            // 72 products * 1 groups + 1 row header + 1 total col
            assert.strictEqual(model.getters.getNumberCols(model.getters.getActiveSheetId()), 75);
        }
    );

    QUnit.test("groupby week is sorted", async (assert) => {
        assert.expect(4);
        const { model } = await createSpreadsheetFromPivotView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,pivot": /* xml */ `
                        <pivot string="Partners">
                            <field name="foo" type="col"/>
                            <field name="date" interval="week" type="row"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                    "partner,false,search": /* xml */ `<search/>`,
                },
            },
        });
        assert.strictEqual(
            getCellContent(model, "A3"),
            `=ODOO.PIVOT.HEADER(1,"date:week","15/2016")`
        );
        assert.strictEqual(
            getCellContent(model, "A4"),
            `=ODOO.PIVOT.HEADER(1,"date:week","43/2016")`
        );
        assert.strictEqual(
            getCellContent(model, "A5"),
            `=ODOO.PIVOT.HEADER(1,"date:week","49/2016")`
        );
        assert.strictEqual(
            getCellContent(model, "A6"),
            `=ODOO.PIVOT.HEADER(1,"date:week","50/2016")`
        );
    });

    QUnit.test("Can save a pivot in a new spreadsheet", async (assert) => {
        const serverData = {
            models: getBasicData(),
            views: {
                "partner,false,pivot": /* xml */ `
                 <pivot string="Partners">
                     <field name="probability" type="measure"/>
                 </pivot>`,
                "partner,false,search": /* xml */ `<search/>`,
            },
        };
        await prepareWebClientForSpreadsheet();
        const webClient = await createWebClient({
            serverData,
            mockRPC: function (route, args) {
                if (route.includes("get_spreadsheets_to_display")) {
                    return [{ id: 1, name: "My Spreadsheet" }];
                }
                if (args.method === "action_open_new_spreadsheet") {
                    assert.step("action_open_new_spreadsheet");
                }
            },
        });

        await doAction(webClient, {
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "pivot"]],
        });
        const target = getFixture();
        const insertButton = target.querySelector("button.o_pivot_add_spreadsheet");
        assert.strictEqual(insertButton.parentElement.dataset.tooltip, undefined);
        await click(insertButton);
        await click(document.querySelector(".modal-content > .modal-footer > .btn-primary"));
        assert.verifySteps(["action_open_new_spreadsheet"]);
    });

    QUnit.test("Can save a pivot in existing spreadsheet", async (assert) => {
        assert.expect(3);

        const serverData = {
            models: getBasicData(),
            views: {
                "partner,false,pivot": /* xml */ `
                    <pivot>
                        <field name="probability" type="measure"/>
                    </pivot>`,
                "partner,false,search": /* xml */ `<search/>`,
            },
        };
        await prepareWebClientForSpreadsheet();
        const webClient = await createWebClient({
            serverData,
            mockRPC: function (route, args) {
                if (route === "/web/action/load") {
                    assert.step("write");
                    return { id: args.action_id, type: "ir.actions.act_window_close" };
                }
                if (route.includes("join_spreadsheet_session")) {
                    assert.step("join_spreadsheet_session");
                }
                if (args.model === "documents.document") {
                    switch (args.method) {
                        case "get_spreadsheets_to_display":
                            return [{ id: 1, name: "My Spreadsheet" }];
                    }
                }
            },
        });

        await doAction(webClient, {
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "pivot"]],
        });
        const target = getFixture();
        await click(target.querySelector(".o_pivot_add_spreadsheet"));
        await triggerEvent(target, ".o-sp-dialog-item div[data-id='1']", "focus");
        await nextTick();
        await click(document.querySelector(".modal-content > .modal-footer > .btn-primary"));
        await doAction(webClient, 1); // leave the spreadsheet action
        assert.verifySteps(["join_spreadsheet_session", "write"]);
    });

    QUnit.test("Add pivot sheet at the end of existing sheets", async (assert) => {
        const model = new Model();
        model.dispatch("CREATE_SHEET", { sheetId: "42", position: 1, name: "My Sheet" });
        const models = getBasicData();
        models["documents.document"].records = [
            {
                spreadsheet_data: JSON.stringify(model.exportData()),
                name: "a spreadsheet",
                folder_id: 1,
                handler: "spreadsheet",
                id: 456,
                is_favorited: false,
            },
        ];
        const serverData = {
            models: models,
            views: getBasicServerData().views,
        };
        await prepareWebClientForSpreadsheet();
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, {
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [[false, "pivot"]],
        });
        const fixture = getFixture();
        await click(fixture.querySelector(".o_pivot_add_spreadsheet"));
        await triggerEvent(fixture, ".o-sp-dialog-item div[data-id='456']", "focus");
        await nextTick();
        await click(document.querySelector(".modal-content > .modal-footer > .btn-primary"));
        await nextTick();
        assert.containsN(fixture, ".o-sheet", 3, "it should have a third sheet");
        const sheets = fixture.querySelectorAll(".o-sheet");
        const activeSheet = fixture.querySelector(".o-sheet.active");
        assert.equal(activeSheet, sheets[2]);
        assert.equal(sheets[0].innerText, "Sheet1");
        assert.equal(sheets[1].innerText, "My Sheet");
        assert.equal(sheets[2].innerText, "Sheet2");
    });

    QUnit.test("pivot with a domain", async (assert) => {
        assert.expect(3);

        const { model } = await createSpreadsheetFromPivotView({
            domain: [["bar", "=", true]],
        });
        const domain = model.getters.getPivotDefinition("1").domain;
        assert.deepEqual(domain, [["bar", "=", true]], "It should have the correct domain");
        assert.strictEqual(getCellContent(model, "A3"), `=ODOO.PIVOT.HEADER(1,"bar","true")`);
        assert.strictEqual(getCellContent(model, "A4"), `=ODOO.PIVOT.HEADER(1)`);
    });

    QUnit.test("pivot with a contextual domain", async (assert) => {
        const uid = session.user_context.uid;
        const serverData = getBasicServerData();
        serverData.models.partner.records = [
            {
                id: 1,
                probability: 0.5,
                foo: uid,
                bar: true,
            },
        ];
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <filter string="Filter" name="filter" domain="[('foo', '=', uid)]"/>
            </search>
        `;
        serverData.views["partner,false,pivot"] = /* xml */ `
            <pivot>
                <field name="probability" type="measure"/>
            </pivot>
        `;
        const { model } = await createSpreadsheetFromPivotView({
            serverData,
            additionalContext: { search_default_filter: 1 },
            mockRPC: function (route, args) {
                if (args.method === "read_group") {
                    assert.deepEqual(
                        args.kwargs.domain,
                        [["foo", "=", uid]],
                        "data should be fetched with the evaluated the domain"
                    );
                    assert.step("read_group");
                }
            },
        });
        const pivotId = "1";
        const domain = model.getters.getPivotDefinition("1").domain;
        assert.deepEqual(domain, '[("foo", "=", uid)]', "It should have the raw domain string");
        assert.deepEqual(
            model.exportData().pivots[pivotId].domain,
            '[("foo", "=", uid)]',
            "domain is exported with the dynamic value"
        );
        assert.verifySteps(["read_group", "read_group"]);
    });

    QUnit.test("pivot with a quote in name", async function (assert) {
        assert.expect(1);

        const data = getBasicData();
        data.product.records.push({
            id: 42,
            display_name: `name with "`,
        });
        const { model } = await createSpreadsheetFromPivotView({
            model: "product",
            serverData: {
                models: data,
                views: {
                    "product,false,pivot": /*xml*/ `
                        <pivot>
                            <field name="display_name" type="col"/>
                            <field name="id" type="row"/>
                        </pivot>`,
                    "product,false,search": `<search/>`,
                },
            },
        });
        assert.equal(
            getCellContent(model, "B1"),
            `=ODOO.PIVOT.HEADER(1,"display_name","name with \\"")`
        );
    });

    QUnit.test("group by related field with archived record", async function (assert) {
        assert.expect(3);
        // TODOAFTERSPLIT this doesn't seem to have any archived record
        const { model } = await createSpreadsheetFromPivotView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,pivot": /* xml */ `
                        <pivot>
                            <field name="product_id" type="col"/>
                            <field name="name" type="row"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                    "partner,false,search": /* xml */ `<search/>`,
                },
            },
        });
        assert.equal(getCellContent(model, "B1"), `=ODOO.PIVOT.HEADER(1,"product_id",37)`);
        assert.equal(getCellContent(model, "C1"), `=ODOO.PIVOT.HEADER(1,"product_id",41)`);
        assert.equal(getCellContent(model, "D1"), `=ODOO.PIVOT.HEADER(1)`);
    });

    QUnit.test("group by regular field with archived record", async function (assert) {
        assert.expect(4);

        const data = getBasicData();
        data.partner.records[0].active = false;
        const { model } = await createSpreadsheetFromPivotView({
            serverData: {
                models: data,
                views: {
                    "partner,false,pivot": /* xml */ `
                        <pivot>
                            <field name="product_id" type="col"/>
                            <field name="foo" type="row"/>
                            <field name="probability" type="measure"/>
                        </pivot>`,
                    "partner,false,search": /* xml */ `<search/>`,
                },
            },
        });
        assert.equal(getCellContent(model, "A3"), `=ODOO.PIVOT.HEADER(1,"foo",1)`);
        assert.equal(getCellContent(model, "A4"), `=ODOO.PIVOT.HEADER(1,"foo",2)`);
        assert.equal(getCellContent(model, "A5"), `=ODOO.PIVOT.HEADER(1,"foo",17)`);
        assert.equal(getCellContent(model, "A6"), `=ODOO.PIVOT.HEADER(1)`);
    });

    QUnit.test("Columns of newly inserted pivot are auto-resized", async function (assert) {
        assert.expect(1);

        const data = getBasicData();
        data.partner.fields.probability.string = "Probability with a super long name";
        const { model } = await createSpreadsheetFromPivotView({
            serverData: {
                ...getBasicServerData(),
                models: data,
            },
        });
        const sheetId = model.getters.getActiveSheetId();
        const defaultColSize = 96;
        assert.ok(
            model.getters.getColSize(sheetId, 1) > defaultColSize,
            "Column should be resized"
        );
    });

    QUnit.test("user related context is not saved in the spreadsheet", async function (assert) {
        const userContext = {
            allowed_company_ids: [15],
            tz: "bx",
            lang: "FR",
            uid: 4,
        };
        const context = {
            ...userContext,
            default_stage_id: 5,
        };
        const testSession = {
            uid: 4,
            user_companies: {
                allowed_companies: { 15: { id: 15, name: "Hermit" } },
                current_company: 15,
            },
            user_context: userContext,
        };
        patchWithCleanup(session, testSession);
        const { model, env } = await createSpreadsheetFromPivotView({
            additionalContext: context,
        });
        assert.deepEqual(
            env.services.user.context,
            userContext,
            "context is used for spreadsheet action"
        );
        assert.deepEqual(
            model.exportData().pivots[1].context,
            {
                default_stage_id: 5,
            },
            "user related context is not stored in context"
        );
    });

    QUnit.test("pivot related context is not saved in the spreadsheet", async function (assert) {
        const context = {
            pivot_row_groupby: ["foo"],
            pivot_column_groupby: ["bar"],
            pivot_measures: ["probability"],
            default_stage_id: 5,
        };
        const { model } = await createSpreadsheetFromPivotView({
            additionalContext: context,
            actions: async (target) => {
                await toggleMenu(target, "Measures");
                await toggleMenuItem(target, "Count");
            },
            mockRPC: function (route, args) {
                if (args.method === "read_group") {
                    assert.step(args.kwargs.fields.join(","));
                }
            },
        });
        assert.verifySteps([
            // initial view
            "probability:avg",
            "probability:avg",
            "probability:avg",
            "probability:avg",
            // adding count in the view
            "probability:avg,__count",
            "probability:avg,__count",
            "probability:avg,__count",
            "probability:avg,__count",
            // loaded in the spreadsheet
            "probability:avg,__count",
            "probability:avg,__count",
            "probability:avg,__count",
            "probability:avg,__count",
        ]);
        assert.deepEqual(
            model.exportData().pivots[1].context,
            {
                default_stage_id: 5,
            },
            "pivot related context is not stored in context"
        );
    });

    QUnit.test("sort first pivot column (ascending)", async (assert) => {
        const { model } = await createSpreadsheetFromPivotView({
            actions: async (target) => {
                await click(target.querySelector("thead .o_pivot_measure_row"));
            },
        });
        assert.strictEqual(getCellValue(model, "A3"), "No");
        assert.strictEqual(getCellValue(model, "A4"), "Yes");
        assert.strictEqual(getCellValue(model, "B3"), "");
        assert.strictEqual(getCellValue(model, "B4"), 11);
        assert.strictEqual(getCellValue(model, "C3"), 15);
        assert.strictEqual(getCellValue(model, "C4"), "");
        assert.strictEqual(getCellValue(model, "F3"), 15);
        assert.strictEqual(getCellValue(model, "F4"), 116);
        assert.deepEqual(model.getters.getPivotDefinition(1).sortedColumn, {
            groupId: [[], [1]],
            measure: "probability",
            order: "asc",
            originIndexes: [0],
        });
    });

    QUnit.test("sort first pivot column (descending)", async (assert) => {
        const { model } = await createSpreadsheetFromPivotView({
            actions: async (target) => {
                await click(target.querySelector("thead .o_pivot_measure_row")); // first click toggles ascending
                await click(target.querySelector("thead .o_pivot_measure_row")); // second is descending
            },
        });
        assert.strictEqual(getCellValue(model, "A3"), "Yes");
        assert.strictEqual(getCellValue(model, "A4"), "No");
        assert.strictEqual(getCellValue(model, "B3"), 11);
        assert.strictEqual(getCellValue(model, "B4"), "");
        assert.strictEqual(getCellValue(model, "C3"), "");
        assert.strictEqual(getCellValue(model, "C4"), 15);
        assert.strictEqual(getCellValue(model, "F3"), 116);
        assert.strictEqual(getCellValue(model, "F4"), 15);
        assert.deepEqual(model.getters.getPivotDefinition(1).sortedColumn, {
            groupId: [[], [1]],
            measure: "probability",
            order: "desc",
            originIndexes: [0],
        });
    });

    QUnit.test("sort second pivot column (ascending)", async (assert) => {
        const { model } = await createSpreadsheetFromPivotView({
            actions: async (target) => {
                await click(target.querySelectorAll("thead .o_pivot_measure_row")[1]);
            },
        });
        assert.strictEqual(getCellValue(model, "A3"), "Yes");
        assert.strictEqual(getCellValue(model, "A4"), "No");
        assert.strictEqual(getCellValue(model, "B3"), 11);
        assert.strictEqual(getCellValue(model, "B4"), "");
        assert.strictEqual(getCellValue(model, "C3"), "");
        assert.strictEqual(getCellValue(model, "C4"), 15);
        assert.strictEqual(getCellValue(model, "F3"), 116);
        assert.strictEqual(getCellValue(model, "F4"), 15);
        assert.deepEqual(model.getters.getPivotDefinition(1).sortedColumn, {
            groupId: [[], [2]],
            measure: "probability",
            order: "asc",
            originIndexes: [0],
        });
    });

    QUnit.test("sort second pivot column (descending)", async (assert) => {
        const { model } = await createSpreadsheetFromPivotView({
            actions: async (target) => {
                await click(target.querySelectorAll("thead .o_pivot_measure_row")[1]); // first click toggles ascending
                await click(target.querySelectorAll("thead .o_pivot_measure_row")[1]); // second is descending
            },
        });
        assert.strictEqual(getCellValue(model, "A3"), "No");
        assert.strictEqual(getCellValue(model, "A4"), "Yes");
        assert.strictEqual(getCellValue(model, "B3"), "");
        assert.strictEqual(getCellValue(model, "B4"), 11);
        assert.strictEqual(getCellValue(model, "C3"), 15);
        assert.strictEqual(getCellValue(model, "C4"), "");
        assert.strictEqual(getCellValue(model, "F3"), 15);
        assert.strictEqual(getCellValue(model, "F4"), 116);
        assert.deepEqual(model.getters.getPivotDefinition(1).sortedColumn, {
            groupId: [[], [2]],
            measure: "probability",
            order: "desc",
            originIndexes: [0],
        });
    });

    QUnit.test("sort second pivot measure (ascending)", async (assert) => {
        const { model } = await createSpreadsheetFromPivotView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,pivot": /* xml */ `
                        <pivot string="Partners">
                            <field name="product_id" type="row"/>
                            <field name="probability" type="measure"/>
                            <field name="foo" type="measure"/>
                        </pivot>`,
                    "partner,false,search": /* xml */ `<search/>`,
                },
            },
            actions: async (target) => {
                await click(target.querySelectorAll("thead .o_pivot_measure_row")[1]);
            },
        });
        assert.strictEqual(getCellValue(model, "A3"), "xphone");
        assert.strictEqual(getCellValue(model, "A4"), "xpad");
        assert.strictEqual(getCellValue(model, "B3"), 10);
        assert.strictEqual(getCellValue(model, "B4"), 121);
        assert.strictEqual(getCellValue(model, "C3"), 12);
        assert.strictEqual(getCellValue(model, "C4"), 20);
        assert.deepEqual(model.getters.getPivotDefinition(1).sortedColumn, {
            groupId: [[], []],
            measure: "foo",
            order: "asc",
            originIndexes: [0],
        });
    });

    QUnit.test("sort second pivot measure (descending)", async (assert) => {
        const { model } = await createSpreadsheetFromPivotView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,pivot": /* xml */ `
                        <pivot string="Partners">
                            <field name="product_id" type="row"/>
                            <field name="probability" type="measure"/>
                            <field name="foo" type="measure"/>
                        </pivot>`,
                    "partner,false,search": /* xml */ `<search/>`,
                },
            },
            actions: async (target) => {
                await click(target.querySelectorAll("thead .o_pivot_measure_row")[1]);
                await click(target.querySelectorAll("thead .o_pivot_measure_row")[1]);
            },
        });
        assert.strictEqual(getCellValue(model, "A3"), "xpad");
        assert.strictEqual(getCellValue(model, "A4"), "xphone");
        assert.strictEqual(getCellValue(model, "B3"), 121);
        assert.strictEqual(getCellValue(model, "B4"), 10);
        assert.strictEqual(getCellValue(model, "C3"), 20);
        assert.strictEqual(getCellValue(model, "C4"), 12);
        assert.deepEqual(model.getters.getPivotDefinition(1).sortedColumn, {
            groupId: [[], []],
            measure: "foo",
            order: "desc",
            originIndexes: [0],
        });
    });

    QUnit.test("search view with group by and additional row group", async (assert) => {
        const { model } = await createSpreadsheetFromPivotView({
            additionalContext: { search_default_group_name: true },
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,pivot": /* xml */ `
                        <pivot>
                        </pivot>`,
                    "partner,false,search": /* xml */ `
                    <search>
                        <group>
                            <filter name="group_name" context="{'group_by':'name'}"/>
                            <filter name="group_foo" context="{'group_by':'foo'}"/>
                        </group>
                    </search>
                `,
                },
            },
            actions: async (target) => {
                await click(target.querySelectorAll("tbody .o_pivot_header_cell_closed")[0]);
                // group by foo
                await click(target.querySelector(".dropdown-menu span:nth-child(2)"));
            },
        });
        assert.strictEqual(getCellContent(model, "A1"), "");
        assert.strictEqual(getCellContent(model, "A2"), "name");
        assert.strictEqual(getCellContent(model, "A3"), '=ODOO.PIVOT.HEADER(1,"name","false")');
        assert.strictEqual(
            getCellContent(model, "A4"),
            '=ODOO.PIVOT.HEADER(1,"name","false","foo",1)'
        );
        assert.strictEqual(
            getCellContent(model, "A5"),
            '=ODOO.PIVOT.HEADER(1,"name","false","foo",2)'
        );
        assert.strictEqual(
            getCellContent(model, "A6"),
            '=ODOO.PIVOT.HEADER(1,"name","false","foo",12)'
        );
        assert.strictEqual(
            getCellContent(model, "A7"),
            '=ODOO.PIVOT.HEADER(1,"name","false","foo",17)'
        );
        assert.strictEqual(
            getCellContent(model, "B2"),
            '=ODOO.PIVOT.HEADER(1,"measure","__count")'
        );
    });

    QUnit.test("Pivot name can be changed from the dialog", async (assert) => {
        assert.expect(2);

        await spawnPivotViewForSpreadsheet();

        let spreadsheetAction;
        patchWithCleanup(SpreadsheetAction.prototype, {
            setup() {
                super.setup();
                spreadsheetAction = this;
            },
        });
        await click(document.body.querySelector(".o_pivot_add_spreadsheet"));
        /** @type {HTMLInputElement} */
        const name = document.body.querySelector(".o_spreadsheet_name");
        name.value = "New name";
        await triggerEvent(name, null, "input");
        await click(document.querySelector(".modal-content > .modal-footer > .btn-primary"));
        const model = getSpreadsheetActionModel(spreadsheetAction);
        await waitForDataSourcesLoaded(model);
        assert.equal(model.getters.getPivotName("1"), "New name");
        assert.equal(model.getters.getPivotDisplayName("1"), "(#1) New name");
    });

    QUnit.test("Pivot name is not changed if the name is empty", async (assert) => {
        assert.expect(1);

        await spawnPivotViewForSpreadsheet();

        let spreadsheetAction;
        patchWithCleanup(SpreadsheetAction.prototype, {
            setup() {
                super.setup();
                spreadsheetAction = this;
            },
        });
        await click(document.body.querySelector(".o_pivot_add_spreadsheet"));
        document.body.querySelector(".o_spreadsheet_name").value = "";
        await click(document.querySelector(".modal-content > .modal-footer > .btn-primary"));
        await nextTick();
        const model = getSpreadsheetActionModel(spreadsheetAction);
        await waitForDataSourcesLoaded(model);
        assert.equal(model.getters.getPivotName("1"), "Partners by Foo");
    });

    QUnit.test("Check pivot measures with m2o field", async function (assert) {
        assert.expect(3);
        const data = getBasicData();
        data.partner.records.push(
            { active: true, id: 5, foo: 12, bar: true, product_id: 37, probability: 50 },
            { active: true, id: 6, foo: 17, bar: true, product_id: 41, probability: 12 },
            { active: true, id: 7, foo: 17, bar: true, product_id: 37, probability: 13 },
            { active: true, id: 8, foo: 17, bar: true, product_id: 37, probability: 14 }
        );
        const { model } = await createSpreadsheetFromPivotView({
            serverData: {
                models: data,
                views: {
                    "partner,false,pivot": `
                            <pivot string="Partners">
                                <field name="foo" type="col"/>
                                <field name="bar" type="row"/>
                                <field name="product_id" type="measure"/>
                            </pivot>`,
                    "partner,false,search": `<search/>`,
                },
            },
        });
        assert.equal(
            getCellValue(model, "B4"),
            1,
            "[Cell B3] There is one distinct product for 'foo - 1' and 'bar - true'"
        );
        assert.equal(
            getCellValue(model, "D4"),
            1,
            "[Cell C3] There is one distinct product for 'foo - 12' and 'bar - true'"
        );
        assert.equal(
            getCellValue(model, "E4"),
            2,
            "[Cell D3] There are two distinct products for 'foo - 17' and 'bar - true'"
        );
    });

    QUnit.test("Styling on row headers", async function (assert) {
        assert.expect(10);

        const { model } = await createSpreadsheetFromPivotView({
            serverData: {
                models: getBasicData(),
                views: {
                    "partner,false,pivot": `
                            <pivot string="Partners">
                                <field name="product_id" type="row"/>
                                <field name="bar" type="row"/>
                                <field name="foo" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
                    "partner,false,search": `<search/>`,
                },
            },
        });
        const styleMainheader = {
            fillColor: "#E6F2F3",
            bold: true,
        };
        const styleSubHeader = {
            fillColor: "#E6F2F3",
        };
        const styleSubSubHeader = undefined;
        assert.deepEqual(getCell(model, "A3").style, styleMainheader);
        assert.deepEqual(getCell(model, "A4").style, styleSubHeader);
        assert.deepEqual(getCell(model, "A5").style, styleSubSubHeader);
        assert.deepEqual(getCell(model, "A6").style, styleMainheader);
        assert.deepEqual(getCell(model, "A7").style, styleSubHeader);
        assert.deepEqual(getCell(model, "A8").style, styleSubSubHeader);
        assert.deepEqual(getCell(model, "A9").style, styleSubHeader);
        assert.deepEqual(getCell(model, "A10").style, styleSubSubHeader);
        assert.deepEqual(getCell(model, "A11").style, styleSubSubHeader);
        assert.deepEqual(getCell(model, "A12").style, styleMainheader);
    });
});
