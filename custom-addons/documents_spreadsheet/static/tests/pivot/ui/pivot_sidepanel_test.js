/** @odoo-module */

import * as spreadsheet from "@odoo/o-spreadsheet";
import { click, editInput, getFixture, nextTick } from "@web/../tests/helpers/utils";
import {
    getBasicData,
    getBasicPivotArch,
    getBasicServerData,
} from "@spreadsheet/../tests/utils/data";
import { getCellValue } from "@spreadsheet/../tests/utils/getters";
import { selectCell } from "@spreadsheet/../tests/utils/commands";
import { createSpreadsheetFromPivotView } from "../../utils/pivot_helpers";
import { PivotUIPlugin } from "@spreadsheet/pivot/plugins/pivot_ui_plugin";
import { insertPivotInSpreadsheet } from "@spreadsheet/../tests/utils/pivot";
import * as dsHelpers from "@web/../tests/core/domain_selector_tests";

const { cellMenuRegistry } = spreadsheet.registries;

let target;

QUnit.module(
    "documents_spreadsheet > Pivot Side Panel",
    {
        beforeEach: function () {
            target = getFixture();
        },
    },
    function () {
        QUnit.test("Open pivot properties properties", async function (assert) {
            const { model, env } = await createSpreadsheetFromPivotView({
                serverData: {
                    models: getBasicData(),
                    views: {
                        "partner,false,pivot": `
                            <pivot string="Partner" display_quantity="true">
                                <field name="foo" type="col"/>
                                <field name="bar" type="row"/>
                                <field name="probability" type="measure"/>
                            </pivot>`,
                        "partner,false,search": `<search/>`,
                    },
                },
            });
            // opening from a pivot cell
            const sheetId = model.getters.getActiveSheetId();
            const pivotA3 = model.getters.getPivotIdFromPosition({ sheetId, col: 0, row: 2 });
            await model.getters.getAsyncPivotDataSource(pivotA3);
            model.dispatch("SELECT_PIVOT", { pivotId: pivotA3 });
            env.openSidePanel("PIVOT_PROPERTIES_PANEL", {
                pivot: pivotA3,
            });
            await nextTick();
            let title = target.querySelector(".o-sidePanelTitle").innerText;
            assert.equal(title, "Pivot properties");

            const sections = target.querySelectorAll(".o_side_panel_section");
            assert.equal(sections.length, 5, "it should have 5 sections");
            const [pivotName, pivotModel, domain, dimensions, measures] = sections;

            assert.equal(pivotName.children[0].innerText, "Pivot name");
            assert.equal(pivotName.children[1].innerText, "(#1) Partner by Foo");

            assert.equal(pivotModel.children[0].innerText, "Model");
            assert.equal(pivotModel.children[1].innerText, "Partner (partner)");

            assert.equal(domain.children[0].innerText, "Domain");
            assert.equal(domain.children[1].innerText, "Match all records\nInclude archived");

            assert.equal(measures.children[0].innerText, "Measures");
            assert.equal(measures.children[1].innerText, "Count");
            assert.equal(measures.children[2].innerText, "Probability");

            assert.ok(measures.children[3].innerText.startsWith("Last updated at"));
            assert.equal(measures.children[4].innerText, "Refresh values");

            assert.equal(dimensions.children[0].innerText, "Dimensions");
            assert.equal(dimensions.children[1].innerText, "Bar");
            assert.equal(dimensions.children[2].innerText, "Foo");

            // opening from a non pivot cell
            const pivotA1 = model.getters.getPivotIdFromPosition({ sheetId, col: 0, row: 0 });
            model.dispatch("SELECT_PIVOT", { pivotId: pivotA1 });
            env.openSidePanel("PIVOT_PROPERTIES_PANEL", {
                pivot: pivotA1,
            });
            await nextTick();
            title = target.querySelector(".o-sidePanelTitle").innerText;
            assert.equal(title, "Pivot properties");

            assert.containsOnce(target, ".o_side_panel_select");
        });

        QUnit.test("Pivot properties panel shows ascending sorting", async function (assert) {
            const { model, env } = await createSpreadsheetFromPivotView({
                actions: async (target) => {
                    await click(target.querySelector("thead .o_pivot_measure_row"));
                },
            });
            // opening from a pivot cell
            const sheetId = model.getters.getActiveSheetId();
            const pivotA3 = model.getters.getPivotIdFromPosition({ sheetId, col: 0, row: 2 });
            model.dispatch("SELECT_PIVOT", { pivotId: pivotA3 });
            env.openSidePanel("PIVOT_PROPERTIES_PANEL", {
                pivot: pivotA3,
            });
            await nextTick();

            const sections = target.querySelectorAll(".o_side_panel_section");
            assert.equal(sections.length, 6, "it should have 6 sections");
            const pivotSorting = sections[4];

            assert.equal(pivotSorting.children[0].innerText, "Sorting");
            assert.equal(pivotSorting.children[1].innerText, "Probability (ascending)");
        });

        QUnit.test("Pivot properties panel shows descending sorting", async function (assert) {
            const { model, env } = await createSpreadsheetFromPivotView({
                actions: async (target) => {
                    await click(target.querySelector("thead .o_pivot_measure_row"));
                    await click(target.querySelector("thead .o_pivot_measure_row"));
                },
            });
            // opening from a pivot cell
            const sheetId = model.getters.getActiveSheetId();
            const pivotA3 = model.getters.getPivotIdFromPosition({ sheetId, col: 0, row: 2 });
            model.dispatch("SELECT_PIVOT", { pivotId: pivotA3 });
            env.openSidePanel("PIVOT_PROPERTIES_PANEL", {
                pivot: pivotA3,
            });
            await nextTick();

            const sections = target.querySelectorAll(".o_side_panel_section");
            assert.equal(sections.length, 6, "it should have 6 sections");
            const pivotSorting = sections[4];

            assert.equal(pivotSorting.children[0].innerText, "Sorting");
            assert.equal(pivotSorting.children[1].innerText, "Probability (descending)");
        });

        QUnit.test("can refresh a sorted pivot", async function (assert) {
            const { model, env } = await createSpreadsheetFromPivotView({
                actions: async (target) => {
                    await click(target.querySelector("thead .o_pivot_measure_row"));
                },
            });
            // opening from a pivot cell
            const sheetId = model.getters.getActiveSheetId();
            const pivotA3 = model.getters.getPivotIdFromPosition({ sheetId, col: 0, row: 2 });
            model.dispatch("SELECT_PIVOT", { pivotId: pivotA3 });
            env.openSidePanel("PIVOT_PROPERTIES_PANEL", {
                pivot: pivotA3,
            });
            await nextTick();

            let sections = target.querySelectorAll(".o_side_panel_section");
            assert.equal(sections.length, 6, "it should have 6 sections");
            let pivotSorting = sections[4];

            assert.equal(pivotSorting.children[0].innerText, "Sorting");
            assert.equal(pivotSorting.children[1].innerText, "Probability (ascending)");
            await click(target, ".o_refresh_measures");
            sections = target.querySelectorAll(".o_side_panel_section");
            assert.equal(sections.length, 6, "it should have 6 sections");
            pivotSorting = sections[4];
            assert.equal(pivotSorting.children[0].innerText, "Sorting");
            assert.equal(pivotSorting.children[1].innerText, "Probability (ascending)");
        });

        QUnit.test("Pivot focus changes on side panel click", async function (assert) {
            assert.expect(6);
            const { model, env } = await createSpreadsheetFromPivotView();
            await insertPivotInSpreadsheet(model, { arch: getBasicPivotArch() });

            selectCell(model, "L1"); //target empty cell
            const root = cellMenuRegistry.getAll().find((item) => item.id === "pivot_properties");
            root.execute(env);
            assert.notOk(model.getters.getSelectedPivotId(), "No pivot should be selected");
            await nextTick();
            assert.containsN(target, ".o_side_panel_select", 2);
            await click(target.querySelectorAll(".o_side_panel_select")[0]);
            assert.strictEqual(
                model.getters.getSelectedPivotId(),
                "1",
                "The selected pivot should be have the id 1"
            );
            await nextTick();
            await click(target, ".o_pivot_cancel");
            assert.notOk(model.getters.getSelectedPivotId(), "No pivot should be selected anymore");
            assert.containsN(target, ".o_side_panel_select", 2);
            await click(target.querySelectorAll(".o_side_panel_select")[1]);
            assert.strictEqual(
                model.getters.getSelectedPivotId(),
                "2",
                "The selected pivot should be have the id 2"
            );
        });

        QUnit.test(
            "Can refresh the pivot from the pivot properties panel",
            async function (assert) {
                assert.expect(1);

                const data = getBasicData();

                const { model, env } = await createSpreadsheetFromPivotView({
                    serverData: {
                        models: data,
                        views: getBasicServerData().views,
                    },
                });
                data.partner.records.push({
                    active: true,
                    id: 5,
                    foo: 12,
                    bar: true,
                    product: 37,
                    probability: 10,
                    create_date: "2016-02-02",
                    date: "2016-02-02",
                    field_with_array_agg: 1,
                    product_id: 41,
                    tag_ids: [],
                });
                const sheetId = model.getters.getActiveSheetId();
                const pivotA3 = model.getters.getPivotIdFromPosition({ sheetId, col: 0, row: 2 });
                model.dispatch("SELECT_PIVOT", { pivotId: pivotA3 });
                env.openSidePanel("PIVOT_PROPERTIES_PANEL", {});
                await nextTick();
                await click(target.querySelectorAll(".o_refresh_measures")[0]);
                await nextTick();
                assert.equal(getCellValue(model, "D4"), 10 + 10);
            }
        );

        QUnit.test(
            "Open pivot properties properties with non-loaded field",
            async function (assert) {
                const { model, env } = await createSpreadsheetFromPivotView();
                const pivotPlugin = model["handlers"].find(
                    (handler) => handler instanceof PivotUIPlugin
                );
                const dataSource = Object.values(pivotPlugin.dataSources._dataSources)[0];
                // remove all loading promises and the model to simulate the data source is not loaded
                dataSource._loadPromise = undefined;
                dataSource._createModelPromise = undefined;
                dataSource._model = undefined;
                model.dispatch("SELECT_PIVOT", { pivotId: "1" });
                env.openSidePanel("PIVOT_PROPERTIES_PANEL", {
                    pivot: model.getters.getSelectedPivotId(),
                });
                await nextTick();
                const sections = target.querySelectorAll(".o_side_panel_section");
                const fields = sections[3];
                assert.equal(fields.children[1].innerText, "Bar");
                const measures = sections[4];
                assert.equal(measures.children[1].innerText, "Probability");
            }
        );

        QUnit.test("Update the pivot title from the side panel", async function (assert) {
            assert.expect(1);

            const { model, env } = await createSpreadsheetFromPivotView();
            // opening from a pivot cell
            const sheetId = model.getters.getActiveSheetId();
            const pivotA3 = model.getters.getPivotIdFromPosition({ sheetId, col: 0, row: 2 });
            model.dispatch("SELECT_PIVOT", { pivotId: pivotA3 });
            env.openSidePanel("PIVOT_PROPERTIES_PANEL", {
                pivot: pivotA3,
            });
            await nextTick();
            await click(document.body.querySelector(".o_sp_en_rename"));
            await editInput(document, ".o_sp_en_name", "new name");
            await click(document.body.querySelector(".o_sp_en_save"));
            assert.equal(model.getters.getPivotName(pivotA3), "new name");
        });

        QUnit.test("Update the pivot domain from the side panel", async function (assert) {
            const { model, env } = await createSpreadsheetFromPivotView({
                mockRPC(route) {
                    if (route === "/web/domain/validate") {
                        return true;
                    }
                },
            });
            const [pivotId] = model.getters.getPivotIds();
            model.dispatch("SELECT_PIVOT", { pivotId });
            env.openSidePanel("PIVOT_PROPERTIES_PANEL", {
                pivot: pivotId,
            });
            await nextTick();
            const fixture = getFixture();
            await click(fixture.querySelector(".o_edit_domain"));
            await dsHelpers.addNewRule(fixture);
            await click(fixture.querySelector(".modal-footer .btn-primary"));
            assert.deepEqual(model.getters.getPivotDefinition(pivotId).domain, [["id", "=", 1]]);
            assert.equal(dsHelpers.getConditionText(fixture), "ID = 1");
        });

        QUnit.test(
            "Opening the sidepanel of a pivot while the panel of another pivot is open updates the side panel",
            async function (assert) {
                const { model, env } = await createSpreadsheetFromPivotView();
                const arch = /* xml */ `
                    <pivot string="Product">
                        <field name="name" type="col"/>
                        <field name="active" type="row"/>
                        <field name="__count" type="measure"/>
                    </pivot>`;
                await insertPivotInSpreadsheet(model, {
                    arch,
                    resModel: "product",
                });
                const pivotIds = model.getters.getPivotIds();

                model.dispatch("SELECT_PIVOT", { pivotId: pivotIds[0] });
                env.openSidePanel("PIVOT_PROPERTIES_PANEL", {});
                await nextTick();
                let modelName = target.querySelector(".o_side_panel_section .o_model_name");
                assert.equal(modelName.innerText, "Partner (partner)");

                model.dispatch("SELECT_PIVOT", { pivotId: pivotIds[1] });
                env.openSidePanel("PIVOT_PROPERTIES_PANEL", {});
                await nextTick();
                modelName = target.querySelector(".o_side_panel_section .o_model_name");
                assert.equal(modelName.innerText, "Product (product)");
            }
        );

        QUnit.test("Deleting the pivot closes the side panel", async function (assert) {
            const { model, env } = await createSpreadsheetFromPivotView();
            const [pivotId] = model.getters.getPivotIds();
            model.dispatch("SELECT_PIVOT", { pivotId });
            env.openSidePanel("PIVOT_PROPERTIES_PANEL", {
                pivot: pivotId,
            });
            await nextTick();
            const fixture = getFixture();
            const titleSelector = ".o-sidePanelTitle";
            assert.equal(fixture.querySelector(titleSelector).innerText, "Pivot properties");

            model.dispatch("REMOVE_PIVOT", { pivotId });
            await nextTick();
            assert.equal(fixture.querySelector(titleSelector), null);
            assert.equal(model.getters.getSelectedPivotId(), undefined);
        });

        QUnit.test("Undo a pivot insertion closes the side panel", async function (assert) {
            const { model, env } = await createSpreadsheetFromPivotView();
            const [pivotId] = model.getters.getPivotIds();
            model.dispatch("SELECT_PIVOT", { pivotId });
            env.openSidePanel("PIVOT_PROPERTIES_PANEL", {
                pivot: pivotId,
            });
            await nextTick();
            const fixture = getFixture();
            const titleSelector = ".o-sidePanelTitle";
            assert.equal(fixture.querySelector(titleSelector).innerText, "Pivot properties");

            model.dispatch("REQUEST_UNDO");
            model.dispatch("REQUEST_UNDO");
            await nextTick();
            assert.equal(fixture.querySelector(titleSelector), null);
            assert.equal(model.getters.getSelectedPivotId(), undefined);
        });
    }
);
