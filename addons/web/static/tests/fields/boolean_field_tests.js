/** @odoo-module **/

import { click, getFixture, nextTick, triggerEvent, triggerEvents } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
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
        await makeView({
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

        assert.containsOnce(target, ".o_field_boolean input:checked", "checkbox should be checked");
        assert.containsOnce(
            target,
            ".o_field_boolean input:disabled",
            "checkbox should be disabled"
        );

        // switch to edit mode and check the result
        await click(target, ".o_form_button_edit");
        assert.containsOnce(
            target,
            ".o_field_boolean input:checked",
            "checkbox should still be checked"
        );
        assert.containsNone(
            target,
            ".o_field_boolean input:disabled",
            "checkbox should not be disabled"
        );

        // uncheck the checkbox
        await click(target, ".o_field_boolean input:checked");
        assert.containsNone(
            target,
            ".o_field_boolean input:checked",
            "checkbox should no longer be checked"
        );

        // save
        await click(target, ".o_form_button_save");
        assert.containsNone(
            target,
            ".o_field_boolean input:checked",
            "checkbox should still no longer be checked"
        );

        // switch to edit mode and test the opposite change
        await click(target, ".o_form_button_edit");
        assert.containsNone(
            target,
            ".o_field_boolean input:checked",
            "checkbox should still be unchecked"
        );

        // check the checkbox
        await click(target, ".o_field_boolean input");
        assert.containsOnce(
            target,
            ".o_field_boolean input:checked",
            "checkbox should now be checked"
        );

        // uncheck it back
        await click(target, ".o_field_boolean input");
        assert.containsNone(
            target,
            ".o_field_boolean input:checked",
            "checkbox should now be unchecked"
        );

        // check the checkbox by clicking on label
        await click(target, ".o_form_view label:not(.custom-control-label)");
        assert.containsOnce(
            target,
            ".o_field_boolean input:checked",
            "checkbox should now be checked"
        );

        // uncheck it back
        await click(target, ".o_form_view label:not(.custom-control-label)");
        assert.containsNone(
            target,
            ".o_field_boolean input:checked",
            "checkbox should now be unchecked"
        );

        // check the checkbox by hitting the "enter" key after focusing it
        await triggerEvents(target, ".o_field_boolean input", [
            ["focusin"],
            ["keydown", { key: "Enter" }],
            ["keyup", { key: "Enter" }],
        ]);
        assert.containsOnce(
            target,
            ".o_field_boolean input:checked",
            "checkbox should now be checked"
        );

        // blindly press enter again, it should uncheck the checkbox
        await triggerEvent(document.activeElement, null, "keydown", { key: "Enter" });
        assert.containsNone(
            target,
            ".o_field_boolean input:checked",
            "checkbox should not be checked"
        );
        await nextTick();
        // blindly press enter again, it should check the checkbox back
        await triggerEvent(document.activeElement, null, "keydown", { key: "Enter" });
        assert.containsOnce(
            target,
            ".o_field_boolean input:checked",
            "checkbox should still be checked"
        );

        // save
        await click(target, ".o_form_button_save");
        assert.containsOnce(
            target,
            ".o_field_boolean input:checked",
            "checkbox should still be checked"
        );
    });

    QUnit.test("boolean field in editable list view", async function (assert) {
        await makeView({
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
            target,
            "tbody td:not(.o_list_record_selector) .custom-checkbox input",
            5,
            "should have 5 checkboxes"
        );
        assert.containsN(
            target,
            "tbody td:not(.o_list_record_selector) .custom-checkbox input:checked",
            4,
            "should have 4 checked input"
        );

        // Edit a line
        let cell = target.querySelector("tr.o_data_row td:not(.o_list_record_selector)");
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
        await click(target.querySelector(".o_list_button_save"));
        cell = target.querySelector("tr.o_data_row td:not(.o_list_record_selector)");
        assert.ok(
            cell.querySelector(".custom-checkbox input:not(:checked)").disabled,
            "input should be disabled again"
        );
        assert.containsN(
            target,
            "tbody td:not(.o_list_record_selector) .custom-checkbox input",
            5,
            "should still have 5 checkboxes"
        );
        assert.containsN(
            target,
            "tbody td:not(.o_list_record_selector) .custom-checkbox input:checked",
            3,
            "should now have only 3 checked input"
        );

        // Re-Edit the line and fake-check the checkbox
        await click(cell);
        await click(cell, ".custom-checkbox input");
        await click(cell, ".custom-checkbox input");

        // Save
        await click(target.querySelector(".o_list_button_save"));
        assert.containsN(
            target,
            "tbody td:not(.o_list_record_selector) .custom-checkbox input",
            5,
            "should still have 5 checkboxes"
        );
        assert.containsN(
            target,
            "tbody td:not(.o_list_record_selector) .custom-checkbox input:checked",
            3,
            "should still have only 3 checked input"
        );

        // Re-Edit the line to check the checkbox back but this time click on
        // the checkbox directly in readonly mode !
        cell = target.querySelector("tr.o_data_row td:not(.o_list_record_selector)");
        await click(cell, ".custom-checkbox input");

        assert.containsN(
            target,
            "tbody td:not(.o_list_record_selector) .custom-checkbox input",
            5,
            "should still have 5 checkboxes"
        );
        assert.containsN(
            target,
            "tbody td:not(.o_list_record_selector) .custom-checkbox input:checked",
            4,
            "should now have 4 checked input back"
        );
    });

    QUnit.test("readonly boolean field", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `<form><field name="bar" readonly="1"/></form>`,
        });
        assert.containsOnce(target, ".o_field_boolean input:checked", "checkbox should be checked");
        assert.containsOnce(
            target,
            ".o_field_boolean input:disabled",
            "checkbox should be disabled"
        );

        await click(target, ".o_form_button_edit");
        assert.containsOnce(
            target,
            ".o_field_boolean input:checked",
            "checkbox should still be checked"
        );
        assert.containsOnce(
            target,
            ".o_field_boolean input:disabled",
            "checkbox should still be disabled"
        );

        await click(target, ".o_field_boolean input");
        assert.containsOnce(
            target,
            ".o_field_boolean input:checked",
            "checkbox should still be checked"
        );
        assert.containsOnce(
            target,
            ".o_field_boolean input:disabled",
            "checkbox should still be disabled"
        );
    });
});
