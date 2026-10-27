/** @odoo-module */

import { click, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

QUnit.module("QuestionPageListRenderer", (hooks) => {
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
                        sequence: { type: "number" },
                        is_page: { type: "boolean" },
                        title: { type: "char", string: "Title" },
                        question_type: { type: "string" },
                        random_questions_count: { type: "number", string: "Question Count" },
                    },
                    records: [
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
                            question_type: 'simple_choice',
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
        "normal list view",
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
                            <field name="sequence" widget="handle"/>
                            <field name="title" widget="survey_description_page"/>
                            <field name="question_type" />
                            <field name="is_page" column_invisible="1"/>
                        </tree>
                    </field>
                </form>
            `,
            });
            assert.containsN(target, "td.o_survey_description_page_cell", 2); // Check if we have the two rows in the list

            assert.containsOnce(target, "tr.o_is_section"); // Check if we have only one section row
            const section = target.querySelector("tr.o_is_section > td.o_survey_description_page_cell");
            assert.strictEqual(section.colSpan, 2, 'The section should have a colspan of 1');

            await click(section);
            assert.containsOnce(section, 'div.input-group');
        }
    );

    QUnit.test(
        "list view with random count",
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
                            <field name="sequence" widget="handle"/>
                            <field name="title" widget="survey_description_page"/>
                            <field name="question_type" />
                            <field name="is_page" column_invisible="1"/>
                            <field name="random_questions_count"/>
                        </tree>
                    </field>
                </form>
            `,
            });
            assert.containsN(target, "td.o_survey_description_page_cell", 2); // Check if we have the two rows in the list

            assert.containsOnce(target, "tr.o_is_section"); // Check if we have only one section row
            const section = target.querySelector("tr.o_is_section > td.o_survey_description_page_cell");
            assert.strictEqual(section.colSpan, 2, 'The section should have a colspan of 2');

            // We can edit the section title
            await click(section);
            assert.containsOnce(section, 'div.input-group');

            //We can edit the number of random questions selected
            const numberQuestions = target.querySelector("tr.o_is_section > [name='random_questions_count']");
            await click(numberQuestions);
            assert.containsOnce(numberQuestions, 'div');
        }
    );

    QUnit.test(
        "list view with random but with question_type at the left of the title",
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
                            <field name="sequence" widget="handle"/>
                            <field name="question_type" />
                            <field name="title" widget="survey_description_page"/>
                            <field name="is_page" column_invisible="1"/>
                            <field name="random_questions_count"/>
                        </tree>
                    </field>
                </form>
            `,
            });
            assert.containsN(target, "td.o_survey_description_page_cell", 2); // Check if we have the two rows in the list

            assert.containsOnce(target, "tr.o_is_section"); // Check if we have only one section row
            const section = target.querySelector("tr.o_is_section > td.o_survey_description_page_cell");
            assert.strictEqual(section.colSpan, 1, 'The section should have a colspan of 1');

            await click(section);
            assert.containsOnce(section, 'div.input-group');

            const numberQuestions = target.querySelector("tr.o_is_section > [name='random_questions_count']");
            await click(numberQuestions);
            assert.containsOnce(numberQuestions, 'div');
        }
    );
    QUnit.test(
        "list view with random and question_type at the beginning of row",
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
                            <field name="sequence" widget="handle"/>
                            <field name="random_questions_count"/>
                            <field name="question_type" />
                            <field name="title" widget="survey_description_page"/>
                            <field name="is_page" column_invisible="1"/>
                        </tree>
                    </field>
                </form>
            `,
            });
            assert.containsN(target, "td.o_survey_description_page_cell", 2); // Check if we have the two rows in the list

            assert.containsOnce(target, "tr.o_is_section"); // Check if we have only one section row
            const section = target.querySelector("tr.o_is_section > td.o_survey_description_page_cell");
            assert.strictEqual(section.colSpan, 1, 'The section should have a colspan of 1');

            await click(section);
            assert.containsOnce(section, 'div.input-group');

            const numberQuestions = target.querySelector("tr.o_is_section > [name='random_questions_count']");
            await click(numberQuestions);
            assert.containsOnce(numberQuestions, 'div');
        }
    );
});
