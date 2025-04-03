import { expect, test } from "@odoo/hoot";
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

defineModels([Partner, LinesSections]);
defineMailModels();

test("button is visible in the edited record and allows to open that record", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
            <form>
                <field name="lines" widget="question_page_one2many">
                    <list>
                        <field name="is_page" invisible="1" />
                        <field name="title" widget="survey_description_page"/>
                        <field name="random_questions_count" />
                    </list>
                </field>
            </form>
        `,
    });
    expect("td.o_survey_description_page_cell").toHaveCount(2);
    expect("button.o_icon_button").toHaveCount(0);

    await contains(".o_data_cell").click();
    expect(".o_data_row button.o_icon_button").toHaveCount(1);
    expect(".modal .o_form_view").toHaveCount(0);

    await contains("button.o_icon_button").click();
    expect(".modal .o_form_view").toHaveCount(1);
});
