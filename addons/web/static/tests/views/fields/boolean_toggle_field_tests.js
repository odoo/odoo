/** @odoo-module **/

import { click, clickEdit, getFixture } from "@web/../tests/helpers/utils";
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
                    records: [{ id: 1, bar: false }],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("BooleanToggleField");

    QUnit.test("use BooleanToggleField in form view", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="bar" widget="boolean_toggle" />
                </form>`,
        });

        assert.containsOnce(
            target,
            ".custom-checkbox.o_boolean_toggle",
            "Boolean toggle widget applied to boolean field"
        );
        assert.containsOnce(
            target,
            ".custom-checkbox.o_boolean_toggle .fa-check-circle",
            "Boolean toggle should have fa-check-circle icon"
        );

        await click(target, ".o_field_widget[name='bar'] input");
        assert.containsOnce(
            target,
            ".custom-checkbox.o_boolean_toggle .fa-times-circle",
            "Boolean toggle should have fa-times-circle icon"
        );
    });

    QUnit.test("readonly BooleanToggleField is not disabled in edit mode", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="bar" widget="boolean_toggle" readonly="1" />
                </form>`,
        });

        assert.containsOnce(target, ".o_boolean_toggle input:disabled:checked");

        await click(target, ".o_field_widget[name='bar'] label");

        assert.containsOnce(target, ".o_boolean_toggle input:disabled:checked");
    });

    QUnit.test("BooleanToggleField is not disabled in readonly mode", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="bar" widget="boolean_toggle"/></form>',
            resId: 1,
        });

        assert.containsOnce(target, ".custom-checkbox.o_boolean_toggle");
        assert.notOk(target.querySelector(".o_boolean_toggle input").checked);
        await click(target, ".o_field_widget[name='bar'] label");
        assert.ok(target.querySelector(".o_boolean_toggle input").checked);
    });

    QUnit.test("BooleanToggleField is disabled with a readonly attribute", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="bar" widget="boolean_toggle" readonly="1"/></form>',
            resId: 1,
        });

        assert.containsOnce(target, ".custom-checkbox.o_boolean_toggle");
        await click(target.querySelector(".o_form_button_edit"));
        assert.notOk(target.querySelector(".o_boolean_toggle input").checked);
        await click(target, ".o_field_widget[name='bar'] label");
        assert.notOk(target.querySelector(".o_boolean_toggle input").checked);
    });

    QUnit.test("BooleanToggleField is enabled in edit mode", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="bar" widget="boolean_toggle"/></form>',
            resId: 1,
        });

        assert.containsOnce(target, ".custom-checkbox.o_boolean_toggle");
        await click(target.querySelector(".o_form_button_edit"));

        assert.notOk(target.querySelector(".o_boolean_toggle input").checked);
        await click(target, ".o_field_widget[name='bar'] label");
        assert.ok(target.querySelector(".o_boolean_toggle input").checked);
    });

    QUnit.test("boolean toggle widget is not disabled in readonly mode", async function (assert) {
        assert.expect(3);

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `
                    <form>
                        <field name="bar" widget="boolean_toggle" />
                    </form>`,
        });

        assert.containsOnce(
            target,
            ".custom-checkbox.o_boolean_toggle",
            "Boolean toggle widget applied to boolean field"
        );
        assert.containsNone(target, ".o_boolean_toggle input:checked");

        await click(target, ".o_boolean_toggle");
        assert.containsOnce(target, ".o_boolean_toggle input:checked");
    });

    QUnit.test(
        "boolean toggle widget is disabled with a readonly attribute",
        async function (assert) {
            assert.expect(3);

            await makeView({
                type: "form",
                serverData,
                resModel: "partner",
                resId: 1,
                arch: `
                    <form>
                        <field name="bar" widget="boolean_toggle" readonly="1" />
                    </form>`,
            });

            assert.containsOnce(
                target,
                ".custom-checkbox.o_boolean_toggle",
                "Boolean toggle widget applied to boolean field"
            );

            await clickEdit(target);
            assert.containsNone(target, ".o_boolean_toggle input:checked");

            await click(target, ".o_boolean_toggle");
            assert.containsNone(target, ".o_boolean_toggle input:checked");
        }
    );

    QUnit.test("boolean toggle widget is enabled in edit mode", async function (assert) {
        assert.expect(3);

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `
                <form>
                    <field name="bar" widget="boolean_toggle" />
                </form>`,
        });

        assert.containsOnce(
            target,
            ".custom-checkbox.o_boolean_toggle",
            "Boolean toggle widget applied to boolean field"
        );

        await clickEdit(target);
        assert.containsNone(target, ".o_boolean_toggle input:checked");

        await click(target, ".o_boolean_toggle");
        assert.containsOnce(target, ".o_boolean_toggle input:checked");
    });
});
