/** @odoo-module */

import { makeServerError } from "@web/../tests/helpers/mock_server";
import { click, editInput, getFixture, nextTick, triggerHotkey } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { errorService } from "@web/core/errors/error_service";
import { registry } from "@web/core/registry";

QUnit.module("QuestionPageOneToManyField", (hooks) => {
    let serverData;
    let target;

    hooks.beforeEach(() => {
        target = getFixture();

        serverData = {
            models: {
                survey: {
                    fields: {
                        question_and_page_ids: { type: "one2many", relation: "survey_question" },
                        favorite_color: { string: "Favorite color", type: "char" }
                    },
                    records: [
                        {
                            id: 1,
                            question_and_page_ids: [1, 2],
                            favorite_color: ""
                        },
                    ],
                },
                survey_question: {
                    fields: {
                        is_page: { type: "boolean" },
                        title: { type: "char", string: "Title" },
                        random_questions_count: { type: "integer", string: "Question Count" },
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
                "survey_question,false,form": `
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
            resModel: "survey",
            resId: 1,
            serverData,
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
            resModel: "survey",
            resId: 1,
            serverData,
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
            mode: "readonly",
        });

        await click(target.querySelector(".o_data_cell"));
        assert.containsNone(target, ".o_selected_row");
        assert.containsOnce(target, ".modal .o_form_view");
    });

    QUnit.test("click on section edit the section in place", async (assert) => {
        await makeView({
            type: "form",
            resModel: "survey",
            resId: 1,
            serverData,
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
        await click(target.querySelector(".o_data_cell"));
        assert.hasClass(target.querySelector(".o_is_section"), "o_selected_row");
        assert.containsNone(target, ".modal .o_form_view");
    });

    QUnit.test("click on real line saves form and opens a dialog", async (assert) => {
        await makeView({
            type: "form",
            resModel: "survey",
            resId: 1,
            serverData,
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
            mockRPC(route, args) {
                if (args.method === "web_save" && args.model === "survey") {
                    assert.step("save parent form");
                }
            },
        });
        await editInput(target, "[name='favorite_color'] input", "Yellow");
        await click(target.querySelector(".o_data_row:nth-child(2) .o_data_cell"));
        // Edit content to trigger the expected actual save at row opening
        assert.verifySteps(["save parent form"]);
        assert.containsOnce(target, ".o_selected_row");
        assert.containsOnce(target, ".modal .o_form_view");
    });

    QUnit.test("A validation error from saving parent form notifies and prevents dialog from closing", async (assert) => {
        registry.category("services").add("error", errorService);

        await makeView({
            type: "form",
            resModel: "survey",
            resId: 1,
            serverData,
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
            mockRPC(route, args) {
                if (args.method === "web_save" && args.model === "survey") {
                    assert.step("save parent form");
                    throw makeServerError({
                        description: "This isn't right!",
                        type: "ValidationError",
                    });

                }
            },
        });
        await click(target.querySelector(".o_data_row:nth-child(2) .o_data_cell"));
        await editInput(target, ".o_dialog:not(.o_inactive_modal) .modal-body [name='title'] input", "Invalid RecordTitle");
        await click(target.querySelector(".o_dialog:not(.o_inactive_modal) .o_form_button_save"));
        assert.verifySteps(["save parent form"]);
        await nextTick();
        assert.containsOnce(document.body, ".o_notification");
        assert.containsOnce(target, ".modal .o_form_view");
        assert.containsOnce(target, ".modal-dialog .o_form_button_save");
        assert.containsNone(target, ".modal-dialog .o_form_button_save[disabled='1']");
    });

    QUnit.test("can create section inline", async (assert) => {
        await makeView({
            type: "form",
            resModel: "survey",
            resId: 1,
            serverData,
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

        assert.containsNone(target, ".o_selected_row");

        await click(target.querySelectorAll(".o_field_x2many_list_row_add a")[1]);
        assert.containsOnce(target, ".o_selected_row.o_is_section");
        assert.containsNone(target, ".modal .o_form_view");
    });

    QUnit.test("creates real record in form dialog", async (assert) => {
        await makeView({
            type: "form",
            resModel: "survey",
            resId: 1,
            serverData,
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

        await click(target.querySelector(".o_field_x2many_list_row_add a"));
        assert.containsNone(target, ".o_selected_row");
        assert.containsOnce(target, ".modal .o_form_view");
    });

    QUnit.test(
        "press enter with focus in a edited section pass the section in readonly mode",
        async (assert) => {
            await makeView({
                type: "form",
                resModel: "survey",
                resId: 1,
                serverData,
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
