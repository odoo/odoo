import { click, editInput, getFixture, nextTick } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";


QUnit.module("UpdateFlagFields", (hooks) => {
    let serverData, target;

    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                survey_survey: {
                    fields: {
                        question_and_page_ids: { type: "one2many", relation: "survey_question", string: "Questions"},
                        session_speed_rating: { type: "boolean", string: "Speed Reward" },
                        session_speed_rating_time_limit: { type: "integer", string: "Speed Reward Time (s)" },
                    },
                    records: [
                        {
                            id: 1,
                            question_and_page_ids: [1],
                            session_speed_rating: false,
                            session_speed_rating_time_limit: 30,
                        },
                    ],
                    onchanges: {
                        session_speed_rating: () => {},
                        session_speed_rating_time_limit: () => {},
                    }
                },
                survey_question: {
                    fields: {
                        is_time_customized: { type: "boolean", string: "Is time customized" },
                        is_time_limited: { type: "boolean", string: "Is time limited"},
                        survey_id: { type : "many2one", relation: "survey_survey", string: "Survey" },
                        time_limit: { type: "integer", string: "Time limit (s)" },
                        title: { type: "char", string: "title", },
                    },
                    records: [
                        {
                            id: 1,
                            is_time_customized: false,
                            is_time_limited: false,
                            survey_id: 1,
                            time_limit: 30,
                            title: "Question 1",
                        },
                    ],
                },
            },
        };
        setupViewRegistries();
    });

    QUnit.test("Auto update of is_time_customized", async (assert) => {
        await makeView({
            type: "form",
            resModel: "survey_survey",
            mockRPC(route, args) {
                if (args.method === "onchange" && args.model === "survey_survey") {
                    return { value: { question_and_page_ids: [[1, 1, { "is_time_customized": false }]] } };
                }
            },
            resId: 1,
            serverData,
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
        const changeQuestionTimeLimit = async (value) => {
            await editInput(target, "div[name='time_limit'] input", value);
            await nextTick();
            await target.querySelector("div[name='time_limit'] input").dispatchEvent(new Event("change"));
            await nextTick();
        }
        const assertQuestionIsTimeCustomized = () => assert.containsOnce(target, "div[name='is_time_customized'] input:checked");
        const assertQuestionIsNotTimeCustomized = () => assert.containsNone(target, "div[name='is_time_customized'] input:checked");

        // Open question
        await click(target.querySelector("tr.o_data_row > td.o_list_char"));
        assertQuestionIsNotTimeCustomized();
        // set question "is_time_limited" => true
        await click(target.querySelector("div[name='is_time_limited'] input"));
        await nextTick();
        assertQuestionIsTimeCustomized(); // widget-triggered update to `true` based on `is_time_limited`
        // save question
        await click(target.querySelector("div.modal-dialog button.o_form_button_save"));
        await nextTick();
        // set survey "session_speed_rating" => true
        await click(target.querySelector("div[name='session_speed_rating'] input"));
        await nextTick();
        // check that questions "is_time_limited" === true and "is_time_customized" === false after survey onchange
        assert.containsOnce(target, "td.o_field_cell[name='is_time_limited'] input:checked");
        assert.containsNone(target, "td.o_field_cell[name='is_time_customized'] input:checked");
        // Open question again
        await click(target.querySelector("tr.o_data_row > td.o_list_char"));
        await changeQuestionTimeLimit(20);
        assertQuestionIsTimeCustomized();  // widget-triggered update to `true` based on `time_limit`
        await changeQuestionTimeLimit(30);
        assertQuestionIsNotTimeCustomized();  // widget-triggered update to `false` based on `time_limit`
        // set question "is_time_limited" => false
        await click(target.querySelector("div[name='is_time_limited'] input"));
        await nextTick();
        assertQuestionIsTimeCustomized();  // widget-triggered update to `false` based on `is_time_limited`
    });

});
