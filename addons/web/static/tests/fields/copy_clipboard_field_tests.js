/** @odoo-module **/

import { getFixture } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

let serverData, target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
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
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<div>" +
                '<field name="text_field" widget="CopyClipboardText"/>' +
                '<field name="char_field" widget="CopyClipboardChar"/>' +
                "</div>" +
                "</sheet>" +
                "</form>",
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

    QUnit.test("CopyClipboardField on unset field", async function (assert) {
        serverData.models.partner.records[0].char_field = false;

        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch:
                "<form>" +
                "<sheet>" +
                "<group>" +
                '<field name="char_field" widget="CopyClipboardChar" />' +
                "</group>" +
                "</sheet>" +
                "</form>",
            resId: 1,
        });

        assert.containsNone(
            target,
            '.o_field_copy[name="char_field"] .o_clipboard_button',
            "char_field (unset) should not contain a button"
        );
    });

    QUnit.test(
        "CopyClipboardField on readonly unset fields in create mode",
        async function (assert) {
            serverData.models.partner.fields.display_name.readonly = true;

            await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch:
                    "<form>" +
                    "<sheet>" +
                    "<group>" +
                    '<field name="display_name" widget="CopyClipboardChar" />' +
                    "</group>" +
                    "</sheet>" +
                    "</form>",
            });

            assert.containsNone(
                target,
                '.o_field_copy[name="display_name"] .o_clipboard_button',
                "the readonly unset field should not contain a button"
            );
        }
    );
});
