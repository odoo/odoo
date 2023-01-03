/** @odoo-module **/

import { click, editInput, getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { registry } from "@web/core/registry";
import { HtmlField } from "@web/views/fields/html/html_field";
import { makeFakeLocalizationService } from "@web/../tests/helpers/mock_services";
import { session } from "@web/session";

const RED_TEXT = /* html */ `<div class="kek" style="color:red">some text</div>`;
const GREEN_TEXT = /* html */ `<div class="kek" style="color:green">hello</div>`;
const BLUE_TEXT = /* html */ `<div class="kek" style="color:blue">hello world</div>`;
const serviceRegistry = registry.category("services");

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

    QUnit.test("field html translatable", async (assert) => {
        assert.expect(10);

        serverData.models.partner.fields.txt.translate = true;
        serviceRegistry.add("localization", makeFakeLocalizationService({ multiLang: true }), {
            force: true,
        });
        patchWithCleanup(session.user_context, {
            lang: "en_US",
        });

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form string="Partner">
                    <sheet>
                        <group>
                            <field name="txt" widget="html"/>
                        </group>
                    </sheet>
                </form>`,
            mockRPC(route, { args, method, model }) {
                if (route === "/web/dataset/call_kw/partner/get_field_translations") {
                    assert.deepEqual(
                        args,
                        [[1], "txt"],
                        "should translate the txt field of the record"
                    );
                    return Promise.resolve([
                        [
                            { lang: "en_US", source: "first paragraph", value: "first paragraph" },
                            {
                                lang: "en_US",
                                source: "second paragraph",
                                value: "second paragraph",
                            },
                            {
                                lang: "fr_BE",
                                source: "first paragraph",
                                value: "",
                            },
                            {
                                lang: "fr_BE",
                                source: "second paragraph",
                                value: "deuxième paragraphe",
                            },
                        ],
                        { translation_type: "char", translation_show_source: true },
                    ]);
                }
                if (route === "/web/dataset/call_kw/res.lang/get_installed") {
                    return Promise.resolve([
                        ["en_US", "English"],
                        ["fr_BE", "French (Belgium)"],
                    ]);
                }
                if (route === "/web/dataset/call_kw/partner/update_field_translations") {
                    assert.deepEqual(
                        args,
                        [
                            [1],
                            "txt",
                            {
                                en_US: { "first paragraph": "first paragraph modified" },
                                fr_BE: {
                                    "first paragraph": "premier paragraphe modifié",
                                    "deuxième paragraphe": "deuxième paragraphe modifié",
                                },
                            },
                        ],
                        "the new translation value should be written"
                    );
                    return Promise.resolve(null);
                }
            },
        });

        assert.hasClass(target.querySelector("[name=txt] textarea"), "o_field_translate");

        assert.containsOnce(
            target,
            ".o_field_html .btn.o_field_translate",
            "should have a translate button"
        );
        assert.strictEqual(
            target.querySelector(".o_field_html .btn.o_field_translate").textContent,
            "EN",
            "the button should have as test the current language"
        );
        await click(target, ".o_field_html .btn.o_field_translate");

        assert.containsOnce(target, ".modal", "a translate modal should be visible");
        assert.containsN(target, ".translation", 4, "four rows should be visible");

        const translations = target.querySelectorAll(
            ".modal .o_translation_dialog .translation input"
        );

        const enField1 = translations[0];
        assert.strictEqual(
            enField1.value,
            "first paragraph",
            "first part of english translation should be filled"
        );
        await editInput(enField1, null, "first paragraph modified");

        const frField1 = translations[2];
        assert.strictEqual(
            frField1.value,
            "",
            "first part of french translation should not be filled"
        );
        await editInput(frField1, null, "premier paragraphe modifié");

        const frField2 = translations[3];
        assert.strictEqual(
            frField2.value,
            "deuxième paragraphe",
            "second part of french translation should be filled"
        );
        await editInput(frField2, null, "deuxième paragraphe modifié");

        await click(target, ".modal button.btn-primary"); // save
    });

    QUnit.test("html fields: spellcheck is disabled on blur", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: /* xml */ `<form><field name="txt" /></form>`,
        });

        const textarea = target.querySelector(".o_field_html textarea");
        assert.strictEqual(textarea.spellcheck, true, "by default, spellcheck is enabled");
        textarea.focus();

        await editInput(textarea, null, "nev walue");
        textarea.blur();
        assert.strictEqual(
            textarea.spellcheck,
            false,
            "spellcheck is disabled once the field has lost its focus"
        );
        textarea.focus();
        assert.strictEqual(
            textarea.spellcheck,
            true,
            "spellcheck is re-enabled once the field is focused"
        );
    });
});
