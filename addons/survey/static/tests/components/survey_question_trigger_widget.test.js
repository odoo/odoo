import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { contains, defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

class Survey extends models.Model {
    question_and_page_ids = fields.One2many({ relation: "survey_question" });

    _records = [
        {
            id: 1,
            question_and_page_ids: [1, 2],
        },
    ];
}

class SurveyQuestion extends models.Model {
    _name = "survey_question";

    title = fields.Char();
    sequence = fields.Integer();
    triggering_question_ids = fields.Many2many({
        string: "Triggering question",
        relation: "survey_question",
        required: false,
    });
    triggering_answer_ids = fields.Many2many({
        string: "Triggering answers",
        relation: "survey_question_answer",
        required: false,
    });

    _records = [
        {
            id: 1,
            sequence: 1,
            title: "Question 1",
        },
        {
            id: 2,
            sequence: 2,
            title: "Question 2",
            triggering_question_ids: [1],
            triggering_answer_ids: [1],
        },
    ];
    _views = {
        form: /* xml */ `
            <form>
                <group>
                    <field name="title"/>
                    <field name="triggering_question_ids" invisible="1"/>
                    <field name="triggering_answer_ids" invisible="1" widget="many2many_tags"/>
                </group>
            </form>
        `,
    };
}

class SurveyQuestionAnswer extends models.Model {
    _name = "survey_question_answer";

    name = fields.Char();

    _records = [
        {
            id: 1,
            name: "Question 1: Answer 1",
        },
    ];
}

defineModels([Survey, SurveyQuestion, SurveyQuestionAnswer]);
defineMailModels();

test("dynamic rendering of surveyQuestionTriggerError rows", async () => {
    await mountView({
        type: "form",
        resModel: "survey",
        resId: 1,
        arch: `
            <form>
                <field name="question_and_page_ids">
                    <list>
                        <field name="sequence" widget="handle"/>
                        <field name="title"/>
                        <field name="triggering_question_ids" invisible="1"/>
                        <field name="triggering_answer_ids" invisible="1" widget="many2many_tags"/> <!-- widget to fetch display_name -->
                        <widget name="survey_question_trigger"/>
                    </list>
                </field>
            </form>
        `,
    });

    const firstDataRow = ".o_data_row:eq(0)";
    const secondDataRow = ".o_data_row:eq(1)";
    const q1TriggerDiv = `${firstDataRow} td.o_data_cell div.o_widget_survey_question_trigger`;
    const q2TriggerDiv = `${secondDataRow} td.o_data_cell div.o_widget_survey_question_trigger`;

    expect(".o_field_x2many .o_list_renderer table.o_list_table").toHaveCount(1);
    expect(".o_data_row").toHaveCount(2);

    expect(firstDataRow).toHaveText("Question 1");
    expect(`${q1TriggerDiv} button`).toHaveCount(0);

    expect(secondDataRow).toHaveText("Question 2");
    expect(`${q2TriggerDiv} button`).toHaveCount(1);
    // Question 2 is correctly placed after Question 1
    expect(`${q2TriggerDiv} button i`).not.toHaveClass("text-warning");
    expect(`${q2TriggerDiv} button i`).toHaveAttribute(
        "data-tooltip",
        'Displayed if "Question 1: Answer 1".',
        { message: "Trigger tooltip should be 'Displayed if \"Question 1: Answer 1\".'." }
    );

    // drag and drop Question 2 (triggered) before Question 1 (trigger)
    await contains("tbody tr:nth-child(2) .o_handle_cell").dragAndDrop("tbody tr:nth-child(1)");
    await animationFrame();

    expect(firstDataRow).toHaveText("Question 2");
    expect(`${q1TriggerDiv} button`).toHaveCount(1);
    expect(`${q1TriggerDiv} button i`).toHaveClass("text-warning");
    expect(`${q1TriggerDiv} button i`).toHaveAttribute(
        "data-tooltip",
        '⚠ Triggers based on the following questions will not work because they are positioned after this question:\n"Question 1".',
        { message: "Trigger tooltip should have been changed to misplacement error message." }
    );

    // drag and drop Question 1 (trigger) back before Question 2 (triggered)
    await contains("tbody tr:nth-child(2) .o_handle_cell").dragAndDrop("tbody tr:nth-child(1)");
    await animationFrame();

    expect(".o_data_row:eq(1)").toHaveText("Question 2");
    expect(`${q2TriggerDiv} button i`).not.toHaveClass("text-warning");
    expect(`${q2TriggerDiv} button i`).toHaveAttribute(
        "data-tooltip",
        'Displayed if "Question 1: Answer 1".',
        { message: "Trigger tooltip should be back to 'Displayed if \"Question 1: Answer 1\".'." }
    );
});
