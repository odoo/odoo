import { expect, test } from "@odoo/hoot";
import { animationFrame, edit, getActiveElement, press } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { defineAnalyticModels } from "./analytic_test_helpers";

defineAnalyticModels();

class AccountAnalyticAccount extends models.Model {
    _name = "account.analytic.account";
    name = fields.Char({ string: "Name" });
    plan_id = fields.Many2one({ string: "Plan", relation: "account.analytic.plan" });
    root_plan_id = fields.Many2one({ string: "Root Plan", relation: "account.analytic.plan" });
    color = fields.Integer({ string: "Color" });
    code = fields.Char({ string: "Ref" });
    partner_id = fields.Many2one({ string: "Partner", relation: "partner" });
    company_id = fields.Many2one({ relation: "res.company" });
    _records = [
        { id: 1, color: 1, root_plan_id: 2, plan_id: 2, name: "RD", company_id: 1 },
        { id: 2, color: 1, root_plan_id: 2, plan_id: 2, name: "HR", company_id: 1 },
        { id: 3, color: 1, root_plan_id: 2, plan_id: 2, name: "FI", company_id: 1 },
        { id: 4, color: 2, root_plan_id: 1, plan_id: 1, name: "Time Off", company_id: 1 },
        { id: 5, color: 2, root_plan_id: 1, plan_id: 1, name: "Operating Costs", company_id: 1 },
        { id: 6, color: 6, root_plan_id: 4, plan_id: 4, name: "Incognito", company_id: 1 },
        { id: 7, color: 5, root_plan_id: 5, plan_id: 5, name: "Belgium", company_id: 1 },
        { id: 8, color: 6, root_plan_id: 5, plan_id: 6, name: "Brussels", company_id: 1 },
        { id: 9, color: 6, root_plan_id: 5, plan_id: 6, name: "Beirut", company_id: 1 },
        { id: 10, color: 6, root_plan_id: 5, plan_id: 6, name: "Berlin", company_id: 1 },
        { id: 11, color: 6, root_plan_id: 5, plan_id: 6, name: "Bruges", company_id: 1 },
        { id: 12, color: 6, root_plan_id: 5, plan_id: 6, name: "Birmingham", company_id: 1 },
        { id: 13, color: 6, root_plan_id: 5, plan_id: 6, name: "Bologna", company_id: 1 },
        { id: 14, color: 6, root_plan_id: 5, plan_id: 6, name: "Bratislava", company_id: 1 },
        { id: 15, color: 6, root_plan_id: 5, plan_id: 6, name: "Budapest", company_id: 1 },
        { id: 16, color: 6, root_plan_id: 5, plan_id: 6, name: "Namur", company_id: 1 },
    ];
    _views = {
        search: `
            <search>
                <field name="name"/>
            </search>
        `,
        list: `
            <list>
                <field name="name"/>
            </list>
        `,
    };
}

class Plan extends models.Model {
    _name = "account.analytic.plan";
    name = fields.Char();
    applicability = fields.Selection({
        string: "Applicability",
        selection: [
            ["mandatory", "Mandatory"],
            ["optional", "Options"],
            ["unavailable", "Unavailable"],
        ],
    });
    color = fields.Integer({ string: "Color" });
    all_account_count = fields.Integer();
    parent_id = fields.Many2one({ relation: "account.analytic.plan" });
    column_name = fields.Char();
    _records = [
        { id: 1, name: "Internal", applicability: "optional", all_account_count: 2, column_name: 'x_plan1_id' },
        { id: 2, name: "Departments", applicability: "mandatory", all_account_count: 3, column_name: 'x_plan2_id' },
        { id: 3, name: "Projects", applicability: "optional", column_name: 'account_id' },
        { id: 4, name: "Hidden", applicability: "unavailable", all_account_count: 1, column_name: 'x_plan4_id' },
        { id: 5, name: "Country", applicability: "optional", all_account_count: 3, column_name: 'x_plan5_id' },
        { id: 6, name: "City", applicability: "optional", all_account_count: 2, parent_id: 5, column_name: 'x_plan5_id' },
    ];
}

class Move extends models.Model {
    line_ids = fields.One2many({
        string: "Move Lines",
        relation: "aml",
        relation_field: "move_line_id",
    });
    _records = [
        { id: 1, display_name: "INV0001", line_ids: [1, 2] },
        { id: 2, display_name: "INV0002", line_ids: [3, 4] },
    ];
}

class Aml extends models.Model {
    label = fields.Char({ string: "Label" });
    amount = fields.Float({ string: "Amount" });
    analytic_distribution = fields.Json({ string: "Analytic" });
    move_id = fields.Many2one({ string: "Account Move", relation: "move" });
    analytic_precision = fields.Integer({ string: "Analytic Precision" });
    company_id = fields.Many2one({ relation: "res.company" });

    _records = [
        {
            id: 1,
            label: "Developer Time",
            amount: 100.0,
            analytic_distribution: { "1, 7": 30.3, 3: 69.704 },
            analytic_precision: 3,
            company_id: 1,
        },
        { id: 2, label: "Coke", amount: 100.0, analytic_distribution: {}, company_id: 1 },
        { id: 3, label: "Sprite", amount: 100.0, analytic_distribution: {}, analytic_precision: 3, company_id: 1 },
        { id: 4, label: "", amount: 100.0, analytic_distribution: {}, company_id: 1 },
    ];
}

defineModels([Aml, AccountAnalyticAccount, Move, Plan]);

test.tags("desktop");
test("analytic field in form view basic features", async () => {
    onRpc("account.analytic.plan", "get_relevant_plans", function ({ model }) {
        return this.env[model].filter((r) => !r.parent_id && r.applicability !== "unavailable");
    });
    await mountView({
        type: "form",
        resModel: "aml",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="label"/>
                        <field name="analytic_distribution" widget="analytic_distribution"/>
                        <field name="amount"/>
                    </group>
                </sheet>
            </form>`,
    });
    // tags
    expect(".o_field_analytic_distribution").toHaveCount(1);
    expect(".badge").toHaveCount(2);
    expect(".badge .o_tag_badge_text:eq(0)").toHaveText("30.3% RD | 69.7% FI");
    expect(".badge .o_tag_badge_text:eq(1)").toHaveText("30.3% Belgium");

    // open popup
    await contains(".o_field_analytic_distribution .o_input_dropdown").click();
    expect(".analytic_distribution_popup").toHaveCount(1);

    // contents of popup
    expect(".analytic_distribution_popup table:eq(0) tr").toHaveCount(4);
    expect(".analytic_distribution_popup table:eq(0) tr:first-of-type #x_plan1_id").toBeFocused();

    // change percentage
    await contains(
        ".analytic_distribution_popup table:eq(0) tr:first-of-type .o_field_percentage input"
    ).edit("19.7001");

    // mandatory plan is red
    expect("th:contains(Departments) .text-danger:contains(50%)").toHaveCount(1);
    // close and open popup with keyboard
    await press("Escape");
    await animationFrame();
    expect(".analytic_distribution_popup").toHaveCount(0);

    await press("ArrowDown");
    await animationFrame();
    expect(".analytic_distribution_popup").toHaveCount(1);

    // add a line
    await contains(
        ".analytic_distribution_popup table:eq(0) .o_field_x2many_list_row_add a"
    ).click();
    expect(
        ".analytic_distribution_popup table:eq(0) tr:nth-of-type(3) .o_field_percentage input"
    ).toHaveValue("50");

    // choose an account for the mandatory plan using the keyboard
    await contains(
        ".analytic_distribution_popup table:eq(0) tr:nth-of-type(3) #x_plan2_id"
    ).click();
    await press("ArrowDown");
    await animationFrame();
    await press("Enter");
    await animationFrame();

    // mandatory plan is green
    expect(
        ".analytic_distribution_popup table:eq(0) th:contains(Departments) .text-success:contains(100%)"
    ).toHaveCount(1);

    // tags
    await contains(".fa-close").click();
    expect(".analytic_distribution_popup").toHaveCount(0);
    expect(".badge").toHaveCount(2);
    expect(".badge:eq(0) .o_tag_badge_text").toHaveText("30.3% RD | 50% HR | 19.7% FI");
    expect(".badge:eq(1) .o_tag_badge_text").toHaveText("30.3% Belgium");
});

test.tags("desktop");
test("analytic field in multi_edit list view + search more", async () => {
    onRpc("account.analytic.plan", "get_relevant_plans", function ({ model, kwargs }) {
        return this.env[model]
            .filter((r) => !r.parent_id && r.applicability !== "unavailable")
            .map((r) => ({ ...r, applicability: kwargs.applicability }));
    });
    onRpc("account.analytic.account", "web_search_read", function ({ model, kwargs }) {
        const records = this.env[model]._filter(kwargs.domain);
        return {
            length: records.length,
            records,
        };
    });
    await mountView({
        type: "list",
        resModel: "aml",
        arch: `
                <list multi_edit="1">
                    <field name="label"/>
                    <field name="analytic_distribution" widget="analytic_distribution" options="{'force_applicability': 'optional'}"/>
                    <field name="amount"/>
                </list>`,
    });
    expect(".badge").toHaveCount(2);
    await contains(".badge:eq(0) .o_tag_badge_text").click();
    expect(".analytic_distribution_popup").toHaveCount(0);

    // select 2 rows
    await contains(".o_data_row:eq(0) .o_list_record_selector input").check();
    await contains(".o_data_row:eq(1) .o_list_record_selector input").check();
    await contains(".o_data_row:eq(0) .badge:eq(0)").click();
    await animationFrame();
    expect(".analytic_distribution_popup").toHaveCount(1);
    expect(".analytic_distribution_popup:not(:has(.text-success))").toHaveCount(1);

    // add a line
    await contains(".analytic_distribution_popup .o_field_x2many_list_row_add").click();
    await contains(".analytic_distribution_popup tr[name='line_2'] #x_plan5_id").click();
    await contains(".analytic_distribution_popup .ui-menu-item:contains(search more)").click();

    expect(".modal-dialog .o_list_renderer").toHaveCount(1);

    await contains(".modal-dialog .modal-title").click();
    await contains(".modal-dialog .o_data_row:nth-of-type(4) .o_data_cell:first-of-type").click();
    expect(".modal-dialog .o_list_renderer").toHaveCount(0);

    await contains(".fa-close").click();
    await contains(".modal-dialog .btn-primary").click();
    await animationFrame();
    expect(".o_data_row .badge").toHaveCount(4);
    expect("tr:nth-of-type(2) .badge:nth-of-type(2) .o_tag_badge_text").toHaveText(
        "30.3% Belgium | 69.7% Berlin"
    );
});

test.tags("desktop");
test("Rounding, value suggestions, keyboard only", async () => {
    onRpc("account.analytic.plan", "get_relevant_plans", function ({ model }) {
        return this.env[model].filter(
            (r) => !r.parent_id && r.applicability !== "unavailable" && r.all_account_count
        );
    });
    await mountView({
        type: "form",
        resModel: "move",
        resId: 2,
        arch: `
                <form>
                    <sheet>
                        <field name="line_ids">
                            <list editable="bottom">
                                <field name="label"/>
                                <field name="analytic_distribution" widget="analytic_distribution"/>
                                <field name="amount"/>
                            </list>
                        </field>
                    </sheet>
                </form>`,
    });
    await contains(".o_data_row:nth-of-type(1) .o_list_char").click();
    await press("Tab");
    await animationFrame();
    expect(".analytic_distribution_popup").toHaveCount(1);

    // department
    await press("Tab");
    await press("ArrowDown");
    await animationFrame();
    await press("Enter"); // choose the RD account
    await animationFrame();
    await press("Tab"); // tab to country
    await press("Tab"); // tab to percentage
    await edit("99.9", { confirm: "tab" });

    // internal
    await animationFrame();
    await press("ArrowDown");
    await animationFrame();
    await press("Enter"); // choose the Time off account
    await animationFrame();
    await press("Tab"); // tab to departments
    await press("Tab"); // tab to country
    await press("Tab"); // tab to percentage
    await edit("99.99", { confirm: "tab" });

    // country
    await animationFrame();
    await press("Tab"); // tab to departments
    await press("Tab"); // tab to country
    await press("ArrowDown");
    await animationFrame();
    await press("Enter"); // choose the Belgium account
    await animationFrame();
    await press("Tab"); // tab to percentage
    await edit("99.999", { confirm: "tab" });
    await animationFrame();

    // tags
    expect(".badge:contains(99.9% RD)").toHaveCount(1);
    expect(".badge:contains(99.99% Time Off)").toHaveCount(1);
    expect(".badge:contains(100% Belgium)").toHaveCount(1);

    // fill department
    await press("Tab"); // tab to departments
    await press("ArrowDown");
    await animationFrame();
    await press("ArrowDown");
    await animationFrame();
    await press("Enter"); // choose the HR account
    await animationFrame();
    await press("Tab");
    await press("Tab");
    expect(getActiveElement()).toHaveValue(0.1);
    await edit("0.0996", { confirm: "tab" });
    await animationFrame();
    expect(".badge:contains('99.9% RD | 0.1% HR')").toHaveCount(1);
    expect(".text-success:contains('100%')").toHaveCount(1);

    // fill country
    await press("Tab"); // tab to departments
    await press("Tab"); // tab to country
    await press("ArrowDown");
    await animationFrame();
    await press("Enter"); // choose Belgium again
    await animationFrame();
    await press("Tab"); // tab to percentage
    await animationFrame();
    expect(getActiveElement()).toHaveValue(0.001);
    await edit("0.0006", { confirm: "tab" });
    await animationFrame();
    expect(".badge:contains('Belgium'):not(:contains('%'))").toHaveCount(1);

    // fill internal
    const autocomplete = getActiveElement().parentNode;
    // choose Operating Costs
    while (
        autocomplete.querySelector("a[aria-selected='true']")?.textContent !== "Operating Costs"
    ) {
        await press("ArrowDown");
        await animationFrame();
    }
    await press("Enter"); // validate
    await animationFrame();
    await press("Escape"); // close the popup
    await animationFrame();
    expect(".badge:contains('99.99% Time Off | 0.01% Operating Costs')").toHaveCount(1);
});
