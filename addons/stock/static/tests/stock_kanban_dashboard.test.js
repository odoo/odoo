import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

import "@stock/components/stock_overview/stock_overview";

const sampleGraph = JSON.stringify([
    {
        key: "Sample",
        values: [{ value: 0, type: "sample", label: "before" }],
    },
]);
const realGraph = JSON.stringify([
    {
        key: "Real",
        values: [{ value: 3, type: "present", label: "today" }],
    },
]);

class PickingType extends models.Model {
    _name = "stock.picking.type";

    name = fields.Char();
    kanban_dashboard_graph = fields.Text();

    _records = [
        { id: 1, name: "Receipts", kanban_dashboard_graph: sampleGraph },
        { id: 2, name: "Delivery Orders", kanban_dashboard_graph: sampleGraph },
    ];
}
defineModels([PickingType]);
defineMailModels();

const cardTemplate = (fieldXml) => /* xml */ `
    <kanban js_class="stock_dashboard_kanban">
        <templates>
            <t t-name="card">
                <field name="name"/>
                ${fieldXml}
            </t>
        </templates>
    </kanban>`;

test("does not crash when kanban_dashboard_graph is not in the arch (e.g. removed via Studio)", async () => {
    await mountView({
        type: "kanban",
        resModel: "stock.picking.type",
        arch: cardTemplate(""),
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(2);
});

test("still renders when all kanban_dashboard_graph data is sample", async () => {
    await mountView({
        type: "kanban",
        resModel: "stock.picking.type",
        arch: cardTemplate(
            `<field name="kanban_dashboard_graph" graph_type="bar" widget="picking_type_dashboard_graph"/>`
        ),
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(2);
    expect(".o_dashboard_graph canvas").toHaveCount(2);
});

test("still renders when kanban_dashboard_graph data is a mix of sample and real records", async () => {
    PickingType._records[1].kanban_dashboard_graph = realGraph;

    await mountView({
        type: "kanban",
        resModel: "stock.picking.type",
        arch: cardTemplate(
            `<field name="kanban_dashboard_graph" graph_type="bar" widget="picking_type_dashboard_graph"/>`
        ),
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(2);
    expect(".o_dashboard_graph canvas").toHaveCount(2);
});
