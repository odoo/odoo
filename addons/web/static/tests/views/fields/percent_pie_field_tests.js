/** @odoo-module **/

import { getFixture } from "@web/../tests/helpers/utils";
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
                        foo: {
                            string: "Foo",
                            type: "char",
                            default: "My little Foo Value",
                            searchable: true,
                            trim: true,
                        },
                        int_field: {
                            string: "int_field",
                            type: "integer",
                            sortable: true,
                            searchable: true,
                        },
                    },
                    records: [
                        { id: 1, foo: "yop", int_field: 10 },
                        { id: 2, foo: "gnap", int_field: 80 },
                    ],
                    onchanges: {},
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("PercentPieField");

    QUnit.test("PercentPieField in form view with value < 50%", async function (assert) {
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="int_field" widget="percentpie"/>
                        </group>
                    </sheet>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(
            target,
            ".o_field_percent_pie.o_field_widget .o_pie",
            "should have a pie chart"
        );
        assert.strictEqual(
            target.querySelector(".o_field_percent_pie.o_field_widget .o_pie_info .o_pie_value")
                .textContent,
            "10%",
            "should have 10% as pie value since int_field=10"
        );
        assert.strictEqual(
            target
                .querySelector(".o_field_percent_pie.o_field_widget .o_pie")
                .style.background.replaceAll(/\s+/g, " "),
            "conic-gradient( var(--PercentPieField-color-active) 0% 10%, var(--PercentPieField-color-static) 0% 100% )",
            "pie should have a background computed for its value of 10%"
        );
    });

    QUnit.test("PercentPieField in form view with value > 50%", async function (assert) {
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="int_field" widget="percentpie"/>
                        </group>
                    </sheet>
                </form>`,
            resId: 2,
        });

        assert.containsOnce(
            target,
            ".o_field_percent_pie.o_field_widget .o_pie",
            "should have a pie chart"
        );
        assert.strictEqual(
            target.querySelector(".o_field_percent_pie.o_field_widget .o_pie_info .o_pie_value")
                .textContent,
            "80%",
            "should have 80% as pie value since int_field=80"
        );
        assert.strictEqual(
            target
                .querySelector(".o_field_percent_pie.o_field_widget .o_pie")
                .style.background.replaceAll(/\s+/g, " "),
            "conic-gradient( var(--PercentPieField-color-active) 0% 80%, var(--PercentPieField-color-static) 0% 100% )",
            "pie should have a background computed for its value of 80%"
        );
    });
});
