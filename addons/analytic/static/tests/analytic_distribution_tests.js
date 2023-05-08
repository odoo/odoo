/** @odoo-module **/

import {
    click,
    editInput,
    getFixture,
    nextTick,
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
                        {id: 1, color: 1, root_plan_id: 2, plan_id: 2, name: "RD" },
                        {id: 2, color: 1, root_plan_id: 2, plan_id: 2, name: "HR" },
                        {id: 3, color: 1, root_plan_id: 2, plan_id: 2, name: "FI" },
                        {id: 4, color: 2, root_plan_id: 1, plan_id: 1, name: "Time Off" },
                        {id: 5, color: 2, root_plan_id: 1, plan_id: 1, name: "Operating Costs" },
                        {id: 6, color: 6, root_plan_id: 4, plan_id: 4, name: "Incognito" },
                        {id: 7, color: 5, root_plan_id: 5, plan_id: 5, name: "Belgium" },
                        {id: 8, color: 6, root_plan_id: 5, plan_id: 6, name: "Brussels" },
                        {id: 9, color: 6, root_plan_id: 5, plan_id: 6, name: "Namur" },
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
                        { id: 1, name: 'Internal', applicability: "optional", all_account_count: 2 },
                        { id: 2, name: 'Departments', applicability: "mandatory", all_account_count: 3 },
                        { id: 3, name: 'Projects', applicability: "optional" },
                        { id: 4, name: 'Hidden', applicability: "unavailable", all_account_count: 1 },
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
                    },
                    records: [
                        { id: 1, label: "Developer Time", amount: 100.00, analytic_distribution: {"1": 30.3, "3": 69.7}},
                        { id: 2, label: "Coke", amount: 100.00, analytic_distribution: '{}'},
                        { id: 3, label: "Sprite", amount: 100.00, analytic_distribution: '{}'},
                        { id: 4, label: "", amount: 100.00, analytic_distribution: '{}'},
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
                "decimal.precision": {
                    fields: {
                        name: { string: "Name", type: "char" },
                        digits: { string: "Digits", type: "int" },
                    },
                    records: [
                        { id: 1, name: "Percentage Analytic", digits: 2}
                    ]
                }
            },
        };

        setupViewRegistries();
    });

    QUnit.module("AnalyticDistribution");

    QUnit.test("field in form view basic features", async function (assert) {
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
            mockRPC(route, { kwargs, method, model }) {
                if (method === "get_relevant_plans" && model === "account.analytic.plan") {
                    return Promise.resolve(
                        serverData.models['plan'].records.filter((r) => !r.parent_id && r.applicability !== "unavailable")
                    );
                }
            },
        });

        assert.containsOnce(target, ".o_field_analytic_distribution", "widget should be visible");
        assert.containsN(target, ".badge", 2, "should contain 2 tags");
        assert.strictEqual(target.querySelector(".badge .o_tag_badge_text").textContent, "RD 30.3%",
            "should have rendered 'RD 30.3%'"
        );
        assert.strictEqual(target.querySelectorAll(".badge .o_tag_badge_text")[1].textContent, "FI 69.7%",
            "should have rendered 'FI 69.7%'"
        );

        assert.containsN(target, ".o_delete", 2, "tags should contain a delete button");

        let badge1 = target.querySelector('.badge');
        await click(badge1, ".o_tag_badge_text");
        assert.containsN(target, ".analytic_distribution_popup", 1, "popup should be visible");

        let popup = target.querySelector('.analytic_distribution_popup');
        let planTable = popup.querySelectorAll('table')[0];
        assert.strictEqual(planTable.id, "plan_2", "mandatory plan appears first");
        assert.containsN(planTable, 'tr', 4,
            "first plan contains 4 rows including: title, 2 tags, add a line"
        );
        assert.strictEqual(document.activeElement, planTable.querySelector('input'),
            "focus is on the first analytic account"
        );

        triggerHotkey("Tab");
        const input = document.activeElement;
        await editInput(input, null, "19");

        assert.containsOnce(planTable, '.o_analytic_status_editing', "Mandatory plan has incomplete status");

        let incompleteInputName = planTable.querySelector('tr.incomplete .o_analytic_account_name input');
        assert.strictEqual(document.activeElement, incompleteInputName,
            "focus is on the first incomplete tag"
        );

        triggerHotkey("Escape");
        await nextTick();
        assert.containsNone(target, '.analytic_distribution_popup', "The popup should be closed");

        triggerHotkey("arrowdown"); //opens the popup again
        await nextTick();

        popup = target.querySelector('.analytic_distribution_popup');
        planTable = popup.querySelectorAll('table')[0];
        incompleteInputName = planTable.querySelector('tr.incomplete .o_analytic_account_name input');
        assert.strictEqual(document.activeElement, incompleteInputName,
            "focus returns to the first incomplete tag"
        );

        triggerHotkey("arrowdown");
        await nextTick();

        triggerHotkey("Tab");
        await nextTick();

        assert.strictEqual(document.activeElement.value, "11.3%", "remainder percentage is prepopulated");

        await click(target, '.fa-close');
        assert.containsNone(target, '.analytic_distribution_popup', "The popup should be closed");
        assert.containsNone(target, '.o_field_invalid', "Distribution is valid");
        assert.containsN(target, ".badge", 3, "should contain 3 tags");
    });
});
