/** @odoo-module **/

import { click, nextTick, triggerEvent, triggerEvents } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

let serverData;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        bar: { string: "Bar", type: "boolean", default: true, searchable: true },
                    },
                    records: [
                        { id: 1, bar: true },
                        { id: 2, bar: true },
                        { id: 3, bar: true },
                        { id: 4, bar: true },
                        { id: 5, bar: false },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("BooleanField");

    QUnit.test("boolean field in form view", async function (assert) {
        assert.expect(15);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <label for="bar" string="Awesome checkbox" />
                    <field name="bar" />
                </form>
            `,
        });

        assert.containsOnce(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should be checked"
        );
        assert.containsOnce(
            form.el,
            ".o_field_boolean input:disabled",
            "checkbox should be disabled"
        );

        // switch to edit mode and check the result
        await click(form.el, ".o_form_button_edit");
        assert.containsOnce(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should still be checked"
        );
        assert.containsNone(
            form.el,
            ".o_field_boolean input:disabled",
            "checkbox should not be disabled"
        );

        // uncheck the checkbox
        await click(form.el, ".o_field_boolean input:checked");
        assert.containsNone(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should no longer be checked"
        );

        // save
        await click(form.el, ".o_form_button_save");
        assert.containsNone(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should still no longer be checked"
        );

        // switch to edit mode and test the opposite change
        await click(form.el, ".o_form_button_edit");
        assert.containsNone(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should still be unchecked"
        );

        // check the checkbox
        await click(form.el, ".o_field_boolean input");
        assert.containsOnce(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should now be checked"
        );

        // uncheck it back
        await click(form.el, ".o_field_boolean input");
        assert.containsNone(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should now be unchecked"
        );

        // check the checkbox by clicking on label
        await click(form.el, ".o_form_view label:not(.custom-control-label)");
        assert.containsOnce(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should now be checked"
        );

        // uncheck it back
        await click(form.el, ".o_form_view label:not(.custom-control-label)");
        assert.containsNone(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should now be unchecked"
        );

        // check the checkbox by hitting the "enter" key after focusing it
        await triggerEvents(form.el, ".o_field_boolean input", [
            ["focusin"],
            ["keydown", { key: "Enter" }],
            ["keyup", { key: "Enter" }],
        ]);
        assert.containsOnce(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should now be checked"
        );

        // blindly press enter again, it should uncheck the checkbox
        await triggerEvent(document.activeElement, null, "keydown", { key: "Enter" });
        assert.containsNone(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should not be checked"
        );
        await nextTick();
        // blindly press enter again, it should check the checkbox back
        await triggerEvent(document.activeElement, null, "keydown", { key: "Enter" });
        assert.containsOnce(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should still be checked"
        );

        // save
        await click(form.el, ".o_form_button_save");
        assert.containsOnce(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should still be checked"
        );
    });

    QUnit.skip("boolean field in editable list view", async function (assert) {
        assert.expect(11);

        const list = await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="bar" />
                </tree>
            `,
        });

        assert.containsN(
            list.el,
            "tbody td:not(.o_list_record_selector) .custom-checkbox input",
            5,
            "should have 5 checkboxes"
        );
        assert.containsN(
            list.el,
            "tbody td:not(.o_list_record_selector) .custom-checkbox input:checked",
            4,
            "should have 4 checked input"
        );

        // Edit a line
        let cell = list.el.querySelector("tr.o_data_row td:not(.o_list_record_selector)");
        assert.ok(
            cell.querySelector(".custom-checkbox input:checked").disabled,
            "input should be disabled in readonly mode"
        );
        await click(cell);
        assert.notOk(
            cell.querySelector(".custom-checkbox input:checked").disabled,
            "input should not have the disabled property in edit mode"
        );
        await click(cell, ".custom-checkbox input:checked");

        // save
        await click(list.el.querySelector(".o_list_button_save"));
        cell = list.el.querySelector("tr.o_data_row td:not(.o_list_record_selector)");
        assert.ok(
            cell.querySelector(".custom-checkbox input:not(:checked)").disabled,
            "input should be disabled again"
        );
        assert.containsN(
            list.el,
            "tbody td:not(.o_list_record_selector) .custom-checkbox input",
            5,
            "should still have 5 checkboxes"
        );
        assert.containsN(
            list.el,
            "tbody td:not(.o_list_record_selector) .custom-checkbox input:checked",
            3,
            "should now have only 3 checked input"
        );

        // Re-Edit the line and fake-check the checkbox
        await click(cell);
        await click(cell, ".custom-checkbox input");
        await click(cell, ".custom-checkbox input");

        // Save
        await click(list.el.querySelector(".o_list_button_save"));
        assert.containsN(
            list.el,
            "tbody td:not(.o_list_record_selector) .custom-checkbox input",
            5,
            "should still have 5 checkboxes"
        );
        assert.containsN(
            list.el,
            "tbody td:not(.o_list_record_selector) .custom-checkbox input:checked",
            3,
            "should still have only 3 checked input"
        );

        // Re-Edit the line to check the checkbox back but this time click on
        // the checkbox directly in readonly mode !
        cell = list.el.querySelector("tr.o_data_row td:not(.o_list_record_selector)");
        await click(cell, ".custom-checkbox .custom-control-label");
        await nextTick();

        assert.containsN(
            list.el,
            "tbody td:not(.o_list_record_selector) .custom-checkbox input",
            5,
            "should still have 5 checkboxes"
        );
        assert.containsN(
            list.el,
            "tbody td:not(.o_list_record_selector) .custom-checkbox input:checked",
            4,
            "should now have 4 checked input back"
        );
    });

    QUnit.test("readonly boolean field", async function (assert) {
        assert.expect(6);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                        <field name="bar" readonly="1"/>
                </form>
            `,
        });

        assert.containsOnce(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should be checked"
        );
        assert.containsOnce(
            form.el,
            ".o_field_boolean input:disabled",
            "checkbox should be disabled"
        );

        await click(form.el, ".o_form_button_edit");
        assert.containsOnce(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should still be checked"
        );
        assert.containsOnce(
            form.el,
            ".o_field_boolean input:disabled",
            "checkbox should still be disabled"
        );

        await click(form.el, ".o_field_boolean label");
        assert.containsOnce(
            form.el,
            ".o_field_boolean input:checked",
            "checkbox should still be checked"
        );
        assert.containsOnce(
            form.el,
            ".o_field_boolean input:disabled",
            "checkbox should still be disabled"
        );
    });
});
