/** @odoo-module **/

import {
    click,
    getFixture,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("Analytic", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                analytic_account: {
                    fields: {
                        plan_id: { string: "Plan", type: "many2one", relation: "plan" },
                        root_plan_id: { string: "Root Plan", type: "many2one", relation: "plan" },
                        color: { string: "Color", type: "integer" },
                    },
                    records: [
                        {id: 1, color: 1, root_plan_id: 1, plan_id: 1, name: "RD" },
                        {id: 2, color: 1, root_plan_id: 1, plan_id: 1, name: "HR" },
                        {id: 3, color: 1, root_plan_id: 1, plan_id: 1, name: "FI" },
                        {id: 4, color: 2, root_plan_id: 2, plan_id: 2, name: "Time Off" },
                        {id: 5, color: 2, root_plan_id: 2, plan_id: 2, name: "Operating Costs" },
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
                    },
                    records: [
                        { id: 1, name: 'Departments', applicability: "mandatory" },
                        { id: 2, name: 'Internal', applicability: "optional", all_account_count: 2 },
                        { id: 3, name: 'Projects', applicability: "optional" },
                        { id: 4, name: 'Hidden', applicability: "unavailable" },
                        { id: 5, name: "Country", applicability: "optional"},
                        { id: 6, name: "City", applicability: "optional"},
                    ],
                },
                aml: {
                    fields: {
                        label: { string: "Label", type: "char" },
                        amount: { string: "Amount", type: "float" },
                        analytic_distribution: { string: "Analytic", type: "char" },
                        move_id: { string: "Account Move", type: "many2one", relation: "move" },
                    },
                    records: [
                        { id: 1, label: "Developer Time", amount: 100.00, analytic_distribution: {"1": 30.3, "3": 69.7}},
                        { id: 2, label: "Coke", amount: 100.00, analytic_distribution: '{}'},
                        { id: 3, label: "Sprite", amount: 100.00, analytic_distribution: '{}'},
                        { id: 4, label: "", amount: 100.00, analytic_distribution: '{}'},
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
                }
            },
        };

        setupViewRegistries();
    });

    QUnit.module("AnalyticDistribution");

    QUnit.test("field in form view should open and close", async function (assert) {
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
                if (method === "search_read" && model === "account.analytic.plan") {
                    return Promise.resolve(serverData.models['plan'].records);
                } else if (method === "search_read" && model === "account.analytic.account") {
                    if (kwargs.domain[0][0] == "id" && kwargs.domain[0][1] == "in") {
                        const required_ids = kwargs.domain[0][2].map((id) => parseInt(id));
                        const analytic_accs = serverData.models['analytic_account'].records.filter((r) => required_ids.includes(r.id));
                        const accs_with_plan = analytic_accs.map(
                            (r) => (
                                {
                                    ...r,
                                    root_plan_id: Object.values(serverData.models['plan'].records.find((p) => p.id === r.root_plan_id))
                                }
                            ));
                        return Promise.resolve(accs_with_plan);
                    }
                    return Promise.resolve(serverData.models['analytic_account'].records);
                } else if (method === "get_relevant_plans" && model === "account.analytic.plan") {
                    return Promise.resolve(serverData.models['plan'].records);
                }
            },
        });

        assert.containsOnce(target, ".analytic_distribution", "widget should be visible");
        assert.containsN(target, ".badge", 2, "should contain 2 tags");
        assert.strictEqual(
            target.querySelector(".badge .o_tag_badge_text").textContent,
            "RD 30.3%",
            "should have rendered 'RD 30.3%'"
        );
        assert.strictEqual(
            target.querySelectorAll(".badge .o_tag_badge_text")[1].textContent,
            "FI 69.7%",
            "should have rendered 'FI 69.7%'"
        );

        assert.containsN(
            target,
            ".o_delete",
            2,
            "tags should contain a delete button"
        );

        const badge1 = target.querySelector('.badge');
        await click(badge1, ".o_tag_badge_text");
        assert.containsN(
            target,
            ".analytic_distribution_popup",
            1,
            "popup should be visible"
        );

        await click(target, '.fa-close');
        assert.containsNone(target, '.analytic_distribution_popup', "The popup should be closed");

    });
});
