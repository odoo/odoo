/** @odoo-module */

import {
    click,
    getFixture,
    triggerEvent,
    patchWithCleanup,
    nextTick,
    editInput,
} from "@web/../tests/helpers/utils";
import { createBasicChart } from "@spreadsheet/../tests/utils/commands";
import { createSpreadsheet } from "../spreadsheet_test_utils";
import { createSpreadsheetFromGraphView, openChartSidePanel } from "../utils/chart_helpers";
import { GraphRenderer } from "@web/views/graph/graph_renderer";
import { patchGraphSpreadsheet } from "@spreadsheet_edition/assets/graph_view/graph_view";
import * as dsHelpers from "@web/../tests/core/domain_selector_tests";

function beforeEach() {
    patchWithCleanup(GraphRenderer.prototype, patchGraphSpreadsheet());
}

QUnit.module("documents_spreadsheet > chart side panel", { beforeEach }, () => {
    QUnit.test("Open a chart panel", async (assert) => {
        const { model, env } = await createSpreadsheetFromGraphView();
        await openChartSidePanel(model, env);
        const target = getFixture();
        assert.ok(target.querySelector(".o-sidePanel .o-sidePanelBody .o-chart"));
    });

    QUnit.test("From an Odoo chart, can only change to an Odoo chart", async (assert) => {
        const { model, env } = await createSpreadsheetFromGraphView();
        await openChartSidePanel(model, env);
        const target = getFixture();
        /** @type {NodeListOf<HTMLOptionElement>} */
        const options = target.querySelectorAll(".o-type-selector option");
        assert.strictEqual(options.length, 3);
        assert.strictEqual(options[0].value, "odoo_bar");
        assert.strictEqual(options[1].value, "odoo_line");
        assert.strictEqual(options[2].value, "odoo_pie");
    });

    QUnit.test(
        "From a spreadsheet chart, can only change to a spreadsheet chart",
        async (assert) => {
            const { model, env } = await createSpreadsheet();
            createBasicChart(model, "1");
            await openChartSidePanel(model, env);
            const target = getFixture();
            /** @type {NodeListOf<HTMLOptionElement>} */
            const options = target.querySelectorAll(".o-type-selector option");
            assert.strictEqual(options.length, 5);
            assert.strictEqual(options[0].value, "bar");
            assert.strictEqual(options[1].value, "line");
            assert.strictEqual(options[2].value, "pie");
            assert.strictEqual(options[3].value, "scorecard");
            assert.strictEqual(options[4].value, "gauge");
        }
    );

    QUnit.test("Change odoo chart type", async (assert) => {
        const { model, env } = await createSpreadsheetFromGraphView();
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        assert.strictEqual(model.getters.getChart(chartId).type, "odoo_bar");
        await openChartSidePanel(model, env);
        const target = getFixture();
        /** @type {HTMLSelectElement} */
        const select = target.querySelector(".o-type-selector");
        select.value = "odoo_pie";
        await triggerEvent(select, null, "change");
        assert.strictEqual(model.getters.getChart(chartId).type, "odoo_pie");
        select.value = "odoo_line";
        await triggerEvent(select, null, "change");
        assert.strictEqual(model.getters.getChart(chartId).type, "odoo_line");
        assert.strictEqual(model.getters.getChart(chartId).verticalAxisPosition, "left");
        assert.strictEqual(model.getters.getChart(chartId).stacked, false);
        select.value = "odoo_bar";
        await triggerEvent(select, null, "change");
        assert.strictEqual(model.getters.getChart(chartId).type, "odoo_bar");
        assert.strictEqual(model.getters.getChart(chartId).stacked, false);
    });

    QUnit.test("stacked line chart", async (assert) => {
        const { model, env } = await createSpreadsheetFromGraphView();
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        await openChartSidePanel(model, env);
        const target = getFixture();
        /** @type {HTMLSelectElement} */
        const select = target.querySelector(".o-type-selector");
        select.value = "odoo_line";
        await triggerEvent(select, null, "change");

        // checked by default
        assert.strictEqual(model.getters.getChart(chartId).stacked, true);
        assert.containsOnce(target, ".o_checkbox input:checked", "checkbox should be checked");

        // uncheck
        await click(target, ".o_checkbox input:checked");
        assert.strictEqual(model.getters.getChart(chartId).stacked, false);
        assert.containsNone(
            target,
            ".o_checkbox input:checked",
            "checkbox should no longer be checked"
        );

        // check
        await click(target, ".o_checkbox input[name='stackedBar']");
        assert.strictEqual(model.getters.getChart(chartId).stacked, true);
        assert.containsOnce(target, ".o_checkbox input:checked", "checkbox should be checked");
    });

    QUnit.test("Change the title of a chart", async (assert) => {
        const { model, env } = await createSpreadsheetFromGraphView();
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        assert.strictEqual(model.getters.getChart(chartId).type, "odoo_bar");
        await openChartSidePanel(model, env);
        const target = getFixture();
        await click(target, ".o-panel-design");
        /** @type {HTMLInputElement} */
        const input = target.querySelector(".o-chart-title input");
        assert.strictEqual(model.getters.getChart(chartId).title, "Untitled");
        await editInput(input, null, "bla");
        assert.strictEqual(model.getters.getChart(chartId).title, "bla");
    });

    QUnit.test("Open chart odoo's data properties", async function (assert) {
        const target = getFixture();
        const { model, env } = await createSpreadsheetFromGraphView();
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];

        // opening from a chart
        model.dispatch("SELECT_FIGURE", { id: chartId });
        env.openSidePanel("ChartPanel");
        await nextTick();

        const sections = target.querySelectorAll(".o-section");
        assert.equal(sections.length, 6, "it should have 6 sections");
        const [, , pivotModel, domain, , measures] = sections;

        assert.equal(pivotModel.children[0].innerText, "Model");
        assert.equal(pivotModel.children[1].innerText, "Partner (partner)");

        assert.equal(domain.children[0].innerText, "Domain");
        assert.equal(domain.children[1].innerText, "Match all records\nInclude archived");

        assert.ok(measures.children[0].innerText.startsWith("Last updated at"));
        assert.equal(measures.children[1].innerText, "Refresh values");
    });

    QUnit.test("Update the chart domain from the side panel", async function (assert) {
        const { model, env } = await createSpreadsheetFromGraphView({
            mockRPC(route) {
                if (route === "/web/domain/validate") {
                    return true;
                }
            },
        });
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        model.dispatch("SELECT_FIGURE", { id: chartId });
        env.openSidePanel("ChartPanel");
        await nextTick();
        const fixture = getFixture();
        await click(fixture.querySelector(".o_edit_domain"));
        await dsHelpers.addNewRule(fixture);
        await click(fixture.querySelector(".modal-footer .btn-primary"));
        assert.deepEqual(model.getters.getChartDefinition(chartId).searchParams.domain, [
            ["id", "=", 1],
        ]);
        assert.equal(dsHelpers.getConditionText(fixture), "ID = 1");
    });

    QUnit.test("Cumulative line chart", async (assert) => {
        const { model, env } = await createSpreadsheetFromGraphView();
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        await openChartSidePanel(model, env);
        const target = getFixture();
        /** @type {HTMLSelectElement} */
        const select = target.querySelector(".o-type-selector");
        select.value = "odoo_line";
        await triggerEvent(select, null, "change");
        await click(target, ".o_checkbox input[name='stackedBar']");
        await click(target, ".o_checkbox input[name='cumulative']");
        // check
        assert.strictEqual(model.getters.getChart(chartId).cumulative, true);
        assert.containsOnce(target, ".o_checkbox input:checked", "checkbox should be checked");

        // uncheck
        await click(target, ".o_checkbox input[name='cumulative']");
        assert.strictEqual(model.getters.getChart(chartId).cumulative, false);
        assert.containsNone(
            target,
            ".o_checkbox input:checked",
            "checkbox should no longer be checked"
        );
    });
});
