import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { animationFrame, queryAll, queryOne } from "@odoo/hoot-dom";
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
            triggering_question_ids: null,
            triggering_answer_ids: null,
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
        "form,false": `
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

    expect(".o_field_x2many .o_list_renderer table.o_list_table").toHaveCount(1);
    expect(".o_data_row").toHaveCount(2);
    let rows = queryAll(".o_data_row");

    expect(rows[0]).toHaveText("Question 1");
    expect(
        ".o_data_row:eq(0) td.o_data_cell div.o_widget_survey_question_trigger button"
    ).toHaveCount(0);

    expect(rows[1]).toHaveText("Question 2");
    let q2TriggerDiv = queryOne("td.o_data_cell div.o_widget_survey_question_trigger", {
        root: rows[1],
    });
    expect(queryAll("button", { root: q2TriggerDiv })).toHaveCount(1);
    // Question 2 is correctly placed after Question 1
    let triggerIcon = queryOne("button i", { root: q2TriggerDiv });
    expect(triggerIcon).not.toHaveClass("text-warning");
    expect(triggerIcon).toHaveAttribute("data-tooltip", 'Displayed if "Question 1: Answer 1".', {
        message: "Trigger tooltip should be 'Displayed if \"Question 1: Answer 1\".'.",
    });

    // drag and drop Question 2 (triggered) before Question 1 (trigger)
    await contains("tbody tr:nth-child(2) .o_handle_cell").dragAndDrop("tbody tr:nth-child(1)");
    await animationFrame();
    rows = queryAll(".o_data_row");

    expect(rows[0]).toHaveText("Question 2");
    q2TriggerDiv = queryOne("td.o_data_cell div.o_widget_survey_question_trigger", {
        root: rows[0],
    });
    expect(queryAll("button", { root: q2TriggerDiv })).toHaveCount(1);
    triggerIcon = queryOne("button i", { root: q2TriggerDiv });
    expect(triggerIcon).toHaveClass("text-warning");
    expect(triggerIcon).toHaveAttribute(
        "data-tooltip",
        '⚠ Triggers based on the following questions will not work because they are positioned after this question:\n"Question 1".',
        { message: "Trigger tooltip should have been changed to misplacement error message." }
    );

    // drag and drop Question 1 (trigger) back before Question 2 (triggered)
    await contains("tbody tr:nth-child(2) .o_handle_cell").dragAndDrop("tbody tr:nth-child(1)");
    await animationFrame();

    rows = queryAll(".o_data_row");

    expect(rows[1]).toHaveText("Question 2");
    expect(
        queryOne("td.o_data_cell div.o_widget_survey_question_trigger button i", { root: rows[1] })
    ).not.toHaveClass("text-warning");
    expect(triggerIcon).toHaveAttribute("data-tooltip", 'Displayed if "Question 1: Answer 1".', {
        message: "Trigger tooltip should be back to 'Displayed if \"Question 1: Answer 1\".'.",
    });
});
