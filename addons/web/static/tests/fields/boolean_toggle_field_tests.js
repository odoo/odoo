/** @odoo-module **/

import { click } from "../helpers/utils";
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
            form.el,
            ".custom-checkbox.o_boolean_toggle",
            "Boolean toggle widget applied to boolean field"
        );
        assert.containsOnce(
            form.el,
            ".custom-checkbox.o_boolean_toggle .fa-check-circle",
            "Boolean toggle should have fa-check-circle icon"
        );

        await click(form.el, ".o_field_widget[name='bar'] input");
        assert.containsOnce(
            form.el,
            ".custom-checkbox.o_boolean_toggle .fa-times-circle",
            "Boolean toggle should have fa-times-circle icon"
        );
    });
});
