/** @odoo-module **/

import { localization } from "@web/core/l10n/localization";
import { defaultLocalization } from "@web/../tests/helpers/mock_services";
import {
    click,
    clickSave,
    editInput,
    getFixture,
    patchWithCleanup,
    triggerEvent,
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
                        int_field: {
                            string: "int_field",
                            type: "integer",
                        },
                    },
                    records: [
                        { id: 1, int_field: 10 },
                        { id: 2, int_field: false },
                        { id: 3, int_field: 8069 },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("IntegerField");

    QUnit.test("should be 0 when unset", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 2,
            arch: '<form><field name="int_field"/></form>',
        });

        assert.doesNotHaveClass(
            target.querySelector(".o_field_widget"),
            "o_field_empty",
            "Non-set integer field should be recognized as 0."
        );

        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "0",
            "Non-set integer field should be recognized as 0."
        );
    });

    QUnit.test("basic form view flow", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: '<form><field name="int_field"/></form>',
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=int_field] input").value,
            "10",
            "The value should be rendered correctly in edit mode."
        );

        await editInput(target, ".o_field_widget[name=int_field] input", "30");

        assert.strictEqual(
            target.querySelector(".o_field_widget[name=int_field] input").value,
            "30",
            "The value should be correctly displayed in the input."
        );

        await clickSave(target);
        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "30",
            "The new value should be saved and displayed properly."
        );
    });

    QUnit.test("rounded when using formula in form view", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: '<form><field name="int_field"/></form>',
        });

        await editInput(target, ".o_field_widget[name=int_field] input", "=100/3");
        await clickSave(target);

        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "33",
            "The new value should be calculated properly."
        );
    });

    QUnit.test("with input type 'number' option", async function (assert) {
        patchWithCleanup(localization, { ...defaultLocalization, grouping: [3, 0] });

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `<form><field name="int_field" options="{'type': 'number'}"/></form>`,
        });

        assert.ok(
            target.querySelector(".o_field_widget input").hasAttribute("type"),
            "Integer field with option type must have a type attribute."
        );

        assert.hasAttrValue(
            target.querySelector(".o_field_widget input"),
            "type",
            "number",
            'Integer field with option type must have a type attribute equals to "number".'
        );

        await editInput(target, ".o_field_widget[name=int_field] input", "1234567890");
        await clickSave(target);

        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "1234567890",
            "Integer value must be not formatted if input type is number."
        );
    });

    QUnit.test("with 'step' option", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `<form><field name="int_field" options="{'type': 'number', 'step': 3}"/></form>`,
        });

        assert.ok(
            target.querySelector(".o_field_widget input").hasAttribute("step"),
            "Integer field with option type must have a step attribute."
        );
        assert.hasAttrValue(
            target.querySelector(".o_field_widget input"),
            "step",
            "3",
            'Integer field with option type must have a step attribute equals to "3".'
        );
    });

    QUnit.test("without input type option", async function (assert) {
        patchWithCleanup(localization, { ...defaultLocalization, grouping: [3, 0] });

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: '<form><field name="int_field"/></form>',
        });

        assert.hasAttrValue(
            target.querySelector(".o_field_widget input"),
            "type",
            "text",
            "Integer field without option type must have a text type (default type)."
        );

        await editInput(target, ".o_field_widget[name=int_field] input", "1234567890");
        await clickSave(target);

        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "1,234,567,890",
            "Integer value must be formatted if input type isn't number."
        );
    });

    QUnit.test("with disable formatting option", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 3,
            arch: `<form><field name="int_field"  options="{'format': 'false'}"/></form>`,
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "8069",
            "Integer value must not be formatted"
        );
    });

    QUnit.test("IntegerField is formatted by default", async function (assert) {
        patchWithCleanup(localization, { ...defaultLocalization, grouping: [3, 0] });

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 3,
            arch: '<form><field name="int_field"/></form>',
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget input").value,
            "8,069",
            "Integer value must be formatted by default"
        );
    });

    QUnit.test("basic flow in editable list view", async function (assert) {
        await makeView({
            serverData,
            type: "list",
            resModel: "partner",
            arch: '<tree editable="bottom"><field name="int_field"/></tree>',
        });
        var zeroValues = Array.from(target.querySelectorAll("td")).filter(
            (el) => el.textContent === "0"
        );
        assert.strictEqual(
            zeroValues.length,
            1,
            "Unset integer values should not be rendered as zeros."
        );

        // switch to edit mode
        var cell = target.querySelector("tr.o_data_row td:not(.o_list_record_selector)");
        await click(cell);

        assert.containsOnce(
            target,
            '.o_field_widget[name="int_field"] input',
            "The view should have 1 input for editable integer."
        );

        await editInput(target, ".o_field_widget[name=int_field] input", "-28");
        assert.strictEqual(
            target.querySelector('.o_field_widget[name="int_field"] input').value,
            "-28",
            "The value should be displayed properly in the input."
        );

        await click(target.querySelector(".o_list_button_save"));
        assert.strictEqual(
            target.querySelector("td:not(.o_list_record_selector)").textContent,
            "-28",
            "The new value should be saved and displayed properly."
        );
    });

    QUnit.test("IntegerField field with placeholder", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="int_field" placeholder="Placeholder"/></form>`,
        });

        const input = target.querySelector(".o_field_widget[name='int_field'] input");
        input.value = "";
        await triggerEvent(input, null, "input");
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='int_field'] input").placeholder,
            "Placeholder"
        );
    });
});
