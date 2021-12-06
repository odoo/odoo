/** @odoo-module **/

import { click, triggerEvent } from "../helpers/utils";
import { setupControlPanelServiceRegistry } from "../search/helpers";
import { makeView } from "../views/helpers";

let serverData;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        foo: {
                            string: "Foo",
                            type: "char",
                            default: "My little Foo Value",
                            trim: true,
                        },
                        empty_string: {
                            string: "Empty string",
                            type: "char",
                            default: false,
                            searchable: true,
                            trim: true,
                        },
                        int_field: {
                            string: "int_field",
                            type: "integer",
                            sortable: true,
                            searchable: true,
                        },
                    },
                    records: [
                        {
                            foo: "yop",
                        },
                    ],
                },
            },
        };

        setupControlPanelServiceRegistry();
    });

    QUnit.module("EmailField");

    QUnit.test("EmailField in form view", async function (assert) {
        assert.expect(7);

        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="foo" widget="email"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            resId: 1,
        });
        let mailtoLink = form.el.querySelector("a.o-email-field.o_form_uri.o_text_overflow");
        assert.containsOnce(form, mailtoLink, "should have a anchor with correct classes");
        assert.strictEqual(mailtoLink.innerText, "yop", "the value should be displayed properly");
        assert.hasAttrValue(mailtoLink, "href", "mailto:yop", "should have proper mailto prefix");

        // switch to edit mode and check the result
        await click(form.el.querySelector(".o_form_button_edit"));
        const mailtoEdit = form.el.querySelector('input[type="email"].o-email-field');
        assert.containsOnce(form, mailtoEdit, "should have an input for the email field");
        assert.strictEqual(
            mailtoEdit.value,
            "yop",
            "input should contain field value in edit mode"
        );

        // change value in edit mode
        mailtoEdit.value = "new";
        await triggerEvent(mailtoEdit, null, "change");

        // save
        await click(form.el.querySelector(".o_form_button_save"));
        mailtoLink = form.el.querySelector("a.o-email-field");
        assert.strictEqual(mailtoLink.innerText, "new", "new value should be displayed properly");
        assert.hasAttrValue(
            mailtoLink,
            "href",
            "mailto:new",
            "should still have proper mailto prefix"
        );
    });

    QUnit.skip("EmailField in editable list view", async function (assert) {
        assert.expect(10);

        var list = await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: '<tree edit="1" editable="bottom"><field name="foo"  widget="email"/></tree>',
        });

        assert.strictEqual(
            list.el.querySelectorAll("tbody td:not(.o_list_record_selector)").length,
            5,
            "should have 5 cells"
        );
        assert.strictEqual(
            list.el.querySelector("tbody td:not(.o_list_record_selector)").innerText,
            "yop",
            "value should be displayed properly as text"
        );

        var mailtoLink = list.el.querySelectorAll("a.o-email-field");
        assert.strictEqual(mailtoLink.length, 5, "should have anchors with correct classes");
        assert.hasAttrValue(
            mailtoLink[0],
            "href",
            "mailto:yop",
            "should have proper mailto prefix"
        );
        // Edit a line and check the result
        var cell = list.el.querySelector("tbody td:not(.o_list_record_selector)");
        await click(cell);
        assert.hasClass(cell.parentElement, "o_selected_row", "should be set as edit mode");
        const mailField = cell.querySelector("input");
        assert.strictEqual(
            mailField.value,
            "yop",
            "should have the correct value in internal input"
        );
        mailField.value = "new";
        await triggerEvent(mailField, null, "change");

        // save
        await click(list.buttons.find(".o_list_button_save"));
        cell = list.el.querySelector("tbody td:not(.o_list_record_selector)");
        assert.doesNotHaveClass(
            cell.parentElement,
            "o_selected_row",
            "should not be in edit mode anymore"
        );
        assert.strictEqual(
            list.el.querySelector("tbody td:not(.o_list_record_selector)").innerText,
            "new",
            "value should be properly updated"
        );
        mailtoLink = list.el.querySelectorAll(
            "div.o_form_uri.o_field_widget.o_text_overflow.o-email-field > a"
        );
        assert.strictEqual(mailtoLink.length, 5, "should still have anchors with correct classes");
        assert.hasAttrValue(
            mailtoLink[0],
            "href",
            "mailto:new",
            "should still have proper mailto prefix"
        );
    });

    QUnit.test("EmailField with empty value", async function (assert) {
        assert.expect(1);

        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch:
                "<form>" +
                "<sheet>" +
                "<group>" +
                '<field name="empty_string" widget="email"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
        });

        await click(form.el.querySelector(".o_form_button_save"));
        const mailtoLink = form.el.querySelector("a.o-email-field");
        assert.strictEqual(mailtoLink.innerText, "", "the value should be displayed properly");
    });

    QUnit.test("EmailField trim user value", async function (assert) {
        assert.expect(1);

        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: '<form><field name="foo" widget="email"/></form>',
        });
        const mailField = form.el.querySelector('input[name="foo"]');
        mailField.value = "  abc@abc.com  ";
        await triggerEvent(mailField, null, "change");
        await click(form.el.querySelector(".o_form_button_save"));
        await click(form.el.querySelector(".o_form_button_edit"));
        assert.strictEqual(mailField.value, "abc@abc.com", "Foo value should have been trimmed");
    });

    QUnit.test(
        "readonly EmailField is properly rerendered after been changed by onchange",
        async function (assert) {
            assert.expect(2);

            serverData.models.partner.records[0].foo = "dolores.abernathy@delos";
            const form = await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch:
                    '<form string="Partners">' +
                    "<sheet>" +
                    "<group>" +
                    '<field name="int_field" on_change="1"/>' + // onchange to update mobile in readonly mode directly
                    '<field name="foo" widget="email" readonly="1"/>' + // readonly only, we don't want to go through write mode
                    "</group>" +
                    "</sheet>" +
                    "</form>",
                resId: 1,
                mockRPC(route, { method }) {
                    if (method === "onchange") {
                        return Promise.resolve({
                            value: {
                                foo: "lara.espin@unknown", // onchange to update foo in readonly mode directly
                            },
                        });
                    }
                },
            });
            // check initial rendering
            assert.strictEqual(
                form.el.querySelector(".o-email-field").innerText,
                "dolores.abernathy@delos",
                "Initial email text should be set"
            );

            // edit the phone field, but with the mail in readonly mode
            await click(form.el.querySelector(".o_form_button_edit"));
            const field = form.el.querySelector('input[name="int_field"]');
            field.value = 3;
            await triggerEvent(field, null, "change");
            await click(form.el.querySelector(".o_form_button_save"));

            // check rendering after changes
            assert.strictEqual(
                form.el.querySelector(".o-email-field").innerText,
                "lara.espin@unknown",
                "email text should be updated"
            );
        }
    );
});
