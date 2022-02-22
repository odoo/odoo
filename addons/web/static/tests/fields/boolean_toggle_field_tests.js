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
                    records: [],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("BooleanToggleField");

    QUnit.test("use BooleanToggleField in form view", async function (assert) {
        assert.expect(3);

        const form = await makeView({
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

    QUnit.test("readonly switch", async function (assert) {
        assert.expect(2);

        const form = await makeView({
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
});
