import { expect, test } from "@odoo/hoot";
import { click, press } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    defineModels,
    fields,
    findComponent,
    models,
    mountView,
} from "@web/../tests/web_test_helpers";
import { KanbanController } from "@web/views/kanban/kanban_controller";

const graph_values = [
    { value: 300, label: "5-11 Dec" },
    { value: 500, label: "12-18 Dec" },
    { value: 100, label: "19-25 Dec" },
];

class Partner extends models.Model {
    int_field = fields.Integer({
        string: "int_field",
        sortable: true,
        searchable: true,
    });
    selection = fields.Selection({
        string: "Selection",
        searchable: true,
        selection: [
            ["normal", "Normal"],
            ["blocked", "Blocked"],
            ["done", "Done"],
        ],
    });
    graph_data = fields.Text({ string: "Graph Data" });
    graph_type = fields.Selection({
        string: "Graph Type",
        selection: [
            ["line", "Line"],
            ["bar", "Bar"],
        ],
    });

    _records = [
        {
            id: 1,
            int_field: 10,
            selection: "blocked",
            graph_type: "bar",
            graph_data: JSON.stringify([
                {
                    color: "blue",
                    title: "Partner 1",
                    values: graph_values,
                    key: "A key",
                    area: true,
                },
            ]),
        },
        {
            id: 2,
            display_name: "second record",
            int_field: 0,
            selection: "normal",
            graph_type: "line",
            graph_data: JSON.stringify([
                {
                    color: "red",
                    title: "Partner 0",
                    values: graph_values,
                    key: "A key",
                    area: true,
                },
            ]),
        },
    ];
}
class User extends models.Model {
    _name = "res.users";
    has_group() {
        return true;
    }
}
defineModels([Partner, User]);

// Kanban
// WOWL remove this helper and user the control panel instead
const reload = async (kanban, params = {}) => {
    kanban.env.searchModel.reload(params);
    kanban.env.searchModel.search();
    await animationFrame();
};

test.tags("desktop");
test("JournalDashboardGraphField is rendered correctly", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: /* xml */ `
            <kanban>
                <field name="graph_type"/>
                <templates>
                    <t t-name="card">
                        <field name="graph_data" t-att-graph_type="record.graph_type.raw_value" widget="dashboard_graph"/>
                    </t>
                </templates>
            </kanban>`,
        domain: [["id", "in", [1, 2]]],
    });
    expect(".o_dashboard_graph canvas").toHaveCount(2, {
        message: "there should be two graphs rendered",
    });
    expect(".o_kanban_record:nth-child(1) .o_graph_barchart").toHaveCount(1, {
        message: "graph of first record should be a barchart",
    });
    expect(".o_kanban_record:nth-child(2) .o_graph_linechart").toHaveCount(1, {
        message: "graph of second record should be a linechart",
    });

    // reload kanban
    await click("input.o_searchview_input");
    await press("Enter");
    await animationFrame();

    expect(".o_dashboard_graph canvas").toHaveCount(2, {
        message: "there should be two graphs rendered",
    });
});

test("rendering of a JournalDashboardGraphField in an updated grouped kanban view", async () => {
    const view = await mountView({
        type: "kanban",
        resModel: "partner",
        arch: /* xml */ `
            <kanban>
                <field name="graph_type"/>
                <templates>
                    <t t-name="card">
                        <field name="graph_data" t-att-graph_type="record.graph_type.raw_value" widget="dashboard_graph"/>
                    </t>
                </templates>
            </kanban>`,
        domain: [["id", "in", [1, 2]]],
    });
    const kanban = findComponent(view, (component) => component instanceof KanbanController);
    expect(".o_dashboard_graph canvas").toHaveCount(2, {
        message: "there should be two graph rendered",
    });
    await reload(kanban, { groupBy: ["selection"], domain: [["int_field", "=", 10]] });

    expect(".o_dashboard_graph canvas").toHaveCount(1, {
        message: "there should be one graph rendered",
    });
});
