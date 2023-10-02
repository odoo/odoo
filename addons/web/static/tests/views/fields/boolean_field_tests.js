/** @odoo-module **/

import {
    click,
    clickSave,
    getFixture,
    nextTick,
    triggerEvent,
    triggerEvents,
} from "@web/../tests/helpers/utils";
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
                </form>`,
        });

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
        await clickSave(target);
        assert.containsNone(
            target,
            ".o_field_boolean input:checked",
            "checkbox should still no longer be checked"
        );

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
        await click(target, ".o_form_view label:not(.form-check-label)");
        assert.containsOnce(
            target,
            ".o_field_boolean input:checked",
            "checkbox should now be checked"
        );

        // uncheck it back
        await click(target, ".o_form_view label:not(.form-check-label)");
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
        await clickSave(target);
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
                </tree>`,
        });

        assert.containsN(
            target,
            "tbody td:not(.o_list_record_selector) .o-checkbox input",
            5,
            "should have 5 checkboxes"
        );
        assert.containsN(
            target,
            "tbody td:not(.o_list_record_selector) .o-checkbox input:checked",
            4,
            "should have 4 checked input"
        );

        // Edit a line
        let cell = target.querySelector("tr.o_data_row td:not(.o_list_record_selector)");
        assert.ok(
            cell.querySelector(".o-checkbox input:checked").disabled,
            "input should be disabled in readonly mode"
        );
        await click(cell, ".o-checkbox");
        assert.hasClass(
            document.querySelector("tr.o_data_row:nth-child(1)"),
            "o_selected_row",
            "the row is now selected, in edition"
        );
        assert.ok(
            !cell.querySelector(".o-checkbox input:checked").disabled,
            "input should now be enabled"
        );
        await click(cell);
        assert.notOk(
            cell.querySelector(".o-checkbox input:checked").disabled,
            "input should not have the disabled property in edit mode"
        );
        await click(cell, ".o-checkbox");

        // save
        await clickSave(target);
        cell = target.querySelector("tr.o_data_row td:not(.o_list_record_selector)");
        assert.ok(
            cell.querySelector(".o-checkbox input:not(:checked)").disabled,
            "input should be disabled again"
        );
        assert.containsN(
            target,
            "tbody td:not(.o_list_record_selector) .o-checkbox",
            5,
            "should still have 5 checkboxes"
        );
        assert.containsN(
            target,
            "tbody td:not(.o_list_record_selector) .o-checkbox input:checked",
            3,
            "should now have only 3 checked input"
        );

        // Re-Edit the line and fake-check the checkbox
        await click(cell);
        await click(cell, ".o-checkbox");
        await click(cell, ".o-checkbox");

        // Save
        await clickSave(target);
        assert.containsN(
            target,
            "tbody td:not(.o_list_record_selector) .o-checkbox",
            5,
            "should still have 5 checkboxes"
        );
        assert.containsN(
            target,
            "tbody td:not(.o_list_record_selector) .o-checkbox input:checked",
            3,
            "should still have only 3 checked input"
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

        await click(target, ".o_field_boolean .o-checkbox");
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

    QUnit.test("onchange return value before toggle checkbox", async function (assert) {
        serverData.models.partner.onchanges = {
            bar(obj) {
                obj.bar = true;
            },
        };

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `<form><field name="bar"/></form>`,
        });

        assert.containsOnce(
            target,
            ".o_field_boolean input:checked",
            "checkbox should still be checked"
        );

        await click(target, ".o_field_boolean .o-checkbox");
        await nextTick();
        assert.containsOnce(
            target,
            ".o_field_boolean input:checked",
            "checkbox should still be checked"
        );
    });
});
