import { beforeEach, expect, test } from "@odoo/hoot";
import { contains, makeMockServer, mountView } from "@web/../tests/web_test_helpers";
import { defineAnalyticModels } from "./analytic_test_helpers";

defineAnalyticModels()
const searchViewArch = `
    <search>
        <filter name="account_id" context="{'group_by': 'account_id'}"/>
        <filter name="x_plan1_id" context="{'group_by': 'x_plan1_id'}"/>
        <filter name="x_plan1_id_1" context="{'group_by': 'x_plan1_id_1'}"/>
        <filter name="x_plan1_id_2" context="{'group_by': 'x_plan1_id_2'}"/>
    </search>
`

beforeEach(async () => {
    const { env } = await makeMockServer();
    const root = env['account.analytic.plan'].create({ name: "State" });
    const eu = env['account.analytic.plan'].create({ name: "Europe", parent_id: root, root_id: root });
    const be = env['account.analytic.plan'].create({ name: "Belgium", parent_id: eu, root_id: root });
    const fr = env['account.analytic.plan'].create({ name: "France", parent_id: eu, root_id: root });
    const am = env['account.analytic.plan'].create({ name: "America", parent_id: root, root_id: root });
    const us = env['account.analytic.plan'].create({ name: "USA", parent_id: am, root_id: root });
    const accounts = env['account.analytic.account'].create([
        { plan_id: be, name: "Brussels" },
        { plan_id: be, name: "Antwerpen" },
        { plan_id: fr, name: "Paris" },
        { plan_id: fr, name: "Marseille" },
        { plan_id: us, name: "New York" },
        { plan_id: us, name: "Los Angeles" },
    ])
    env["account.analytic.line"].create([
        { x_plan1_id: accounts[0], x_plan1_id_1: eu, x_plan1_id_2: be, analytic_distribution: {[accounts[0]]: 100}, amount: 1 },
        { x_plan1_id: accounts[1], x_plan1_id_1: eu, x_plan1_id_2: be, analytic_distribution: {[accounts[1]]: 100}, amount: 10 },
        { x_plan1_id: accounts[2], x_plan1_id_1: eu, x_plan1_id_2: fr, analytic_distribution: {[accounts[2]]: 100}, amount: 100 },
        { x_plan1_id: accounts[3], x_plan1_id_1: eu, x_plan1_id_2: fr, analytic_distribution: {[accounts[3]]: 100}, amount: 1000 },
        { x_plan1_id: accounts[4], x_plan1_id_1: am, x_plan1_id_2: us, analytic_distribution: {[accounts[4]]: 100}, amount: 10000 },
        { x_plan1_id: accounts[5], x_plan1_id_1: am, x_plan1_id_2: us, analytic_distribution: {[accounts[5]]: 100}, amount: 100000 },
    ]);
});

test.tags("desktop");
test("Analytic hierachy in list view", async () => {
    await mountView({
        type: "list",
        resModel: "account.analytic.line",
        arch: `<list js_class="analytic_list"><field name="account_id"/></list>`,
        searchViewId: false,
        searchViewArch: searchViewArch,
    });
    await contains(".o_searchview_dropdown_toggler").click()
    await contains(".o_group_by_menu .o_accordion_toggle").click();
    expect(".o_group_by_menu .o_accordion_values .o-dropdown-item").toHaveCount(3);
    await contains(".o_group_by_menu .o_accordion_values .o-dropdown-item:last").click();
    expect(".o_facet_value").toHaveText("Country")
    expect(".o_list_table tbody .o_group_name").toHaveCount(3);
});

test.tags("desktop");
test("Analytic hierachy in kanban view", async () => {
    await mountView({
        type: "kanban",
        resModel: "account.analytic.line",
        arch: `
            <kanban js_class="analytic_kanban">
                <templates>
                    <t t-name="card">
                        <field class="text-muted" name="account_id"/>
                    </t>
                </templates>
            </kanban>`,
        searchViewId: false,
        searchViewArch: searchViewArch,
    });
    await contains(".o_searchview_dropdown_toggler").click()
    await contains(".o_group_by_menu .o_accordion_toggle").click();
    expect(".o_group_by_menu .o_accordion_values .o-dropdown-item").toHaveCount(3);
    await contains(".o_group_by_menu .o_accordion_values .o-dropdown-item:last").click();
    expect(".o_facet_value").toHaveText("Country")
    expect(".o_kanban_renderer .o_kanban_group").toHaveCount(3);
});

test.tags("desktop");
test("Analytic hierachy in pivot view", async () => {
    await mountView({
        type: "pivot",
        resModel: "account.analytic.line",
        arch: `
            <pivot js_class="analytic_pivot">
                <field name="amount" type="measure"/>
            </pivot>`,
        searchViewId: false,
        searchViewArch: searchViewArch,
    });
    await contains(".o_searchview_dropdown_toggler").click()
    await contains(".o_group_by_menu .o_accordion_toggle").click();
    expect(".o_group_by_menu .o_accordion_values .o-dropdown-item").toHaveCount(3);
    await contains(".o_group_by_menu .o_accordion_values .o-dropdown-item:last").click();
    expect(".o_facet_value").toHaveText("Country");
    expect(".o_pivot tbody .o_value").toHaveCount(4); // 3 groups + 1 total

    // Also check the pivot cell choices
    await contains(".o_pivot tbody .o_pivot_header_cell_closed").click()
    await contains(".o_popover .o-dropdown-caret").hover()
    expect(".o_popover.o-dropdown--menu-submenu span.o-dropdown-item").toHaveCount(3);
});

test.tags("desktop");
test("Analytic hierachy in graph view", async () => {
    await mountView({
        type: "graph",
        resModel: "account.analytic.line",
        arch: `<graph js_class="analytic_graph"><field name="account_id"/></graph>`,
        searchViewId: false,
        searchViewArch: searchViewArch,
    });
    await contains(".o_searchview_dropdown_toggler").click()
    await contains(".o_group_by_menu .o_accordion_toggle").click();
    expect(".o_group_by_menu .o_accordion_values .o-dropdown-item").toHaveCount(3);
    await contains(".o_group_by_menu .o_accordion_values .o-dropdown-item:last").click();
    expect(".o_facet_value").toHaveText("Country")
});
