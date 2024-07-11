/** @odoo-module **/

import { click, getFixture } from "@web/../tests/helpers/utils";
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
            ".form-check.o_boolean_toggle",
            "Boolean toggle widget applied to boolean field"
        );
        assert.containsOnce(
            target,
            ".form-check.o_boolean_toggle input:checked",
            "Boolean toggle should be checked"
        );

        await click(target, ".o_field_widget[name='bar'] input");
        assert.containsOnce(
            target,
            ".form-check.o_boolean_toggle input:not(:checked)",
            "Boolean toggle shouldn't be checked"
        );
    });

    QUnit.test("readonly BooleanToggleField is disabled in edit mode", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="bar" widget="boolean_toggle" readonly="1" />
                </form>`,
        });

        assert.containsOnce(target, ".o_form_editable");
        assert.ok(target.querySelector(".o_boolean_toggle input").disabled);
    });

    QUnit.test("BooleanToggleField is not disabled in readonly mode", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="bar" widget="boolean_toggle"/></form>',
            resId: 1,
        });

        assert.containsOnce(target, ".o_form_editable");
        assert.containsOnce(target, ".form-check.o_boolean_toggle");
        assert.notOk(target.querySelector(".o_boolean_toggle input").disabled);
        assert.notOk(target.querySelector(".o_boolean_toggle input").checked);
        await click(target, ".o_field_widget[name='bar'] input");
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

        assert.containsOnce(target, ".form-check.o_boolean_toggle");
        assert.ok(target.querySelector(".o_boolean_toggle input").disabled);
    });

    QUnit.test("BooleanToggleField is enabled in edit mode", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="bar" widget="boolean_toggle"/></form>',
            resId: 1,
        });

        assert.containsOnce(target, ".form-check.o_boolean_toggle");

        assert.notOk(target.querySelector(".o_boolean_toggle input").disabled);
        assert.notOk(target.querySelector(".o_boolean_toggle input").checked);
        await click(target, ".o_field_widget[name='bar'] input");
        assert.notOk(target.querySelector(".o_boolean_toggle input").disabled);
        assert.ok(target.querySelector(".o_boolean_toggle input").checked);
    });

    QUnit.test("boolean toggle widget is not disabled in readonly mode", async function (assert) {
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
            ".form-check.o_boolean_toggle",
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
                ".form-check.o_boolean_toggle",
                "Boolean toggle widget applied to boolean field"
            );
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
            ".form-check.o_boolean_toggle",
            "Boolean toggle widget applied to boolean field"
        );
        assert.containsNone(target, ".o_boolean_toggle input:checked");

        await click(target, ".o_boolean_toggle");
        assert.containsOnce(target, ".o_boolean_toggle input:checked");
    });

    QUnit.test(
        "BooleanToggleField is disabled if readonly in editable list",
        async function (assert) {
            serverData.models.partner.fields.bar.readonly = true;

            await makeView({
                type: "list",
                serverData,
                resModel: "partner",
                arch: `
                    <tree editable="bottom">
                        <field name="bar" widget="boolean_toggle" />
                    </tree>
                `,
            });

            assert.containsOnce(
                target,
                ".o_boolean_toggle input:disabled",
                "field should be readonly"
            );
            assert.containsOnce(target, ".o_boolean_toggle input:not(:checked)");

            await click(target, ".o_boolean_toggle");
            assert.containsOnce(
                target,
                ".o_boolean_toggle input:disabled",
                "field should still be readonly"
            );
            assert.containsOnce(
                target,
                ".o_boolean_toggle input:not(:checked)",
                "should keep unchecked on cell click"
            );

            await click(target, ".o_boolean_toggle");
            assert.containsOnce(
                target,
                ".o_boolean_toggle input:not(:checked)",
                "should keep unchecked on click"
            );
        }
    );

    QUnit.test("BooleanToggleField - auto save record when field toggled", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="bar" widget="boolean_toggle" />
                </form>`,
            resId: 1,
            mockRPC(_route, { method }) {
                if (method === "web_save") {
                    assert.step("web_save");
                }
            },
        });
        await click(target, ".o_field_widget[name='bar'] input");
        assert.verifySteps(["web_save"]);
    });

    QUnit.test("BooleanToggleField - autosave option set to false", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="bar" widget="boolean_toggle" options="{'autosave': false}"/>
                </form>`,
            resId: 1,
            mockRPC(_route, { method }) {
                if (method === "web_save") {
                    assert.step("web_save");
                }
            },
        });
        await click(target, ".o_field_widget[name='bar'] input");
        assert.verifySteps([]);
    });
});
