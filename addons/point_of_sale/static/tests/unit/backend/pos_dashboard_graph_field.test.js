import { expect, test } from "@odoo/hoot";
import {
    findComponent,
    makeMockServer,
    MockServer,
    mountView,
} from "@web/../tests/web_test_helpers";
import { PosDashboardGraphField } from "@point_of_sale/backend/pos_dashboard_graph/pos_dashboard_graph_field";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

test("tooltip shows day sales and 7-day total", async () => {
    odoo.pos_config_id = 1;
    odoo.pos_session_id = 1;
    await makeMockServer();
    MockServer.env["pos.config"].write([1], {
        kanban_dashboard_graph: JSON.stringify([
            {
                key: "Sales Last 7 Days",
                is_sample_data: false,
                values: [
                    { x: "13 Oct", y: 40 },
                    { x: "14 Oct", y: 150 },
                ],
            },
        ]),
    });
    const view = await mountView({
        type: "kanban",
        resModel: "pos.config",
        domain: [["id", "=", 1]],
        arch: /* xml */ `
            <kanban>
                <field name="currency_id"/>
                <templates>
                    <t t-name="card">
                        <field name="kanban_dashboard_graph" widget="pos_dashboard_graph" graph_type="line"/>
                    </t>
                </templates>
            </kanban>`,
    });
    expect(".o_dashboard_graph canvas").toHaveCount(1);
    const field = findComponent(view, (c) => c instanceof PosDashboardGraphField);
    const { title, label } = field.getChartConfig().options.plugins.tooltip.callbacks;
    expect(title([{ label: "14 Oct", raw: { y: 150 } }])).toBe("14 Oct: $\u00a0150.00");
    expect(label()).toBe("Sales Last 7 Days: $\u00a0190.00");
});
