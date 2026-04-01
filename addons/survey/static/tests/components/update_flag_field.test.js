import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { animationFrame, manuallyDispatchProgrammaticEvent, queryOne } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Survey extends models.Model {
    question_and_page_ids = fields.One2many({ relation: "survey_question" });
    session_speed_rating = fields.Boolean({ string: "Speed Reward", onChange: () => {} });
    session_speed_rating_time_limit = fields.Integer({
        string: "Speed Reward Time (s)",
        onChange: () => {},
    });

    _records = [
        {
            id: 1,
            question_and_page_ids: [1],
            session_speed_rating: false,
            session_speed_rating_time_limit: 30,
        },
    ];
}

class SurveyQuestion extends models.Model {
    _name = "survey_question";

    title = fields.Char();
    is_time_customized = fields.Boolean({ string: "Is time customized" });
    is_time_limited = fields.Boolean({ string: "Is time limited" });
    survey_id = fields.Many2one({ relation: "survey", string: "Survey" });
    time_limit = fields.Integer({ string: "Time limit (s)" });

    _records = [
        {
            id: 1,
            is_time_customized: false,
            is_time_limited: false,
            survey_id: 1,
            time_limit: 30,
            title: "Question 1",
        },
    ];
}

defineModels([Survey, SurveyQuestion]);
defineMailModels();

test("Auto update of is_time_customized", async () => {
    await mountView({
        type: "form",
        resModel: "survey",
        resId: 1,
        arch: `
            <form>
                <group>
                    <field name="session_speed_rating"/>
                    <field name="session_speed_rating_time_limit"/>
                </group>
                <field name="question_and_page_ids" no-label="1" mode="list">
                    <list>
                        <field name="title"/>
                        <field name="is_time_limited"/>
                        <field name="time_limit"/>
                        <field name="is_time_customized"/>
                    </list>
                    <form>
                        <group>
                            <field name="is_time_customized"/>
                            <field name="is_time_limited" readonly="0"
                                widget="boolean_update_flag"
                                options="{'flagFieldName': 'is_time_customized'}"
                                context="{'referenceValue': parent.session_speed_rating}"/>
                            <field name="time_limit" readonly="0"
                                widget="integer_update_flag"
                                options="{'flagFieldName': 'is_time_customized'}"
                                context="{'referenceValue': parent.session_speed_rating_time_limit}"/>
                        </group>
                    </form>
                </field>
            </form>
        `,
    });
    onRpc("survey", "onchange", () => ({
        value: { question_and_page_ids: [[1, 1, { is_time_customized: false }]] },
    }));
    // Open question
    await contains("tr.o_data_row > td.o_list_char").click();
    expect("div[name='is_time_customized'] input").not.toBeChecked();
    // set question "is_time_limited" => true
    await contains("div[name='is_time_limited'] input").click();
    await animationFrame();
    expect("div[name='is_time_customized'] input").toBeChecked(); // widget-triggered update to `true` based on `is_time_limited`
    // save question
    await contains("div.modal-dialog button.o_form_button_save").click();
    await animationFrame();
    // set survey "session_speed_rating" => true
    await contains("div[name='session_speed_rating'] input").click();
    await animationFrame();
    // check that questions "is_time_limited" === true and "is_time_customized" === false after survey onchange
    expect("td.o_field_cell[name='is_time_limited'] input").toBeChecked();
    expect("td.o_field_cell[name='is_time_customized'] input").not.toBeChecked();
    // Open question again
    await contains("tr.o_data_row > td.o_list_char").click();
    await contains("div[name='time_limit'] input").edit(20);
    // TODO: JUM (events concurrency)
    await manuallyDispatchProgrammaticEvent(queryOne("div[name='time_limit'] input"), "change");
    await animationFrame();
    expect("div[name='is_time_customized'] input").toBeChecked(); // widget-triggered update to `true` based on `time_limit`
    await contains("div[name='time_limit'] input").edit(30);
    // TODO: JUM (events concurrency)
    await manuallyDispatchProgrammaticEvent(queryOne("div[name='time_limit'] input"), "change");
    await animationFrame();
    expect("div[name='is_time_customized'] input").not.toBeChecked(); // widget-triggered update to `false` based on `time_limit`
    // set question "is_time_limited" => false
    await contains("div[name='is_time_limited'] input").click();
    await animationFrame();
    expect("div[name='is_time_customized'] input").toBeChecked(); // widget-triggered update to `false` based on `is_time_limited`
});
