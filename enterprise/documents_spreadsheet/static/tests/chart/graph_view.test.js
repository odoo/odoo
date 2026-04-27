import {
    createSpreadsheetFromGraphView,
    spawnGraphViewForSpreadsheet,
} from "@documents_spreadsheet/../tests/helpers/chart_helpers";
import {
    defineDocumentSpreadsheetModels,
    getBasicServerData,
} from "@documents_spreadsheet/../tests/helpers/data";
import { SpreadsheetAction } from "@documents_spreadsheet/bundle/actions/spreadsheet_action";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { getSpreadsheetActionModel } from "@spreadsheet_edition/../tests/helpers/webclient_helpers";
import { patchGraphSpreadsheet } from "@spreadsheet_edition/assets/graph_view/graph_view";
import {
    contains,
    defineActions,
    patchWithCleanup,
    toggleMenu,
    toggleMenuItem,
} from "@web/../tests/web_test_helpers";
import { GraphRenderer } from "@web/views/graph/graph_renderer";
import { user } from "@web/core/user";

defineDocumentSpreadsheetModels();
describe.current.tags("desktop");

beforeEach(() => {
    patchWithCleanup(GraphRenderer.prototype, patchGraphSpreadsheet());
});

test("simple chart insertion", async () => {
    const { model } = await createSpreadsheetFromGraphView();
    const sheetId = model.getters.getActiveSheetId();
    expect(".o-sidePanelBody .o-chart").toHaveCount(1);
    expect(model.getters.getChartIds(sheetId).length).toBe(1);
});

test("The chart mode is the selected one", async () => {
    const { model } = await createSpreadsheetFromGraphView({
        actions: async (target) => {
            await contains(".fa-pie-chart").click();
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    expect(model.getters.getChartIds(sheetId).length).toBe(1);
    const chartId = model.getters.getChartIds(sheetId)[0];
    expect(model.getters.getChart(chartId).type).toBe("odoo_pie");
});

test("Line charts are inserted as stacked area charts", async (assert) => {
    const { model } = await createSpreadsheetFromGraphView({
        actions: async (target) => {
            await contains(".fa-line-chart").click();
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId);
    const definition = model.getters.getChartDefinition(chartId);
    expect(definition.fillArea).toBe(true);
    expect(definition.stacked).toBe(true);
});

test("The chart order is the selected one when selecting desc", async () => {
    const { model } = await createSpreadsheetFromGraphView({
        actions: async (target) => {
            await contains(".fa-sort-amount-desc").click();
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    expect(model.getters.getChartIds(sheetId).length).toBe(1);
    const chartId = model.getters.getChartIds(sheetId)[0];
    expect(model.getters.getChart(chartId).metaData.order).toBe("DESC");
});

test("The chart order is the selected one when selecting asc", async () => {
    const { model } = await createSpreadsheetFromGraphView({
        actions: async (target) => {
            await contains(".fa-sort-amount-asc").click();
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    expect(model.getters.getChartIds(sheetId).length).toBe(1);
    const chartId = model.getters.getChartIds(sheetId)[0];
    expect(model.getters.getChart(chartId).metaData.order).toBe("ASC");
});

test("graph order is not saved in spreadsheet context", async () => {
    const context = {
        graph_mode: "bar",
        graph_order: "ASC",
    };
    const { model } = await createSpreadsheetFromGraphView({
        additionalContext: context,
        actions: async (target) => {
            await contains(".fa-sort-amount-desc").click();
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    expect(model.getters.getChart(chartId).metaData.order).toBe("DESC");
    expect(model.exportData().sheets[0].figures[0].data.searchParams.context).toEqual(
        {
            graph_mode: "bar",
        },
        { message: "graph order is not stored in context" }
    );
});

test("graph measure is not saved in spreadsheet context", async () => {
    const context = {
        graph_measure: "__count__",
        graph_mode: "bar",
    };
    const { model } = await createSpreadsheetFromGraphView({
        additionalContext: context,
        actions: async () => {
            await toggleMenu("Measures");
            await toggleMenuItem("Foo");
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    expect(model.getters.getChart(chartId).metaData.measure).toBe("foo");
    expect(model.exportData().sheets[0].figures[0].data.searchParams.context).toEqual(
        {
            graph_mode: "bar",
        },
        { message: "graph measure is not stored in context" }
    );
});

test("can insert chart from action with evaluated context", async function () {
    const actionXmlId = "spreadsheet.partner_action";
    defineActions([
        {
            id: 1,
            name: "partner Action",
            res_model: "partner",
            xml_id: actionXmlId,
            views: [[false, "graph"]],
            context: "{'my_evaluated_context_key': active_id}",
        },
    ]);

    const { model } = await createSpreadsheetFromGraphView({
        actionXmlId,
        additionalContext: { active_id: 1 },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    expect(model.getters.getChart(chartId).actionXmlId).toBe(actionXmlId);
});

test("Chart name can be changed from the dialog", async () => {
    await spawnGraphViewForSpreadsheet();

    let spreadsheetAction;
    patchWithCleanup(SpreadsheetAction.prototype, {
        setup() {
            super.setup();
            spreadsheetAction = this;
        },
    });
    await contains(document.body.querySelector(".o_graph_insert_spreadsheet")).click();
    /** @type {HTMLInputElement} */
    await contains(".o_sp_name").edit("New name");
    await contains(".modal-content > .modal-footer > .btn-primary").click();
    const model = getSpreadsheetActionModel(spreadsheetAction);
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getChartIds(sheetId)[0];
    expect(model.getters.getChart(chartId).title.text).toBe("New name");
});

test("graph with a contextual domain", async () => {
    const uid = user.userId;
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
                expect(args.kwargs.domain).toEqual([["foo", "=", uid]], {
                    message: "data should be fetched with the evaluated the domain",
                });
                expect.step("web_read_group");
            }
        },
    });
    const sheetId = model.getters.getActiveSheetId();
    const chartId = model.getters.getFigures(sheetId)[0].id;

    const chart = model.getters.getChartDefinition(chartId);
    expect(chart.searchParams.domain).toBe('[("foo", "=", uid)]');
    expect(model.exportData().sheets[0].figures[0].data.searchParams.domain).toEqual(
        '[("foo", "=", uid)]',
        { message: "domain is exported with the dynamic value" }
    );
    expect.verifySteps(["web_read_group", "web_read_group"]);
});

test("'cumulated_start' is fetched from the graph view", async () => {
    const serverData = getBasicServerData();
    serverData.views["partner,false,graph"] = /* xml */ `
        <graph string="Partner" cumulated_start="true">
            <field name="foo" type="measure"/>
        </graph>
    `;
    const { model } = await createSpreadsheetFromGraphView({ serverData });

    const sheetId = model.getters.getActiveSheetId();
    const chartIds = model.getters.getChartIds(sheetId)
    expect(chartIds.length).toBe(1);
    expect(model.getters.getChart(chartIds[0]).metaData.cumulatedStart).toBe(true);
})