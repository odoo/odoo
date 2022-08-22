/** @odoo-module */

import { click, clickEdit, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

QUnit.module("DescriptionPageField", (hooks) => {
    let serverData;
    let target;

    hooks.beforeEach(() => {
        target = getFixture();

        serverData = {
            models: {
                partner: {
                    fields: { lines: { type: "one2many", relation: "lines_sections" } },
                    records: [
                        {
                            id: 1,
                            lines: [1, 2],
                        },
                    ],
                },
                lines_sections: {
                    fields: {
                        is_page: { type: "boolean" },
                        title: { type: "char", string: "Title" },
                        random_questions_count: { type: "number", string: "Question Count" },
                    },
                    records: [
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
                    ],
                },
            },
            views: {
                "lines_sections,false,form": `
                    <form>
                        <field name="title" />
                    </form>
                `,
            },
        };

        setupViewRegistries();
    });

    QUnit.test(
        "button is visible in the edited record and allows to open that record",
        async (assert) => {
            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                <form>
                    <field name="lines" widget="question_page_one2many">
                        <tree>
                            <field name="is_page" invisible="1" />
                            <field name="title" widget="survey_description_page"/>
                            <field name="random_questions_count" />
                        </tree>
                    </field>
                </form>
            `,
            });
            assert.containsN(target, "td.o_survey_description_page_cell", 2);
            assert.containsNone(target, "button.o_icon_button");

            await clickEdit(target);
            await click(target.querySelector(".o_data_cell"));
            assert.containsOnce(target.querySelector(".o_data_row"), "button.o_icon_button");
            assert.containsNone(target, ".modal .o_form_view_dialog");

            await click(target, "button.o_icon_button");
            assert.containsOnce(target, ".modal .o_form_view_dialog");
        }
    );
});
