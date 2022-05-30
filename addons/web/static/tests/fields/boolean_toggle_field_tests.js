/** @odoo-module **/

import { click, getFixture } from "../helpers/utils";
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
                </form>
            `,
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
                </form>
            `,
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

    QUnit.skipWOWL(
        "boolean toggle widget is not disabled in readonly mode",
        async function (assert) {
            // assert.expect(3);
            // const form = await createView({
            //     View: FormView,
            //     model: 'partner',
            //     data: this.data,
            //     arch: '<form><field name="bar" widget="boolean_toggle"/></form>',
            //     res_id: 5,
            // });
            // assert.containsOnce(form, ".custom-checkbox.o_boolean_toggle", "Boolean toggle widget applied to boolean field");
            // assert.notOk(form.$('.o_boolean_toggle input')[0].checked);
            // await testUtils.dom.click(form.$('.o_boolean_toggle'));
            // assert.ok(form.$('.o_boolean_toggle input')[0].checked);
            // form.destroy();
        }
    );

    QUnit.skipWOWL(
        "boolean toggle widget is disabled with a readonly attribute",
        async function (assert) {
            // assert.expect(3);
            // const form = await createView({
            //     View: FormView,
            //     model: 'partner',
            //     data: this.data,
            //     arch: '<form><field name="bar" widget="boolean_toggle" readonly="1"/></form>',
            //     res_id: 5,
            // });
            // assert.containsOnce(form, ".custom-checkbox.o_boolean_toggle", "Boolean toggle widget applied to boolean field");
            // await testUtils.dom.click(form.$buttons.find('.o_form_button_edit'));
            // assert.notOk(form.$('.o_boolean_toggle input')[0].checked);
            // await testUtils.dom.click(form.$('.o_boolean_toggle'));
            // assert.notOk(form.$('.o_boolean_toggle input')[0].checked);
            // form.destroy();
        }
    );

    QUnit.skipWOWL("boolean toggle widget is enabled in edit mode", async function (assert) {
        // assert.expect(3);
        // const form = await createView({
        //     View: FormView,
        //     model: 'partner',
        //     data: this.data,
        //     arch: '<form><field name="bar" widget="boolean_toggle"/></form>',
        //     res_id: 5,
        // });
        // assert.containsOnce(form, ".custom-checkbox.o_boolean_toggle", "Boolean toggle widget applied to boolean field");
        // await testUtils.dom.click(form.$buttons.find('.o_form_button_edit'));
        // assert.notOk(form.$('.o_boolean_toggle input')[0].checked);
        // await testUtils.dom.click(form.$('.o_boolean_toggle'));
        // assert.ok(form.$('.o_boolean_toggle input')[0].checked);
        // form.destroy();
    });
});
