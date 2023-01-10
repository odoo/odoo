/** @odoo-module */

import { dragAndDrop, getFixture, nextTick } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

QUnit.module("SurveyQuestionTriggerWidget", (hooks) => {
    let serverData;
    let target;

    hooks.beforeEach(() => {
        target = getFixture();

        serverData = {
            models: {
                survey: {
                    fields: {
                        question_and_page_ids: { type: "one2many", relation: "survey_question" },
                    },
                    records: [
                        {
                            id: 1,
                            question_and_page_ids: [1, 2],
                        },
                    ],
                },
                survey_question: {
                    fields: {
                        sequence: { type: "number" },
                        name: { type: "char", string: "name", },
                        triggering_question_id: {
                            type: "many2one",
                            string: "Triggering question",
                            relation: "survey_question",
                            required: false,
                            searchable: true,
                        },
                        triggering_answer_id: {
                            type: "many2one",
                            string: "Triggering answer",
                            relation: "survey_question_answer",
                            required: false,
                            searchable: true,
                        },
                    },
                    records: [
                        {
                            id: 1,
                            sequence: 1,
                            name: "Question 1",
                            triggering_question_id: null,
                            triggering_answer_id: null,
                        }, {
                            id: 2,
                            sequence: 2,
                            name: "Question 2",
                            triggering_question_id: 1,
                            triggering_answer_id: 1,
                        },
                    ],
                },
                survey_question_answer: {
                    fields: {
                        name: {type: "char", string: "name"},
                    },
                    records: [
                        {
                            id: 1,
                            name: "Answer 1"
                        },
                    ]
                }
            },
            views: {
                "survey_question,false,form": `
                    <form>
                        <group>
                            <field name="name"/>
                            <field name="triggering_answer_id" invisible="1"/>
                            <field name="triggering_question_id" invisible="1"/> 
                            <widget name="survey_question_trigger" nolabel="1"/>
                        </group>
                    </form>
                `,
            },
        };

        setupViewRegistries();
    });

    QUnit.test("dynamic rendering of surveyQuestionTriggerError rows", async (assert) => {
        await makeView({
            type: "form",
            resModel: "survey",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="question_and_page_ids">  
                        <tree>
                            <field name="sequence" widget="handle"/>
                            <field name="name"/>
                            <field name="triggering_answer_id" invisible="1"/>
                            <field name="triggering_question_id" invisible="1"/> 
                            <widget name="survey_question_trigger" options="{'isSurveyForm': True}"/>
                        </tree>
                    </field>
                </form>
            `,
        });

        assert.containsOnce(target, ".o_field_x2many .o_list_renderer table.o_list_table");
        assert.containsN(target, ".o_data_row", 2);
        let rows = target.querySelectorAll(".o_data_row");

        assert.strictEqual(rows[0].textContent, "Question 1");
        let q1TriggerDiv = rows[0].querySelector("td.o_data_cell div.o_widget_survey_question_trigger");
        assert.containsNone(q1TriggerDiv, "button");

        assert.strictEqual(rows[1].textContent, "Question 2");
        let q2TriggerDiv = rows[1].querySelector("td.o_data_cell div.o_widget_survey_question_trigger");
        assert.containsOnce(q2TriggerDiv, "button");
        // Question 2 is correctly placed after Question 1
        let triggerIcon = q2TriggerDiv.querySelector("button i");
        assert.doesNotHaveClass(triggerIcon, "text-warning");
        assert.hasAttrValue(triggerIcon, 'data-tooltip', 'Displayed if "Question 1: Answer 1"',
                       'Trigger tooltip should be \'Displayed if "Question 1: Answer 1"\'.');

        // drag and drop Question 2 (triggered) before Question 1 (trigger)
        await dragAndDrop("tbody tr:nth-child(2) .o_handle_cell", "tbody tr:nth-child(1)");
        await nextTick();
        rows = target.querySelectorAll(".o_data_row");

        assert.strictEqual(rows[0].textContent, "Question 2");
        q2TriggerDiv = rows[0].querySelector("td.o_data_cell div.o_widget_survey_question_trigger");
        assert.containsOnce(q2TriggerDiv, "button");
        triggerIcon = q2TriggerDiv.querySelector("button i");
        assert.hasClass(triggerIcon, "text-warning");
        assert.strictEqual(
            triggerIcon.getAttribute('data-tooltip'),
            '⚠ This question is positioned before its trigger ("Question 1") and will be skipped.',
            'Trigger tooltip should have been changed to misplacement error message.'
        );

        // drag and drop Question 1 (trigger) back before Question 2 (triggered)
        await dragAndDrop("tbody tr:nth-child(2) .o_handle_cell", "tbody tr:nth-child(1)");
        await nextTick();

        rows = target.querySelectorAll(".o_data_row");

        assert.strictEqual(rows[1].textContent, "Question 2");
        assert.doesNotHaveClass(rows[1].querySelector("td.o_data_cell div.o_widget_survey_question_trigger button i"), "text-warning");
        assert.hasAttrValue(triggerIcon, 'data-tooltip', 'Displayed if "Question 1: Answer 1"',
                       'Trigger tooltip should be back to \'Displayed if "Question 1: Answer 1"\'.');
    });
});
