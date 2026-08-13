import { beforeEach, expect, test } from "@odoo/hoot";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { contains, makeMockServer, mountView, onRpc } from "@web/../tests/web_test_helpers";
import { defineAnalyticModels } from "./analytic_test_helpers";

defineAnalyticModels()
beforeEach(async () => {
    const { env } = await makeMockServer();
    const plan = env['account.analytic.plan'].create({ name: "State", root_id: 1 });
    const accounts = env['account.analytic.account'].create([
        { plan_id: plan, name: "Brussels" },
        { plan_id: plan, name: "Antwerpen" },
        { plan_id: plan, name: "Paris" },
        { plan_id: plan, name: "Marseille" },
        { plan_id: plan, name: "New York" },
        { plan_id: plan, name: "Los Angeles" },
    ])
    env["account.analytic.line"].create([
        { x_plan1_id: accounts[0], analytic_distribution: {[accounts[0]]: 100}, amount: 1 },
        { x_plan1_id: accounts[1], analytic_distribution: {[accounts[1]]: 100}, amount: 10 },
        { x_plan1_id: accounts[2], analytic_distribution: {[accounts[2]]: 100}, amount: 100 },
        { x_plan1_id: accounts[3], analytic_distribution: {[accounts[3]]: 100}, amount: 1000 },
        { x_plan1_id: accounts[4], analytic_distribution: {[accounts[4]]: 100}, amount: 10000 },
        { x_plan1_id: accounts[5], analytic_distribution: {[accounts[5]]: 100}, amount: 100000 },
    ]);
});

test.tags("desktop");
test("Analytic single-edit no dynamic", async () => {
    onRpc("account.analytic.line", "write", (params) => {
        // don't have "to update" information if not in multi edit
        expect(params.args[1].analytic_distribution.__update__).toBe(undefined);
    });
    await mountView({
        type: "list",
        resModel: "account.analytic.line",
        arch: `
            <list multi_edit="1" default_order="id DESC">
                <field name="account_id"/>
                <field name="x_plan1_id"/>
                <field name="analytic_distribution" widget="analytic_distribution" options="{'multi_edit': False}"/>
            </list>`,
    });

    // select the first 2 lines to be able to edit
    await contains(".o_list_table tbody tr:nth-child(1) .o_list_record_selector input").click();
    await contains(".o_list_table tbody tr:nth-child(2) .o_list_record_selector input").click();

    await contains(".o_list_table tbody tr:first .o_field_analytic_distribution").click();
    await animationFrame();
    expect(".analytic_distribution_popup").toHaveCount(1);
    // all the fields should be displayed
    expect(".analytic_distribution_popup tbody tr:first .o_field_many2one").toHaveCount(1);
    // we shouldn't display the button-links to hide/display the fields
    expect(".analytic_distribution_popup .o_list_table thead th:first a").toHaveCount(0);
    await contains(".o_list_renderer").click();
})


test.tags("desktop");
test("Analytic dynamic multi-edit", async () => {
    let to_update;
    onRpc("account.analytic.line", "write", (params) => {
        expect(params.args[1].analytic_distribution.__update__).toEqual(to_update);
    });
    await mountView({
        type: "list",
        resModel: "account.analytic.line",
        arch: `
            <list multi_edit="1" default_order="id DESC">
                <field name="account_id"/>
                <field name="x_plan1_id"/>
                <field name="analytic_distribution" widget="analytic_distribution" options="{'multi_edit': True}"/>
            </list>`,
    });

    expect(".o_list_table tbody tr:nth-child(1) .o_field_analytic_distribution .o_tag_badge_text").toHaveText("Los Angeles");
    expect(".o_list_table tbody tr:nth-child(2) .o_field_analytic_distribution .o_tag_badge_text").toHaveText("New York");

    // select the first 2 lines to be able to edit
    await contains(".o_list_table tbody tr:nth-child(1) .o_list_record_selector input").click();
    await contains(".o_list_table tbody tr:nth-child(2) .o_list_record_selector input").click();

    // everything is empty when opening the widget
    await contains(".o_list_table tbody tr:first .o_field_analytic_distribution").click();
    await animationFrame();
    expect(".analytic_distribution_popup").toHaveCount(1);
    expect(".analytic_distribution_popup tbody tr:first .o_field_many2one").toHaveCount(0);
    await contains(".o_list_renderer").click();  // close the widget
    await contains(".modal-footer .btn-secondary").click();  // cancel confirmation

    // update the right columns when ticked
    to_update = ["x_plan1_id"];
    await contains(".o_list_table tbody tr:first .o_field_analytic_distribution").click();
    await animationFrame();
    await contains(".analytic_distribution_popup .o_list_table thead th:first a").click();
    expect(".analytic_distribution_popup tbody tr:first .o_field_many2one").toHaveCount(1);
    await contains(".analytic_distribution_popup tbody tr:first .o_field_many2one").click();
    await contains(".analytic_distribution_popup tbody tr:first .o_field_many2one input").edit("Brussels", {confirm: false});
    await runAllTimers();
    await contains(".analytic_distribution_popup tbody tr:first .o_field_many2one .o_input_dropdown a").click();
    await contains(".o_list_renderer").click();  // close the widget
    // we don't change the value until it's saved
    expect(".o_list_table tbody tr:nth-child(1) .o_field_analytic_distribution .o_tag_badge_text").toHaveText("Los Angeles");
    expect(".o_list_table tbody tr:nth-child(2) .o_field_analytic_distribution .o_tag_badge_text").toHaveText("New York");
    await contains(".modal-footer .btn-primary").click();  // validate confirmation
    await runAllTimers();
    expect(".o_list_table tbody tr:nth-child(1) .o_field_analytic_distribution .o_tag_badge_text").toHaveText("Brussels");
    expect(".o_list_table tbody tr:nth-child(2) .o_field_analytic_distribution .o_tag_badge_text").toHaveText("Brussels");

    // everything should be back to like the first time we opened it
    to_update = [];
    await contains(".o_list_table tbody tr:first .o_field_analytic_distribution").click();
    await animationFrame();
    expect(".analytic_distribution_popup").toHaveCount(1);
    expect(".analytic_distribution_popup tbody tr:first .o_field_many2one").toHaveCount(0);
    await contains(".o_list_renderer").click();  // close the widget
    await contains(".modal-footer .btn-primary").click();  // validate confirmation
})
