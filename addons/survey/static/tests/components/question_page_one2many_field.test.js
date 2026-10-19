import { expect, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fields,
    makeServerError,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { animationFrame, press, queryAll, queryOne } from "@odoo/hoot-dom";

class Survey extends models.Model {
    question_and_page_ids = fields.One2many({ relation: "survey_question" });
    favorite_color = fields.Char({ string: "Favorite color" });

    _records = [
        {
            id: 1,
            question_and_page_ids: [1, 2],
            favorite_color: "",
        },
    ];
}

class SurveyQuestion extends models.Model {
    _name = "survey_question";

    is_page = fields.Boolean();
    title = fields.Char();
    random_questions_count = fields.Integer({ string: "Question Count" });

    _records = [
        {
            id: 1,
            is_page: true,
            title: "firstSectionTitle",
            random_questions_count: 4,
        },
        {
            id: 2,
            is_page: false,
            title: "recordTitle",
            random_questions_count: 5,
        },
    ];
    _views = {
        form: /* xml */ `
            <form>
                <field name="title" />
            </form>
        `,
    };
}

defineModels([Survey, SurveyQuestion]);
defineMailModels();

test("basic rendering", async () => {
    await mountView({
        type: "form",
        resModel: "survey",
        resId: 1,
        arch: `
                <form>
                    <field name="question_and_page_ids" widget="question_page_one2many">
                        <list>
                            <field name="is_page" invisible="1" />
                            <field name="title" />
                            <field name="random_questions_count" />
                        </list>
                    </field>
                </form>
            `,
    });
    expect(".o_field_x2many .o_list_renderer table.o_section_list_view").toHaveCount(1);
    expect(".o_data_row").toHaveCount(2);
    const rows = queryAll(".o_data_row");
    expect(rows[0]).toHaveClass("o_is_section fw-bold");
    expect(rows[0]).toHaveText("firstSectionTitle 4");
    expect(rows[1]).toHaveText("recordTitle 5");
    expect(queryOne("td[name=title]", { root: rows[0] })).toHaveAttribute("colspan", "1");
    expect(queryOne("td[name=title]", { root: rows[1] })).not.toHaveAttribute("colspan");
});

test("click on section behaves as usual in readonly mode", async () => {
    await mountView({
        type: "form",
        resModel: "survey",
        resId: 1,
        arch: `
                <form>
                    <field name="question_and_page_ids" widget="question_page_one2many">
                        <list>
                            <field name="is_page" invisible="1" />
                            <field name="title" />
                            <field name="random_questions_count" />
                        </list>
                    </field>
                </form>
            `,
        readonly: true,
    });

    await contains(".o_data_cell").click();
    expect(".o_selected_row").toHaveCount(0);
    expect(".modal .o_form_view").toHaveCount(1);
});

test("click on section edit the section in place", async () => {
    await mountView({
        type: "form",
        resModel: "survey",
        resId: 1,
        arch: `
                <form>
                    <field name="question_and_page_ids" widget="question_page_one2many">
                        <list>
                            <field name="is_page" invisible="1" />
                            <field name="title" />
                            <field name="random_questions_count" />
                        </list>
                    </field>
                </form>`,
    });
    await contains(".o_data_cell").click();
    expect(".o_is_section").toHaveClass("o_selected_row");
    expect(".modal .o_form_view").toHaveCount(0);
});

test("click on real line saves form and opens a dialog", async () => {
    await mountView({
        type: "form",
        resModel: "survey",
        resId: 1,
        arch: `
                <form>
                    <field name="favorite_color"/>
                    <field name="question_and_page_ids" widget="question_page_one2many">
                        <list>
                            <field name="is_page" invisible="1" />
                            <field name="title" />
                            <field name="random_questions_count" />
                        </list>
                    </field>
                </form>
            `,
    });
    onRpc("survey", "web_save", () => {
        expect.step("save parent form");
    });
    await contains("[name='favorite_color'] input").edit("Yellow");
    await contains(".o_data_row:nth-child(2) .o_data_cell").click();
    // Edit content to trigger the expected actual save at row opening
    expect.verifySteps(["save parent form"]);
    expect(".o_selected_row").toHaveCount(1);
    expect(".modal .o_form_view").toHaveCount(1);
});

test("A validation error from saving parent form notifies and prevents dialog from closing", async () => {
    expect.errors(1);

    await mountView({
        type: "form",
        resModel: "survey",
        resId: 1,
        arch: `
                <form>
                    <field name="question_and_page_ids" widget="question_page_one2many">
                        <list>
                            <field name="is_page" invisible="1" />
                            <field name="title" />
                            <field name="random_questions_count" />
                        </list>
                    </field>
                </form>
            `,
    });
    const error = makeServerError({
        description: "This isn't right!",
        type: "ValidationError",
    });
    onRpc("survey", "web_save", () => {
        expect.step("save parent form");
        throw error;
    });
    await contains(".o_data_row:nth-child(2) .o_data_cell").click();
    await contains(".o_dialog:not(.o_inactive_modal) .modal-body [name='title'] input").edit(
        "Invalid RecordTitle"
    );
    await contains(".o_dialog:not(.o_inactive_modal) .o_form_button_save").click();
    expect.verifySteps(["save parent form"]);
    expect.verifyErrors(["This isn't right!"]);
    await animationFrame();
    expect(".o_notification").toHaveCount(1);
    expect(".modal .o_form_view").toHaveCount(1);
    expect(".modal-dialog .o_form_button_save").toHaveCount(1);
    expect(".modal-dialog .o_form_button_save[disabled='1']").toHaveCount(0);
});

test.tags("desktop");
test("can create section inline", async () => {
    await mountView({
        type: "form",
        resModel: "survey",
        resId: 1,
        arch: `
                <form>
                    <field name="question_and_page_ids" widget="question_page_one2many">
                        <list>
                            <field name="is_page" invisible="1" />
                            <field name="title" />
                            <field name="random_questions_count" />
                            <control>
                                <create string="add line" />
                                <create string="add section" context="{'default_is_page': true}" />
                            </control>
                        </list>
                    </field>
                </form>
            `,
    });

    expect(".o_selected_row").toHaveCount(0);

    await contains(".o_field_x2many_list_row_add button:eq(1)").click();
    expect(".o_selected_row.o_is_section").toHaveCount(1);
    expect(".modal .o_form_view").toHaveCount(0);
});

test("creates real record in form dialog", async () => {
    await mountView({
        type: "form",
        resModel: "survey",
        resId: 1,
        arch: `
                <form>
                    <field name="question_and_page_ids" widget="question_page_one2many">
                        <list>
                            <field name="is_page" invisible="1" />
                            <field name="title" />
                            <field name="random_questions_count" />
                            <control>
                                <create string="add line" />
                                <create string="add section" context="{'default_is_page': true}" />
                            </control>
                        </list>
                    </field>
                </form>
            `,
    });

    await contains(".o_field_x2many_list_row_add button").click();
    expect(".o_selected_row").toHaveCount(0);
    expect(".modal .o_form_view").toHaveCount(1);
});

test("press enter with focus in a edited section pass the section in readonly mode", async () => {
    await mountView({
        type: "form",
        resModel: "survey",
        resId: 1,
        arch: `
                <form>
                    <field name="question_and_page_ids" widget="question_page_one2many">
                        <list>
                            <field name="is_page" invisible="1" />
                            <field name="title" />
                            <field name="random_questions_count" />
                        </list>
                    </field>
                </form>
            `,
    });
    await contains(".o_data_row .o_data_cell").click();
    expect(".o_selected_row.o_is_section").toHaveCount(1);

    await contains("[name='title'] input").edit("a");

    press("Enter");
    expect(".o_selected_row.o_is_section").toHaveCount(0);
    expect(".o_is_section [name=title]").toHaveText("a");
});
