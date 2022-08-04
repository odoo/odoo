/** @odoo-module **/

import { click, editInput, getFixture, triggerEvent } from "@web/../tests/helpers/utils";
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

    QUnit.test("html fields are correctly rendered", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: /* xml */ `<form><field name="txt" /></form>`,
        });

        assert.containsOnce(target, ".o_field_html", "should have a text area");
        assert.strictEqual(target.querySelector(".o_field_html .kek").style.color, "red");
        assert.strictEqual(target.querySelector(".o_field_html").textContent, "some text");

        await click(target, ".o_form_button_edit");
        const textarea = target.querySelector(".o_field_html textarea");
        assert.ok(textarea, "should have a text area");
        assert.strictEqual(textarea.value, RED_TEXT);

        await editInput(textarea, null, GREEN_TEXT);
        assert.strictEqual(textarea.value, GREEN_TEXT);
        assert.containsNone(target.querySelector(".o_field_html"), ".kek");

        await editInput(textarea, null, BLUE_TEXT);
        assert.strictEqual(textarea.value, BLUE_TEXT);

        await click(target, ".o_form_button_save");

        assert.strictEqual(target.querySelector(".o_field_html .kek").style.color, "blue");
        assert.strictEqual(target.querySelector(".o_field_html").textContent, "hello world");
    });

    QUnit.test("html fields: spellcheck is disabled on blur", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: /* xml */ `<form><field name="txt" /></form>`,
        });

        await click(target, ".o_form_button_edit");
        const textarea = target.querySelector(".o_field_html textarea");

        assert.strictEqual(textarea.spellcheck, false, "by default, spellcheck is disabled");
        textarea.focus();

        await triggerEvent(textarea, null, "focus");
        assert.strictEqual(
            textarea.spellcheck,
            true,
            "spellcheck is re-enabled once the field is focused"
        );

        await editInput(textarea, null, "nev walue");
        textarea.blur();

        assert.strictEqual(
            textarea.spellcheck,
            false,
            "spellcheck is disabled once the field has lost its focus"
        );
    });
});
