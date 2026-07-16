import { expect, test, waitFor } from "@odoo/hoot";
import { contains, defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";

class Partner extends models.Model {
    lines = fields.One2many({ relation: "lines_sections" });

    _records = [
        {
            id: 1,
            lines: [1, 2],
        },
    ];
}

class LinesSections extends models.Model {
    _name = "lines_sections";

    is_page = fields.Boolean();
    title = fields.Char();
    random_questions_count = fields.Integer({ string: "Question Count" });
    sequence = fields.Integer();
    question_type = fields.Char();

    _records = [
        {
            id: 1,
            sequence: 1,
            is_page: true,
            question_type: false,
            title: "firstSectionTitle",
            random_questions_count: 4,
        },
        {
            id: 2,
            sequence: 2,
            is_page: false,
            question_type: "simple_choice",
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

defineModels([Partner, LinesSections]);
defineMailModels();

const SELECTORS = {
    section: "tr.o_is_section > td.o_survey_description_page_cell",
    numberQuestions: "tr.o_is_section > [name='random_questions_count']",
};

test("normal list view", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
                <form>
                    <field name="lines" widget="question_page_one2many">
                        <list>
                            <field name="sequence" widget="handle"/>
                            <field name="title" widget="survey_description_page"/>
                            <field name="question_type" />
                            <field name="is_page" column_invisible="1"/>
                        </list>
                    </field>
                </form>
            `,
    });
    expect("td.o_survey_description_page_cell").toHaveCount(2); // Check if we have the two rows in the list

    expect("tr.o_is_section").toHaveCount(1); // Check if we have only one section row
    expect(SELECTORS.section).toHaveProperty("colSpan", 2);

    await contains(SELECTORS.section).click();
    expect(SELECTORS.section + " div.input-group").toHaveCount(1);
});

test("editing a question keeps the pager on the current page", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
                <form>
                    <field name="lines" widget="question_page_one2many">
                        <list limit="1">
                            <field name="sequence" widget="handle"/>
                            <field name="title" widget="survey_description_page"/>
                            <field name="question_type" />
                            <field name="is_page" column_invisible="1"/>
                        </list>
                    </field>
                </form>
            `,
    });
    await waitFor(".o_data_cell:contains(firstSectionTitle)"); // on first page
    expect(".o_data_cell:contains(recordTitle)").toHaveCount(0); // on second page
    await contains(".o_x2m_control_panel .o_pager_next").click();
    await contains(".o_data_cell:contains(recordTitle)").click();
    await contains(".modal [name='title'] input").edit("recordTitleModified");
    await contains(".modal .o_form_button_save").click();
    await waitFor(".o_data_cell:contains(recordTitleModified)");
    expect(".o_data_cell:contains(firstSectionTitle)").toHaveCount(0);
});

test("list view with random count", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
                <form>
                    <field name="lines" widget="question_page_one2many">
                        <list>
                            <field name="sequence" widget="handle"/>
                            <field name="title" widget="survey_description_page"/>
                            <field name="question_type" />
                            <field name="is_page" column_invisible="1"/>
                            <field name="random_questions_count"/>
                        </list>
                    </field>
                </form>
            `,
    });
    expect("td.o_survey_description_page_cell").toHaveCount(2); // Check if we have the two rows in the list

    expect("tr.o_is_section").toHaveCount(1); // Check if we have only one section row
    expect(SELECTORS.section).toHaveProperty("colSpan", 2);

    // We can edit the section title
    await contains(SELECTORS.section).click();
    expect(SELECTORS.section + " div.input-group").toHaveCount(1);

    // We can edit the number of random questions selected
    await contains(SELECTORS.numberQuestions).click();
    expect(SELECTORS.numberQuestions + " div").toHaveCount(1);
});

test("list view with random but with question_type at the left of the title", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
                <form>
                    <field name="lines" widget="question_page_one2many">
                        <list>
                            <field name="sequence" widget="handle"/>
                            <field name="question_type" />
                            <field name="title" widget="survey_description_page"/>
                            <field name="is_page" column_invisible="1"/>
                            <field name="random_questions_count"/>
                        </list>
                    </field>
                </form>
            `,
    });
    expect("td.o_survey_description_page_cell").toHaveCount(2); // Check if we have the two rows in the list

    expect("tr.o_is_section").toHaveCount(1); // Check if we have only one section row
    expect(SELECTORS.section).toHaveProperty("colSpan", 1);

    await contains(SELECTORS.section).click();
    expect(SELECTORS.section + " div.input-group").toHaveCount(1);

    await contains(SELECTORS.numberQuestions).click();
    expect(SELECTORS.numberQuestions + " div").toHaveCount(1);
});
test("list view with random and question_type at the beginning of row", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
                <form>
                    <field name="lines" widget="question_page_one2many">
                        <list>
                            <field name="sequence" widget="handle"/>
                            <field name="random_questions_count"/>
                            <field name="question_type" />
                            <field name="title" widget="survey_description_page"/>
                            <field name="is_page" column_invisible="1"/>
                        </list>
                    </field>
                </form>
            `,
    });
    expect("td.o_survey_description_page_cell").toHaveCount(2); // Check if we have the two rows in the list

    expect("tr.o_is_section").toHaveCount(1); // Check if we have only one section row
    expect(SELECTORS.section).toHaveProperty("colSpan", 1);

    await contains(SELECTORS.section).click();
    expect(SELECTORS.section + " div.input-group").toHaveCount(1);

    await contains(SELECTORS.numberQuestions).click();
    expect(SELECTORS.numberQuestions + " div").toHaveCount(1);
});
