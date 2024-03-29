/** @odoo-module **/

import {
    addRow,
    click,
    editInput,
    getFixture,
    nextTick,
    selectDropdownItem,
    triggerEvent,
    triggerHotkey,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("Analytic", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                "account.analytic.account": {
                    fields: {
                        plan_id: { string: "Plan", type: "many2one", relation: "plan" },
                        root_plan_id: { string: "Root Plan", type: "many2one", relation: "plan" },
                        color: { string: "Color", type: "integer" },
                        code: { string: "Ref", type: "string"},
                        partner_id: { string: "Partner", type: "many2one", relation: "partner" },
                    },
                    records: [
                        {id:  1, color: 1, root_plan_id: 2, plan_id: 2, name: "RD" },
                        {id:  2, color: 1, root_plan_id: 2, plan_id: 2, name: "HR" },
                        {id:  3, color: 1, root_plan_id: 2, plan_id: 2, name: "FI" },
                        {id:  4, color: 2, root_plan_id: 1, plan_id: 1, name: "Time Off" },
                        {id:  5, color: 2, root_plan_id: 1, plan_id: 1, name: "Operating Costs" },
                        {id:  6, color: 6, root_plan_id: 4, plan_id: 4, name: "Incognito" },
                        {id:  7, color: 5, root_plan_id: 5, plan_id: 5, name: "Belgium" },
                        {id:  8, color: 6, root_plan_id: 5, plan_id: 6, name: "Brussels" },
                        {id:  9, color: 6, root_plan_id: 5, plan_id: 6, name: "Beirut" },
                        {id: 10, color: 6, root_plan_id: 5, plan_id: 6, name: "Berlin" },
                        {id: 11, color: 6, root_plan_id: 5, plan_id: 6, name: "Bruges" },
                        {id: 12, color: 6, root_plan_id: 5, plan_id: 6, name: "Birmingham" },
                        {id: 13, color: 6, root_plan_id: 5, plan_id: 6, name: "Bologna" },
                        {id: 14, color: 6, root_plan_id: 5, plan_id: 6, name: "Bratislava" },
                        {id: 15, color: 6, root_plan_id: 5, plan_id: 6, name: "Budapest" },
                        {id: 16, color: 6, root_plan_id: 5, plan_id: 6, name: "Namur" },
                    ],
                },
                plan: {
                    fields: {
                        applicability: {
                            string: "Applicability",
                            type: "selection",
                            selection: [
                                ["mandatory", "Mandatory"],
                                ["optional", "Options"],
                                ["unavailable", "Unavailable"],
                            ],
                        },
                        color: { string: "Color", type: "integer" },
                        all_account_count: { type: "integer" },
                        parent_id: { type: "many2one", relation: "plan" },
                    },
                    records: [
                        { id: 1, name: "Internal", applicability: "optional", all_account_count: 2 },
                        { id: 2, name: "Departments", applicability: "mandatory", all_account_count: 3 },
                        { id: 3, name: "Projects", applicability: "optional" },
                        { id: 4, name: "Hidden", applicability: "unavailable", all_account_count: 1 },
                        { id: 5, name: "Country", applicability: "optional", all_account_count: 3 },
                        { id: 6, name: "City", applicability: "optional", all_account_count: 2, parent_id: 5 },
                    ],
                },
                aml: {
                    fields: {
                        label: { string: "Label", type: "char" },
                        amount: { string: "Amount", type: "float" },
                        analytic_distribution: { string: "Analytic", type: "json" },
                        move_id: { string: "Account Move", type: "many2one", relation: "move" },
                        analytic_precision: { string: "Analytic Precision", type: "integer" },
                    },
                    records: [
                        { id: 1, label: "Developer Time", amount: 100.00, analytic_distribution: {"1, 7": 30.3, "3": 69.704}, analytic_precision: 3},
                        { id: 2, label: "Coke", amount: 100.00, analytic_distribution: {}},
                        { id: 3, label: "Sprite", amount: 100.00, analytic_distribution: {}, analytic_precision: 3},
                        { id: 4, label: "", amount: 100.00, analytic_distribution: {}},
                    ],
                },
                partner: {
                    fields: {
                        name: { string: "Name", type: "char" },
                    },
                    records: [
                        { id: 1, name: "Great Partner" },
                    ],
                },
                move: {
                    fields: {
                        line_ids: { string: "Move Lines", type: "one2many", relation: "aml", relation_field: "move_line_id" },
                    },
                    records: [
                        { id: 1, display_name: "INV0001", line_ids: [1, 2]},
                        { id: 2, display_name: "INV0002", line_ids: [3, 4]},
                    ],
                },
            },
            views: {
                "account.analytic.account,false,search": `<search/>`,
                "account.analytic.account,analytic.view_account_analytic_account_list_select,list": `
                    <tree>
                        <field name="name"/>
                    </tree>
                `,
            }
        };

        setupViewRegistries();
    });

    QUnit.module("AnalyticDistribution");

    QUnit.test("analytic field in form view basic features", async function (assert) {
        await makeView({
            type: "form",
            resModel: "aml",
            resId: 1,
            serverData,
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
            mockRPC(route, { method, model }) {
                if (method === "get_relevant_plans" && model === "account.analytic.plan") {
                    return Promise.resolve(
                        serverData.models['plan'].records.filter((r) => !r.parent_id && r.applicability !== "unavailable")
                    );
                }
            },
        });
        // tags
        assert.containsOnce(target, ".o_field_analytic_distribution", "widget should be visible");
        assert.containsN(target, ".badge", 2, "should contain 2 tags");
        assert.strictEqual(target.querySelector(".badge .o_tag_badge_text").textContent, "30.3% RD | 69.7% FI",
            "should have rendered tag '30.3% RD | 69.7% FI'"
        );
        assert.strictEqual(target.querySelectorAll(".badge .o_tag_badge_text")[1].textContent, "30.3% Belgium",
            "should have rendered tag '30.3% Belgium'"
        );

        // open popup
        let field = target.querySelector('.o_field_analytic_distribution');
        await click(field, ".o_input_dropdown");
        assert.containsN(target, ".analytic_distribution_popup", 1, "popup should be visible");
        
        let popup = target.querySelector('.analytic_distribution_popup');
        let planTable = popup.querySelectorAll('table')[0];

        // contents of popup
        assert.containsN(planTable, 'tr', 4,
        "table contains 4 rows including: header row, 2 lines, add a line"
        );

        assert.strictEqual(document.activeElement, planTable.querySelector('tr:first-of-type #x_plan1_id'),
            "focus is on the first analytic account input of the first row"
        );

        // change percentage
        await click(planTable, "tr:first-of-type .o_field_percentage input");
        let input = document.activeElement;
        await editInput(input, null, "19.7001");
        
        // mandatory plan is red
        assert.containsOnce(planTable, 'th:contains("Departments") .text-danger:contains("50%")', "Mandatory plan has invalid status");

        // close and open popup with keyboard
        triggerHotkey("Escape");
        await nextTick();
        assert.containsNone(target, '.analytic_distribution_popup', "The popup should be closed");

        triggerHotkey("arrowdown");
        await nextTick();

        // add a line
        popup = target.querySelector('.analytic_distribution_popup');
        planTable = popup.querySelectorAll('table')[0];
        await click(planTable, '.o_field_x2many_list_row_add a');
        const newRow = planTable.querySelector('tr:nth-of-type(3)');
        assert.equal(newRow.querySelector('.o_field_percentage input').value, 50);

        // choose an account for the mandatory plan using the keyboard
        await click(newRow, "#x_plan2_id");
        input = document.activeElement;
        await triggerEvent(input, null, "keydown", { key: "enter" });
        await triggerEvent(input, null, "keyup", { key: "enter" });
        triggerHotkey("arrowdown");
        await nextTick();

        triggerHotkey("Tab");
        await nextTick();

        // mandatory plan is green
        assert.containsOnce(planTable, 'th:contains("Departments") .text-success:contains("100%")', "Mandatory plan in complete");

        // tags
        await click(target, '.fa-close');
        assert.containsNone(target, '.analytic_distribution_popup', "The popup should be closed");
        assert.containsN(target, ".badge", 2, "should contain 2 tags");
        assert.strictEqual(target.querySelector(".badge .o_tag_badge_text").textContent, "30.3% RD | 50% HR | 19.7% FI",
            "should have rendered tag '30.3% RD | 50% HR | 19.7% FI'"
        );
    });

    QUnit.test("analytic field in multi_edit list view + search more", async function (assert) {
        await makeView({
            type: "list",
            resModel: "aml",
            serverData,
            arch: `
                <tree multi_edit="1">
                    <field name="label"/>
                    <field name="analytic_distribution" widget="analytic_distribution" options="{'force_applicability': 'optional'}"/>
                    <field name="amount"/>
                </tree>`,
            mockRPC(route, { kwargs, method, model }) {
                if (method === "get_relevant_plans" && model === "account.analytic.plan") {
                    assert.equal(kwargs.applicability, "optional");
                    return Promise.resolve(
                        serverData.models['plan'].records
                            .filter((r) => !r.parent_id && r.applicability !== "unavailable")
                            .map((r) => ({...r, applicability: "optional"}))
                    );
                }
            },
        });
        assert.containsN(target, ".badge", 2, "should contain 2 tags");
        let badge1 = target.querySelector('.badge');
        await click(badge1, ".o_tag_badge_text");
        assert.containsNone(target, '.analytic_distribution_popup', "The popup should not open in readonly mode");

        // select 2 rows
        const amlrows = target.querySelectorAll(".o_data_row");
        await click(amlrows[0].querySelector(".o_list_record_selector input"));
        await click(amlrows[1].querySelector(".o_list_record_selector input"));
        await click(badge1, ".o_tag_badge_text");
        await nextTick();
        assert.containsN(target, ".analytic_distribution_popup", 1, "popup should be visible");

        let popup = target.querySelector('.analytic_distribution_popup');
        assert.containsNone(popup, '.text-success', "All plans are optional");

        // add a line
        let planTable = popup.querySelectorAll('table')[0];
        await addRow(planTable)
        await selectDropdownItem(planTable.querySelector("tr[name='line_2']"), "x_plan5_id", "Search More...");
        assert.containsN(target, ".modal-dialog .o_list_renderer", 1, "select create list dialog is visible");
        
        await click(target, ".modal-dialog .modal-title");
        await click(target, ".modal-dialog .o_data_row:nth-of-type(4) .o_data_cell:first-of-type");
        assert.containsNone(target, ".modal-dialog .o_list_renderer", "select create list dialog is closed");

        await click(popup, ".fa-close");
        await click(target.querySelector(".modal-dialog .btn-primary"));
        await nextTick();
        assert.containsN(target, ".badge", 4, "should contain 2 rows of 2 tags each");
        assert.strictEqual(target.querySelector("tr:nth-of-type(2) .badge:nth-of-type(2) .o_tag_badge_text").textContent, "30.3% Belgium | 69.7% Berlin",
            "should have rendered tag '30.3% Belgium | 69.7% Berlin'"
        );
    });

    QUnit.test("Rounding, value suggestions, keyboard only", async (assert) => {
        await makeView({
            type: "form",
            resModel: "move",
            serverData,
            resId: 2,
            arch: `
                <form>
                    <sheet>
                        <field name="line_ids">
                            <tree editable="bottom">
                                <field name="label"/>
                                <field name="analytic_distribution" widget="analytic_distribution"/>
                                <field name="amount"/>
                            </tree>
                        </field>
                    </sheet>
                </form>`,
            mockRPC(route, { kwargs, method, model }) {
                if (method === "get_relevant_plans" && model === "account.analytic.plan") {
                    return Promise.resolve(
                        serverData.models['plan'].records.filter((r) => !r.parent_id && r.applicability !== "unavailable" && r.all_account_count)
                    );
                }
            },
        });
        await click(target, ".o_data_row:nth-of-type(1) .o_list_char");
        triggerHotkey("Tab");
        await nextTick();
        assert.containsN(target, ".analytic_distribution_popup", 1, "popup should be visible");

        // department
        triggerHotkey("Tab");
        triggerHotkey("arrowdown");
        await nextTick();
        triggerHotkey("Enter");  // choose the RD account
        await nextTick();
        triggerHotkey("Tab");  // tab to country
        triggerHotkey("Tab");  // tab to percentage
        await editInput(document.activeElement, false, "99.9");

        // internal
        triggerHotkey("Tab");  // new line
        await nextTick();
        triggerHotkey("arrowdown");
        await nextTick();
        triggerHotkey("Enter");  // choose the Time off account
        await nextTick();
        triggerHotkey("Tab");  // tab to departments
        triggerHotkey("Tab");  // tab to country
        triggerHotkey("Tab");  // tab to percentage
        await editInput(document.activeElement, false, "99.99");

        // country
        triggerHotkey("Tab");  // new line
        await nextTick();
        triggerHotkey("Tab");  // tab to departments
        triggerHotkey("Tab");  // tab to country
        triggerHotkey("arrowdown");
        await nextTick();
        triggerHotkey("Enter");  // choose the Belgium account
        await nextTick();
        triggerHotkey("Tab");  // tab to percentage
        await editInput(document.activeElement, false, "99.999");

        // tags
        assert.containsOnce(target, ".badge:contains('99.9% RD')", "contains RD tag");
        assert.containsOnce(target, ".badge:contains('99.99% Time Off')", "contains Time Off tag");
        assert.containsOnce(target, ".badge:contains('100% Belgium')", "contains Belgium tag always rounded to 2 decimals");

        // fill department
        triggerHotkey("Tab");  // new line
        await nextTick();
        triggerHotkey("Tab");  // tab to departments
        triggerHotkey("arrowdown");
        await nextTick();
        triggerHotkey("arrowdown");
        await nextTick();
        triggerHotkey("Enter");  // choose the HR account
        await nextTick();
        triggerHotkey("Tab");
        triggerHotkey("Tab");
        assert.equal(document.activeElement.value, 0.1, "Mandatory plan filled first with 0.1");
        await editInput(document.activeElement, false, "0.0996");
        assert.containsOnce(target, ".badge:contains('99.9% RD | 0.1% HR')", "contains RD|HR tag");
        assert.containsOnce(target, ".text-success:contains('100%')", "Department header");

        // fill country
        triggerHotkey("Tab");  // new line
        await nextTick();
        triggerHotkey("Tab");  // tab to departments
        triggerHotkey("Tab");  // tab to country
        triggerHotkey("arrowdown");
        await nextTick();
        triggerHotkey("Enter");  // choose Belgium again
        await nextTick();
        triggerHotkey("Tab");  // tab to percentage
        await nextTick();
        assert.equal(document.activeElement.value, 0.001, "Country plan filled next with 0.001");
        await editInput(document.activeElement, false, "0.0006");
        assert.containsOnce(target, ".badge:contains('Belgium'):not(:contains('%'))", "contains Belgium tag");

        // fill internal
        triggerHotkey("Tab");  // new line
        await nextTick();
        triggerHotkey("arrowdown");
        await nextTick();
        triggerHotkey("arrowdown");
        await nextTick();
        triggerHotkey("Enter");  // choose Operating Costs
        await nextTick();
        triggerHotkey("Escape");  // close the popup
        await nextTick();
        assert.containsOnce(target, ".badge:contains('99.99% Time Off | 0.01% Operating Costs')", "the Time Off | Operating Costs tag");
    });

    QUnit.test("Analytic Account Deleted after json is saved", (assert) => { assert.expect(0) });
    QUnit.test("No Plans Available", (assert) => { assert.expect(0) });
    QUnit.test("amount_field Column", (assert) => { assert.expect(0) });
    QUnit.test("save as model", (assert) => { assert.expect(0) });

});
