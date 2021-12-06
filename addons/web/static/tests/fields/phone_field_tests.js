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

    QUnit.module("PhoneField");

    QUnit.skip("PhoneField in form view on normal screens", async function (assert) {
        assert.expect(6);

        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="foo" widget="phone"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
            resId: 1,
            // config: {
            //     device: {
            //         size_class: config.device.SIZES.LG,
            //     },
            // },
        });

        var phone = form.el.querySelector("a.o-phone-field");
        assert.containsOnce(
            form,
            phone,
            "should have rendered the phone number as a link with correct classes"
        );
        assert.strictEqual(phone.innerText, "yop", "value should be displayed properly");
        assert.hasAttrValue(phone, "href", "tel:yop", "should have proper tel prefix");

        // switch to edit mode and check the result
        await click(form.el.querySelector(".o_form_button_edit"));
        assert.containsOnce(
            form,
            'input[type="phone"].o_field_widget',
            "should have an input for the phone field"
        );
        assert.strictEqual(
            form.el.querySelector('input[type="phone"].o_field_widget').value,
            "yop",
            "input should contain field value in edit mode"
        );

        // change value in edit mode
        const field = form.el.querySelector('input[type="phone"].o_field_widget');
        field.value = "new";
        await triggerEvent(field, null, "change");

        // save
        await click(form.el.querySelector(".o_form_button_save"));
        assert.strictEqual(
            form.el.querySelector("a.o-phone-field").innerText,
            "new",
            "new value should be displayed properly"
        );
    });

    QUnit.skip("PhoneField in editable list view on normal screens", async function (assert) {
        assert.expect(8);

        var list = await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: '<tree editable="bottom"><field name="foo" widget="phone"/></tree>',
            // config: {
            //     device: {
            //         size_class: config.device.SIZES.LG,
            //     },
            // },
        });

        assert.containsN(list, "tbody td:not(.o_list_record_selector)", 5);
        assert.strictEqual(
            list.el.querySelector("tbody td:not(.o_list_record_selector) a").innerText,
            "yop",
            "value should be displayed properly with a link to send SMS"
        );

        assert.containsN(
            list,
            "a.o_field_widget.o_form_uri.o-phone-field",
            5,
            "should have the correct classnames"
        );

        // Edit a line and check the result
        var cell = list.el.querySelector("tbody td:not(.o_list_record_selector)");
        await click(cell);
        assert.hasClass(cell.parent(), "o_selected_row", "should be set as edit mode");
        assert.strictEqual(
            cell.find("input").value,
            "yop",
            "should have the corect value in internal input"
        );
        const inputField = cell.querySelector("input");
        inputField.value = "new";
        await triggerEvent(inputField, null, "change");

        // save
        await click(form.el.querySelector(".o_form_button_save"));
        cell = list.el.querySelector("tbody td:not(.o_list_record_selector)");
        assert.doesNotHaveClass(
            cell.parentElement,
            "o_selected_row",
            "should not be in edit mode anymore"
        );
        assert.strictEqual(
            list.el.querySelector("tbody td:not(.o_list_record_selector) a").innerText,
            "new",
            "value should be properly updated"
        );
        assert.containsN(
            list,
            "a.o_field_widget.o_form_uri.o-phone-field",
            5,
            "should still have links with correct classes"
        );
    });

    QUnit.skip("use TAB to navigate to a PhoneField", async function (assert) {
        assert.expect(2);

        const form = await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch:
                '<form string="Partners">' +
                "<sheet>" +
                "<group>" +
                '<field name="display_name"/>' +
                '<field name="foo" widget="phone"/>' +
                "</group>" +
                "</sheet>" +
                "</form>",
        });
        await click(form.el.querySelector("input[name=display_name]"));
        assert.strictEqual(
            document.activeElement,
            form.el.querySelector('input[name="display_name"]'),
            "display_name should be focused"
        );
        await triggerEvent(form.el, 'input[name="display_name"]', "keydown", {
            key: "Tab",
        });
        assert.strictEqual(
            document.activeElement,
            form.el.querySelector('input[name="foo"]'),
            "foo should be focused"
        );
    });
});
