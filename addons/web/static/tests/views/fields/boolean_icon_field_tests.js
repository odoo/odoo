/** @odoo-module **/

import { getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { click } from "../../helpers/utils";

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
                        barOff: {
                            string: "Bar Off",
                            type: "boolean",
                            default: true,
                            searchable: true,
                        },
                    },
                    records: [{ id: 1, bar: true, barOff: false }],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("BooleanIconField");

    QUnit.test("boolean_icon field in form view", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <label for="bar" string="Bar" />
                    <field name="bar" widget="boolean_icon" options="{'icon': 'fa-recycle'}" />
                    <field name="barOff" widget="boolean_icon" options="{'icon': 'fa-trash'}" />
                </form>`,
        });

        assert.containsN(target, ".o_field_boolean_icon button", 2, "icon buttons are visible");
        assert.strictEqual(
            target.querySelector("[name='bar'] button").dataset.tooltip,
            "Bar",
            "first button has the label as tooltip"
        );
        assert.hasClass(
            target.querySelector("[name='bar'] button"),
            "btn-primary",
            "active boolean button has the right class"
        );
        assert.hasClass(
            target.querySelector("[name='bar'] button"),
            "fa-recycle",
            "first button has the right icon"
        );
        assert.hasClass(
            target.querySelector("[name='barOff'] button"),
            "btn-outline-secondary",
            "inactive boolean button has the right class"
        );
        assert.hasClass(
            target.querySelector("[name='barOff'] button"),
            "fa-trash",
            "second button has the right icon"
        );

        await click(target.querySelector("[name='bar'] button"));
        assert.hasClass(
            target.querySelector("[name='bar'] button"),
            "btn-outline-secondary",
            "boolean button is now inactive"
        );
    });
});
