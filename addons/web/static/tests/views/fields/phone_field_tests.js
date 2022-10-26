/** @odoo-module **/

import { getNextTabableElement } from "@web/core/utils/ui";
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
                    },
                    records: [{ foo: "yop" }, { foo: "blip" }],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("PhoneField");

    QUnit.test("PhoneField in form view on normal screens (readonly)", async function (assert) {
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            mode: "readonly",
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="foo" widget="phone"/>
                        </group>
                    </sheet>
                </form>`,
            resId: 1,
        });

        const phone = target.querySelector(".o_field_phone a");
        assert.containsOnce(
            target,
            phone,
            "should have rendered the phone number as a link with correct classes"
        );
        assert.strictEqual(phone.textContent, "yop", "value should be displayed properly");
        assert.hasAttrValue(phone, "href", "tel:yop", "should have proper tel prefix");
    });

    QUnit.test("PhoneField in form view on normal screens (edit)", async function (assert) {
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="foo" widget="phone"/>
                        </group>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(
            target,
            'input[type="tel"]',
            "should have an input for the phone field"
        );
        assert.strictEqual(
            target.querySelector('input[type="tel"]').value,
            "yop",
            "input should contain field value in edit mode"
        );

        const phoneLink = target.querySelector(".o_field_phone a");
        assert.containsOnce(
            target,
            phoneLink,
            "should have rendered the phone number as a link with correct classes"
        );
        assert.strictEqual(phoneLink.textContent, "Call", "link is shown with the right text");
        assert.hasAttrValue(phoneLink, "href", "tel:yop", "should have proper tel prefix");

        // change value in edit mode
        await editInput(target, "input[type='tel']", "new");

        // save
        await clickSave(target);
        assert.strictEqual(
            target.querySelector("input[type='tel']").value,
            "new",
            "new value should be displayed properly"
        );
    });

    QUnit.test("PhoneField in editable list view on normal screens", async function (assert) {
        await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: '<tree editable="bottom"><field name="foo" widget="phone"/></tree>',
        });

        assert.containsN(target, "tbody td:not(.o_list_record_selector).o_data_cell", 2);
        assert.strictEqual(
            target.querySelector("tbody td:not(.o_list_record_selector) a").textContent,
            "yop",
            "value should be displayed properly with a link to send SMS"
        );

        assert.containsN(
            target,
            ".o_field_widget a.o_form_uri",
            2,
            "should have the correct classnames"
        );

        // Edit a line and check the result
        let cell = target.querySelector("tbody td:not(.o_list_record_selector)");
        await click(cell);
        assert.hasClass(cell.parentElement, "o_selected_row", "should be set as edit mode");
        assert.strictEqual(
            cell.querySelector("input").value,
            "yop",
            "should have the corect value in internal input"
        );
        await editInput(cell, "input", "new");

        // save
        await click(target.querySelector(".o_list_button_save"));
        cell = target.querySelector("tbody td:not(.o_list_record_selector)");
        assert.doesNotHaveClass(
            cell.parentElement,
            "o_selected_row",
            "should not be in edit mode anymore"
        );
        assert.strictEqual(
            target.querySelector("tbody td:not(.o_list_record_selector) a").textContent,
            "new",
            "value should be properly updated"
        );
        assert.containsN(
            target,
            ".o_field_widget a.o_form_uri",
            2,
            "should still have links with correct classes"
        );
    });

    QUnit.test("use TAB to navigate to a PhoneField", async function (assert) {
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="display_name"/>
                            <field name="foo" widget="phone"/>
                        </group>
                    </sheet>
                </form>`,
        });
        target.querySelector(".o_field_widget[name=display_name] input").focus();
        assert.strictEqual(
            document.activeElement,
            target.querySelector('.o_field_widget[name="display_name"] input'),
            "display_name should be focused"
        );
        assert.strictEqual(
            getNextTabableElement(target),
            target.querySelector('[name="foo"] input'),
            "foo should be focused"
        );
    });

    QUnit.test("phone field with placeholder", async function (assert) {
        serverData.models.partner.fields.foo.default = false;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="foo" widget="phone" placeholder="Placeholder"/>
                        </group>
                    </sheet>
                </form>`,
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget[name='foo'] input").placeholder,
            "Placeholder"
        );
    });

    QUnit.test("unset and readonly PhoneField", async function (assert) {
        serverData.models.partner.fields.foo.default = false;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="foo" widget="phone" readonly="1" placeholder="Placeholder"/>
                        </group>
                    </sheet>
                </form>`,
        });
        assert.containsNone(
            target.querySelector(".o_field_widget[name='foo']"),
            "a",
            "The readonly field don't contain a link if no value is set"
        );
    });
});
