/** @odoo-module **/

import { click, clickSave, editInput, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
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
                    records: [{ foo: "yop" }, { foo: "blip" }],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("EmailField");

    QUnit.test("EmailField in form view", async function (assert) {
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="foo" widget="email"/>
                        </group>
                    </sheet>
                </form>`,
            resId: 1,
        });

        // switch to edit mode and check the result
        const mailtoEdit = target.querySelector('.o_field_email input[type="email"]');
        assert.containsOnce(target, mailtoEdit, "should have an input for the email field");
        assert.strictEqual(
            mailtoEdit.value,
            "yop",
            "input should contain field value in edit mode"
        );

        const emailBtn = target.querySelector(".o_field_email a");
        assert.containsOnce(
            target,
            emailBtn,
            "should have rendered the email button as a link with correct classes"
        );
        assert.hasAttrValue(emailBtn, "href", "mailto:yop", "should have proper mailto prefix");
        assert.hasAttrValue(
            emailBtn,
            "target",
            "_blank",
            "should have target attribute set to _blank"
        );

        // change value in edit mode
        await editInput(target, ".o_field_email input[type='email']", "new");

        // save
        await clickSave(target);
        const mailtoLink = target.querySelector(".o_field_email input[type='email']");
        assert.strictEqual(mailtoLink.value, "new", "new value should be displayed properly");
    });

    QUnit.test("EmailField in editable list view", async function (assert) {
        await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: '<tree editable="bottom"><field name="foo" widget="email"/></tree>',
        });
        assert.strictEqual(
            target.querySelectorAll("tbody td:not(.o_list_record_selector) a").length,
            2,
            "should have 2 cells with a link"
        );
        assert.strictEqual(
            target.querySelector("tbody td:not(.o_list_record_selector)").textContent,
            "yop",
            "value should be displayed properly as text"
        );

        let mailtoLink = target.querySelectorAll(".o_field_email a");
        assert.containsN(
            target,
            ".o_field_email a",
            2,
            "should have 2 anchors with correct classes"
        );
        assert.hasAttrValue(
            mailtoLink[0],
            "href",
            "mailto:yop",
            "should have proper mailto prefix"
        );
        // Edit a line and check the result
        let cell = target.querySelector("tbody td:not(.o_list_record_selector)");
        await click(cell);
        assert.hasClass(cell.parentElement, "o_selected_row", "should be set as edit mode");
        const mailField = cell.querySelector("input");
        assert.strictEqual(
            mailField.value,
            "yop",
            "should have the correct value in internal input"
        );
        await editInput(cell, "input", "new");

        // save
        await clickSave(target);
        cell = target.querySelector("tbody td:not(.o_list_record_selector)");
        assert.doesNotHaveClass(
            cell.parentElement,
            "o_selected_row",
            "should not be in edit mode anymore"
        );
        assert.strictEqual(
            target.querySelector("tbody td:not(.o_list_record_selector)").textContent,
            "new",
            "value should be properly updated"
        );
        mailtoLink = target.querySelectorAll(".o_field_widget[name='foo'] a");
        assert.strictEqual(mailtoLink.length, 2, "should still have anchors with correct classes");
        assert.hasAttrValue(
            mailtoLink[0],
            "href",
            "mailto:new",
            "should still have proper mailto prefix"
        );
    });

    QUnit.test("EmailField with empty value", async function (assert) {
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="empty_string" widget="email" placeholder="Placeholder"/>
                        </group>
                    </sheet>
                </form>`,
        });
        const input = target.querySelector(".o_field_email input");
        assert.strictEqual(input.placeholder, "Placeholder");
        assert.strictEqual(input.value, "", "the value should be displayed properly");
    });

    QUnit.test("EmailField trim user value", async function (assert) {
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: '<form><field name="foo" widget="email"/></form>',
        });
        await editInput(target, ".o_field_widget[name='foo'] input", "  abc@abc.com  ");
        const mailFieldInput = target.querySelector('.o_field_widget[name="foo"] input');
        await clickSave(target);
        assert.strictEqual(
            mailFieldInput.value,
            "abc@abc.com",
            "Foo value should have been trimmed"
        );
    });

    QUnit.test(
        "readonly EmailField is properly rerendered after been changed by onchange",
        async function (assert) {
            serverData.models.partner.records[0].foo = "dolores.abernathy@delos";
            await makeView({
                serverData,
                type: "form",
                resModel: "partner",
                arch: `
                    <form>
                        <sheet>
                            <group>
                                <field name="int_field" on_change="1"/> <!-- onchange to update mobile in readonly mode directly -->
                                <field name="foo" widget="email" readonly="1"/> <!-- readonly only, we don't want to go through write mode -->
                            </group>
                        </sheet>
                    </form>`,
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
                target.querySelector(".o_field_email").textContent,
                "dolores.abernathy@delos",
                "Initial email text should be set"
            );

            // edit the phone field, but with the mail in readonly mode
            await editInput(target, ".o_field_widget[name='int_field'] input", 3);

            // check rendering after changes
            assert.strictEqual(
                target.querySelector(".o_field_email").textContent,
                "lara.espin@unknown",
                "email text should be updated"
            );
        }
    );

    QUnit.test("email field with placeholder", async function (assert) {
        serverData.models.partner.fields.foo.default = false;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="foo" placeholder="New Placeholder" />
                        </group>
                    </sheet>
                </form>`,
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget[name='foo'] input").placeholder,
            "New Placeholder"
        );
    });
});
