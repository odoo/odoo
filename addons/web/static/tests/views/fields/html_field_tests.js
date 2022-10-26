/** @odoo-module **/

import { click, editInput, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";
import { HtmlField } from "@web/views/fields/html/html_field";

const RED_TEXT = /* html */ `<div class="kek" style="color:red">some text</div>`;
const GREEN_TEXT = /* html */ `<div class="kek" style="color:green">hello</div>`;
const BLUE_TEXT = /* html */ `<div class="kek" style="color:blue">hello world</div>`;

QUnit.module("Fields", ({ beforeEach }) => {
    let serverData;
    let target;

    beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        txt: { string: "txt", type: "html", trim: true },
                    },
                    records: [{ id: 1, txt: RED_TEXT }],
                },
            },
        };
        target = getFixture();

        setupViewRegistries();

        // Explicitly removed by web_editor, we need to add it back
        registry.category("fields").add("html", HtmlField, { force: true });
    });

    QUnit.module("HtmlField");

    QUnit.test("html fields are correctly rendered in form view (readonly)", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: /* xml */ `<form><field name="txt" readonly="1" /></form>`,
        });

        assert.containsOnce(target, "div.kek");
        assert.strictEqual(target.querySelector(".o_field_html .kek").style.color, "red");
        assert.strictEqual(target.querySelector(".o_field_html").textContent, "some text");
    });

    QUnit.test("html fields are correctly rendered (edit)", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: /* xml */ `<form><field name="txt" /></form>`,
        });

        const textarea = target.querySelector(".o_field_html textarea");
        assert.ok(textarea, "should have a text area");
        assert.strictEqual(textarea.value, RED_TEXT);

        await editInput(textarea, null, GREEN_TEXT);
        assert.strictEqual(textarea.value, GREEN_TEXT);
        assert.containsNone(target.querySelector(".o_field_html"), ".kek");

        await editInput(textarea, null, BLUE_TEXT);
        assert.strictEqual(textarea.value, BLUE_TEXT);
    });

    QUnit.test("html fields are correctly rendered in list view", async (assert) => {
        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                    <tree editable="top">
                        <field name="txt"/>
                    </tree>`,
        });
        const txt = target.querySelector(".o_data_row [name='txt']");
        assert.strictEqual(txt.textContent, "some text");
        assert.strictEqual(txt.querySelector(".kek").style.color, "red");

        await click(target.querySelector(".o_data_row [name='txt']"));
        assert.strictEqual(
            target.querySelector(".o_data_row [name='txt'] textarea").value,
            '<div class="kek" style="color:red">some text</div>'
        );
    });

    QUnit.test("html fields are correctly rendered in kanban view", async (assert) => {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban class="o_kanban_test">
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="txt"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        });
        const txt = target.querySelector(".kek");
        assert.strictEqual(txt.textContent, "some text");
        assert.strictEqual(txt.style.color, "red");
    });
});
