/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import {
    click,
    getFixture,
    editInput,
    nextTick,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

const serviceRegistry = registry.category("services");
let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach((assert) => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char", searchable: true },
                        char_field: {
                            string: "Foo",
                            type: "char",
                            default: "My little Foo Value",
                            searchable: true,
                            trim: true,
                        },
                        text_field: {
                            string: "txt",
                            type: "text",
                            default: "My little txt Value\nHo-ho-hoooo Merry Christmas",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            char_field: "yop",
                        },
                    ],
                },
            },
        };
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.module("CopyClipboardField");

    QUnit.test("Char & Text Fields: Copy to clipboard button", async function (assert) {
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <sheet>
                        <div>
                            <field name="text_field" widget="CopyClipboardText"/>
                            <field name="char_field" widget="CopyClipboardChar"/>
                        </div>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(
            target,
            ".o_clipboard_button.o_btn_text_copy",
            "Should have copy button on text type field"
        );
        assert.containsOnce(
            target,
            ".o_clipboard_button.o_btn_char_copy",
            "Should have copy button on char type field"
        );
    });

    QUnit.test("CopyClipboardField: show copy button even on empty field", async function (assert) {
        serverData.models.partner.records[0].char_field = false;
        serverData.models.partner.records[0].text_field = false;

        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="char_field" widget="CopyClipboardChar" />
                            <field name="text_field" widget="CopyClipboardText" />
                        </group>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(
            target,
            '.o_field_CopyClipboardChar[name="char_field"] .o_clipboard_button'
        );
        assert.containsOnce(
            target,
            '.o_field_CopyClipboardText[name="text_field"] .o_clipboard_button'
        );
    });

    QUnit.test(
        "CopyClipboardField: show copy button even on readonly empty field",
        async function (assert) {
            serverData.models.partner.fields.display_name.readonly = true;

            await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="display_name" widget="CopyClipboardChar" />
                            </group>
                        </sheet>
                    </form>`,
            });

            assert.containsOnce(
                target,
                '.o_field_CopyClipboardChar[name="display_name"] .o_clipboard_button'
            );
        }
    );

    QUnit.test("CopyClipboard fields: display a tooltip on click", async function (assert) {
        const fakePopoverService = {
            async start() {
                return {
                    add(el, comp, params) {
                        assert.strictEqual(el.textContent, "Copy", "button has the right text");
                        assert.deepEqual(
                            params,
                            { tooltip: "Copied" },
                            "tooltip has the right parameters"
                        );
                        assert.step("copied tooltip");
                    },
                };
            },
        };
        serviceRegistry.remove("popover");
        serviceRegistry.add("popover", fakePopoverService);

        patchWithCleanup(browser, {
            navigator: {
                clipboard: {
                    writeText: (text) => {
                        assert.strictEqual(
                            text,
                            "My little txt Value\nHo-ho-hoooo Merry Christmas",
                            "copied text is equal to displayed text"
                        );
                        return Promise.resolve();
                    },
                },
            },
        });

        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <sheet>
                        <div>
                            <field name="text_field" widget="CopyClipboardText"/>
                        </div>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(
            target,
            ".o_clipboard_button.o_btn_text_copy",
            "should have copy button on text type field"
        );

        await click(target, ".o_clipboard_button");
        await nextTick();
        assert.verifySteps(["copied tooltip"]);
    });

    QUnit.module("CopyClipboardButtonField");

    QUnit.test("CopyClipboardButtonField in form view", async function (assert) {
        patchWithCleanup(browser, {
            navigator: {
                clipboard: {
                    writeText: (text) => {
                        assert.step(text);
                        return Promise.resolve();
                    },
                },
            },
        });

        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <sheet>
                        <div>
                            <field name="text_field" widget="CopyClipboardButton"/>
                            <field name="char_field" widget="CopyClipboardButton"/>
                        </div>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.containsNone(target.querySelector(".o_field_widget[name=char_field]"), "input");
        assert.containsNone(target.querySelector(".o_field_widget[name=text_field]"), "input");
        assert.containsOnce(target, ".o_clipboard_button.o_btn_text_copy");
        assert.containsOnce(target, ".o_clipboard_button.o_btn_char_copy");

        await click(target.querySelector(".o_clipboard_button.o_btn_text_copy"));
        await click(target.querySelector(".o_clipboard_button.o_btn_char_copy"));

        assert.verifySteps([
            `My little txt Value
Ho-ho-hoooo Merry Christmas`,
            "yop",
        ]);
    });

    QUnit.test("CopyClipboardButtonField can be disabled", async function (assert) {
        patchWithCleanup(browser, {
            navigator: {
                clipboard: {
                    writeText: (text) => {
                        assert.step(text);
                        return Promise.resolve();
                    },
                },
            },
        });

        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <sheet>
                        <div>
                            <field name="text_field" disabled="1" widget="CopyClipboardButton"/>
                            <field name="char_field" disabled="char_field == 'yop'" widget="CopyClipboardButton"/>
                            <field name="char_field" widget="char"/>
                        </div>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(
            target,
            ".o_clipboard_button.o_btn_text_copy[disabled]",
            "The inner button should be disabled."
        );
        assert.containsOnce(
            target,
            ".o_clipboard_button.o_btn_char_copy[disabled]",
            "The inner button should be disabled."
        );

        await editInput(target, ".o_input", "yip");
        assert.containsNone(
            target,
            ".o_clipboard_button.o_btn_char_copy[disabled]",
            "The inner button should not be disabled."
        );
    });
});
