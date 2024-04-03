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
                    },
                    records: [
                        { id: 1, label: "Developer Time", amount: 100.00, analytic_distribution: {"1": 30.3, "3": 69.7}},
                        { id: 2, label: "Coke", amount: 100.00, analytic_distribution: {}},
                        { id: 3, label: "Sprite", amount: 100.00, analytic_distribution: {}},
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
            "should have rendered tag 'RD 30.3%'"
        );
        assert.strictEqual(target.querySelectorAll(".badge .o_tag_badge_text")[1].textContent, "FI 69.7%",
            "should have rendered tag 'FI 69.7%'"
        );

        assert.containsN(target, ".o_delete", 2, "tags should contain a delete button");

        let badge1 = target.querySelector('.badge');
        await click(badge1, ".o_tag_badge_text");
        assert.containsN(target, ".analytic_distribution_popup", 1, "popup should be visible");

        let popup = target.querySelector('.analytic_distribution_popup');
        let planTable = popup.querySelectorAll('table')[0];

        assert.strictEqual(planTable.id, "plan_2", "mandatory plan appears first");
        assert.containsN(planTable, 'tr', 4,
            "first plan contains 4 rows including: plan title, 2 tags, empty tag"
        );
        assert.strictEqual(document.activeElement, planTable.querySelector('input'),
            "focus is on the first analytic account"
        );

        triggerHotkey("Tab");
        const input = document.activeElement;
        await editInput(input, null, "19");

        assert.containsOnce(planTable, '.o_analytic_status_invalid', "Mandatory plan has invalid status");

        triggerHotkey("Escape");
        await nextTick();
        assert.containsNone(target, '.analytic_distribution_popup', "The popup should be closed");

        triggerHotkey("arrowdown"); //opens the popup again
        await nextTick();

        popup = target.querySelector('.analytic_distribution_popup');
        planTable = popup.querySelectorAll('table')[0];
        let incompleteInputName = planTable.querySelector('tr.incomplete .o_analytic_account_name input');
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
                    assert.equal(kwargs.applicability, "optional")
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
        assert.containsNone(popup, 'th span', "All plans are optional with no status indicator");

        let incompleteCountryTag = popup.querySelector("table#plan_5 .incomplete .o_analytic_account_name input");
        await click(incompleteCountryTag);
        await click(target.querySelector(".o_m2o_dropdown_option_search_more"));

        assert.containsN(target, ".modal-dialog .o_list_renderer", 1, "select create list dialog is visible");

        // select 2 analytic accounts
        let accountRows = [...target.querySelectorAll(".modal-dialog .o_data_row")];
        for (const row of accountRows.slice(0,2)) {
            await click(row.querySelector(".o_list_record_selector input"));
        }
        await click(target.querySelector(".o_select_button"));

        let percentageEls = [...popup.querySelectorAll("table#plan_5 .o_analytic_percentage input")];
        let expectedPercentages = ['100%', '0%', '0%'];
        for (const [i, el] of percentageEls.entries()) {
            assert.equal(el.value, expectedPercentages[i], `1: Percentage Element ${i} should be ${expectedPercentages[i]}`);
        }
        // modify the percentage of tag 1, tag 2 is filled
        await editInput(percentageEls[0], null, "50");
        expectedPercentages = ['50%', '50%', '0%'];
        for (const [i, el] of percentageEls.entries()) {
            assert.equal(el.value, expectedPercentages[i], `2: Percentage Element ${i} should be ${expectedPercentages[i]}`);
        }
        // modify the percentage of tag 1, last empty tag (tag 3) is filled
        await editInput(percentageEls[0], null, "40");
        expectedPercentages = ['40%', '50%', '10%'];
        for (const [i, el] of percentageEls.entries()) {
            assert.equal(el.value, expectedPercentages[i], `3: Percentage Element ${i} should be ${expectedPercentages[i]}`);
        }

        // replace the first analytic account with 4 accounts
        triggerHotkey("shift+Tab");
        await click(document.activeElement);
        await click(target.querySelector(".o_m2o_dropdown_option_search_more"));
        accountRows = [...target.querySelectorAll(".modal-dialog .o_data_row")];
        for (const row of accountRows.slice(0,4)) {
            await click(row.querySelector(".o_list_record_selector input"));
        }
        await click(target.querySelector(".o_select_button"));

        percentageEls = [...popup.querySelectorAll("table#plan_5 .o_analytic_percentage input")];
        expectedPercentages = ['40%', '50%', '10%', '0%', '0%', '0%'];
        for (const [i, el] of percentageEls.entries()) {
            assert.equal(el.value, expectedPercentages[i], `4: Percentage Element ${i} should be ${expectedPercentages[i]}`);
        }

        // modify percentage of the tag 1 (focused), balance goes to the first zero (tag 4)
        await editInput(document.activeElement, null, "10");
        expectedPercentages = ['10%', '50%', '10%', '30%', '0%', '0%'];
        for (const [i, el] of percentageEls.entries()) {
            assert.equal(el.value, expectedPercentages[i], `5: Percentage Element ${i} should be ${expectedPercentages[i]}`);
        }

        // modify percentage of tag 4, balance goes to the first zero (tag 5)
        await editInput(percentageEls[3], null, "20");
        expectedPercentages = ['10%', '50%', '10%', '20%', '10%', '0%'];
        for (const [i, el] of percentageEls.entries()) {
            assert.equal(el.value, expectedPercentages[i], `6: Percentage Element ${i} should be ${expectedPercentages[i]}`);
        }

        // change tag 4 to 0%, tag is removed and balance goes to last tag (tag 5)
        let accountEls = [...popup.querySelectorAll("table#plan_5 .o_analytic_account_name input")];
        await editInput(percentageEls[3], null, "0");
        percentageEls = [...popup.querySelectorAll("table#plan_5 .o_analytic_percentage input")];
        expectedPercentages = ['10%', '50%', '10%', '10%', '20%'];
        for (const [i, el] of percentageEls.entries()) {
            assert.equal(el.value, expectedPercentages[i], `7: Percentage Element ${i} should be ${expectedPercentages[i]}`);
        }
        assert.strictEqual(document.activeElement, accountEls[4], "Focus should be on the fifth tag (one was removed)");

        // delete tag 3, balance goes to last empty tag (tag 4)
        let trashIcons = [...document.querySelectorAll("table#plan_5 .fa-trash-o")];
        assert.equal(trashIcons.length, 4, "1 tag should not have a trash icon");
        await click(trashIcons[2]);
        percentageEls = [...popup.querySelectorAll("table#plan_5 .o_analytic_percentage input")];
        expectedPercentages = ['10%', '50%', '10%', '30%'];
        for (const [i, el] of percentageEls.entries()) {
            assert.equal(el.value, expectedPercentages[i], `7: Percentage Element ${i} should be ${expectedPercentages[i]}`);
        }
        assert.equal(popup.querySelector("table#plan_5 tr:last-of-type .o_analytic_account_name input").value, "",
            "Last tag's account is empty");

        // apply the changes to both move lines
        triggerHotkey("Escape");
        await nextTick();
        await click(target.querySelector(".modal-dialog .btn-primary"));
        assert.containsN(target, ".badge", 10, "should contain 2 rows of 5 tags each");

    });
});
