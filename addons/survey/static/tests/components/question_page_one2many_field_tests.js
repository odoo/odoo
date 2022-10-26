/** @odoo-module */

import { click, editInput, getFixture, nextTick, triggerHotkey } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

QUnit.module("QuestionPageOneToManyField", (hooks) => {
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

    QUnit.test("basic rendering", async (assert) => {
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
                            <field name="title" />
                            <field name="random_questions_count" />
                        </tree>
                    </field>
                </form>
            `,
        });
        assert.containsOnce(target, ".o_field_x2many .o_list_renderer table.o_section_list_view");
        assert.containsN(target, ".o_data_row", 2);
        const rows = target.querySelectorAll(".o_data_row");
        assert.hasClass(rows[0], "o_is_section");
        assert.hasClass(rows[0], "fw-bold");
        assert.strictEqual(rows[0].textContent, "firstSectionTitle4");
        assert.strictEqual(rows[1].textContent, "recordTitle5");
        assert.strictEqual(rows[0].querySelector("td[name=title]").getAttribute("colspan"), "1");
        assert.strictEqual(rows[1].querySelector("td[name=title]").getAttribute("colspan"), null);
    });

    QUnit.test("click on section behaves as usual in readonly mode", async (assert) => {
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
                            <field name="title" />
                            <field name="random_questions_count" />
                        </tree>
                    </field>
                </form>
            `,
            mode: "readonly",
        });

        await click(target.querySelector(".o_data_cell"));
        assert.containsNone(target, ".o_selected_row");
        assert.containsOnce(target, ".modal .o_form_view");
    });

    QUnit.test("click on section edit the section in place", async (assert) => {
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
                            <field name="title" />
                            <field name="random_questions_count" />
                        </tree>
                    </field>
                </form>`,
        });
        await click(target.querySelector(".o_data_cell"));
        assert.hasClass(target.querySelector(".o_is_section"), "o_selected_row");
        assert.containsNone(target, ".modal .o_form_view");
    });

    QUnit.test("click on real line opens a dialog", async (assert) => {
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
                            <field name="title" />
                            <field name="random_questions_count" />
                        </tree>
                    </field>
                </form>
            `,
        });
        await click(target.querySelector(".o_data_row:nth-child(2) .o_data_cell"));
        assert.containsNone(target, ".o_selected_row");
        assert.containsOnce(target, ".modal .o_form_view");
    });

    QUnit.test("can create section inline", async (assert) => {
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
                            <field name="title" />
                            <field name="random_questions_count" />
                            <control>
                                <create string="add line" />
                                <create string="add section" context="{'default_is_page': true}" />
                            </control>
                        </tree>
                    </field>
                </form>
            `,
        });

        assert.containsNone(target, ".o_selected_row");

        await click(target.querySelectorAll(".o_field_x2many_list_row_add a")[1]);
        assert.containsOnce(target, ".o_selected_row.o_is_section");
        assert.containsNone(target, ".modal .o_form_view");
    });

    QUnit.test("creates real record in form dialog", async (assert) => {
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
                            <field name="title" />
                            <field name="random_questions_count" />
                            <control>
                                <create string="add line" />
                                <create string="add section" context="{'default_is_page': true}" />
                            </control>
                        </tree>
                    </field>
                </form>
            `,
        });

        await click(target.querySelector(".o_field_x2many_list_row_add a"));
        assert.containsNone(target, ".o_selected_row");
        assert.containsOnce(target, ".modal .o_form_view");
    });

    QUnit.test(
        "press enter with focus in a edited section pass the section in readonly mode",
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
                            <field name="title" />
                            <field name="random_questions_count" />
                        </tree>
                    </field>
                </form>
            `,
            });
            await click(target.querySelector(".o_data_row .o_data_cell"));
            assert.containsOnce(target, ".o_selected_row.o_is_section");

            await editInput(target, "[name='title'] input", "a");

            triggerHotkey("Enter");
            await nextTick();

            assert.containsNone(target, ".o_selected_row.o_is_section");
            assert.strictEqual(target.querySelector(".o_is_section [name=title]").innerText, "a");
        }
    );
});
