/** @odoo-module */

import { patchGraphSpreadsheet } from "@spreadsheet_edition/assets/graph_view/graph_view";
import { SpreadsheetAction } from "@documents_spreadsheet/bundle/actions/spreadsheet_action";
import { click, patchWithCleanup, triggerEvent } from "@web/../tests/helpers/utils";
import { GraphRenderer } from "@web/views/graph/graph_renderer";
import {
    createSpreadsheetFromGraphView,
    spawnGraphViewForSpreadsheet,
} from "../utils/chart_helpers";
import { getSpreadsheetActionModel } from "@spreadsheet_edition/../tests/utils/webclient_helpers";
import { getBasicServerData } from "@spreadsheet/../tests/utils/data";
import { toggleMenu, toggleMenuItem } from "@web/../tests/search/helpers";
import { session } from "@web/session";

function beforeEach() {
    patchWithCleanup(GraphRenderer.prototype, patchGraphSpreadsheet());
}

QUnit.module("documents_spreadsheet > graph view", { beforeEach }, () => {
    QUnit.test("simple chart insertion", async (assert) => {
        const { model } = await createSpreadsheetFromGraphView();
        const sheetId = model.getters.getActiveSheetId();
        assert.strictEqual(model.getters.getChartIds(sheetId).length, 1);
    });

    QUnit.test("The chart mode is the selected one", async (assert) => {
        const { model } = await createSpreadsheetFromGraphView({
            actions: async (target) => {
                await click(target, ".fa-pie-chart");
            },
        });
        const sheetId = model.getters.getActiveSheetId();
        assert.strictEqual(model.getters.getChartIds(sheetId).length, 1);
        const chartId = model.getters.getChartIds(sheetId)[0];
        assert.strictEqual(model.getters.getChart(chartId).type, "odoo_pie");
    });

    QUnit.test("The chart order is the selected one when selecting desc", async (assert) => {
        const { model } = await createSpreadsheetFromGraphView({
            actions: async (target) => {
                await click(target, ".fa-sort-amount-desc");
            },
        });
        const sheetId = model.getters.getActiveSheetId();
        assert.strictEqual(model.getters.getChartIds(sheetId).length, 1);
        const chartId = model.getters.getChartIds(sheetId)[0];
        assert.strictEqual(model.getters.getChart(chartId).metaData.order, "DESC");
    });

    QUnit.test("The chart order is the selected one when selecting asc", async (assert) => {
        const { model } = await createSpreadsheetFromGraphView({
            actions: async (target) => {
                await click(target, ".fa-sort-amount-asc");
            },
        });
        const sheetId = model.getters.getActiveSheetId();
        assert.strictEqual(model.getters.getChartIds(sheetId).length, 1);
        const chartId = model.getters.getChartIds(sheetId)[0];
        assert.strictEqual(model.getters.getChart(chartId).metaData.order, "ASC");
    });

    QUnit.test("graph order is not saved in spreadsheet context", async (assert) => {
        const context = {
            graph_mode: "bar",
            graph_order: "ASC",
        };
        const { model } = await createSpreadsheetFromGraphView({
            additionalContext: context,
            actions: async (target) => {
                await click(target, ".fa-sort-amount-desc");
            },
        });
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        assert.strictEqual(model.getters.getChart(chartId).metaData.order, "DESC");
        assert.deepEqual(
            model.exportData().sheets[0].figures[0].data.searchParams.context,
            {
                graph_mode: "bar",
            },
            "graph order is not stored in context"
        );
    });

    QUnit.test("graph measure is not saved in spreadsheet context", async (assert) => {
        const context = {
            graph_measure: "__count__",
            graph_mode: "bar",
        };
        const { model } = await createSpreadsheetFromGraphView({
            additionalContext: context,
            actions: async (target) => {
                await toggleMenu(target, "Measures");
                await toggleMenuItem(target, "Foo");
            },
        });
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        assert.strictEqual(model.getters.getChart(chartId).metaData.measure, "foo");
        assert.deepEqual(
            model.exportData().sheets[0].figures[0].data.searchParams.context,
            {
                graph_mode: "bar",
            },
            "graph measure is not stored in context"
        );
    });

    QUnit.test("Chart name can be changed from the dialog", async (assert) => {
        await spawnGraphViewForSpreadsheet();

        let spreadsheetAction;
        patchWithCleanup(SpreadsheetAction.prototype, {
            setup() {
                super.setup();
                spreadsheetAction = this;
            },
        });
        await click(document.body.querySelector(".o_graph_insert_spreadsheet"));
        /** @type {HTMLInputElement} */
        const name = document.body.querySelector(".o_spreadsheet_name");
        name.value = "New name";
        await triggerEvent(name, null, "input");
        await click(document.querySelector(".modal-content > .modal-footer > .btn-primary"));
        const model = getSpreadsheetActionModel(spreadsheetAction);
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getChartIds(sheetId)[0];
        assert.equal(model.getters.getChart(chartId).title, "New name");
    });

    QUnit.test("graph with a contextual domain", async (assert) => {
        const uid = session.user_context.uid;
        const serverData = getBasicServerData();
        serverData.models.partner.records = [
            {
                id: 1,
                probability: 0.5,
                foo: uid,
            },
        ];
        serverData.views["partner,false,search"] = /* xml */ `
            <search>
                <filter string="Filter" name="filter" domain="[('foo', '=', uid)]"/>
            </search>
        `;
        const { model } = await createSpreadsheetFromGraphView({
            serverData,
            additionalContext: { search_default_filter: 1 },
            mockRPC: function (route, args) {
                if (args.method === "web_read_group") {
                    assert.deepEqual(
                        args.kwargs.domain,
                        [["foo", "=", uid]],
                        "data should be fetched with the evaluated the domain"
                    );
                    assert.step("web_read_group");
                }
            },
        });
        const sheetId = model.getters.getActiveSheetId();
        const chartId = model.getters.getFigures(sheetId)[0].id;

        const chart = model.getters.getChartDefinition(chartId);
        assert.deepEqual(chart.searchParams.domain, '[("foo", "=", uid)]');
        assert.deepEqual(
            model.exportData().sheets[0].figures[0].data.searchParams.domain,
            '[("foo", "=", uid)]',
            "domain is exported with the dynamic value"
        );
        assert.verifySteps(["web_read_group", "web_read_group"]);
    });
});
