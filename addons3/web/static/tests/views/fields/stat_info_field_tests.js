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
                        qux: { string: "Qux", type: "float", digits: [16, 1], searchable: true },
                        monetary: { string: "Monetary", type: "monetary" },
                    },
                    records: [
                        {
                            id: 1,
                            foo: "yop",
                            int_field: 10,
                            qux: 0.44444,
                            monetary: 9.999999,
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("StatInfoField");

    QUnit.test("StatInfoField formats decimal precision", async function (assert) {
        // sometimes the round method can return numbers such as 14.000001
        // when asked to round a number to 2 decimals, as such is the behaviour of floats.
        // we check that even in that eventuality, only two decimals are displayed
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <button class="oe_stat_button" name="items" icon="fa-gear">
                        <field name="qux" widget="statinfo" />
                    </button>
                    <button class="oe_stat_button" name="money" icon="fa-money">
                        <field name="monetary" widget="statinfo" />
                    </button>
                </form>`,
        });

        // formatFloat renders according to this.field.digits
        assert.strictEqual(
            target.querySelectorAll(".oe_stat_button .o_field_widget .o_stat_value")[0].textContent,
            "0.4",
            "Default precision should be [16,1]"
        );
        assert.strictEqual(
            target.querySelectorAll(".oe_stat_button .o_field_widget .o_stat_value")[1].textContent,
            "10.00",
            "Currency decimal precision should be 2"
        );
    });

    QUnit.test("StatInfoField in form view", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <div class="oe_button_box" name="button_box">
                        <button class="oe_stat_button" name="items" type="object" icon="fa-gear">
                            <field name="int_field" widget="statinfo" />
                        </button>
                    </div>
                </form>`,
        });

        assert.containsOnce(
            target,
            ".oe_stat_button .o_field_widget .o_stat_info",
            "should have one stat button"
        );
        assert.strictEqual(
            target.querySelector(".oe_stat_button .o_field_widget .o_stat_value").textContent,
            "10",
            "should have 10 as value"
        );
        assert.strictEqual(
            target.querySelector(".oe_stat_button .o_field_widget .o_stat_text").textContent,
            "int_field",
            "should have 'int_field' as text"
        );
    });

    QUnit.test("StatInfoField in form view with specific label_field", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <div class="oe_button_box" name="button_box">
                            <button class="oe_stat_button" name="items" type="object" icon="fa-gear">
                                <field string="Useful stat button" name="int_field" widget="statinfo" options="{'label_field': 'foo'}" />
                            </button>
                        </div>
                        <group>
                            <field name="foo" invisible="1" />
                        </group>
                    </sheet>
                </form>`,
        });

        assert.containsOnce(
            target,
            ".oe_stat_button .o_field_widget .o_stat_info",
            "should have one stat button"
        );
        assert.strictEqual(
            target.querySelector(".oe_stat_button .o_field_widget .o_stat_value").textContent,
            "10",
            "should have 10 as value"
        );
        assert.strictEqual(
            target.querySelector(".oe_stat_button .o_field_widget .o_stat_text").textContent,
            "yop",
            "should have 'yop' as text, since it is the value of field foo"
        );
    });

    QUnit.test("StatInfoField in form view with no label", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <div class="oe_button_box" name="button_box">
                            <button class="oe_stat_button" name="items" type="object" icon="fa-gear">
                                <field string="Useful stat button" name="int_field" widget="statinfo" nolabel="1" />
                            </button>
                        </div>
                    </sheet>
                </form>`,
        });
        assert.containsOnce(
            target,
            ".oe_stat_button .o_field_widget .o_stat_info",
            "should have one stat button"
        );
        assert.strictEqual(
            target.querySelector(".oe_stat_button .o_field_widget .o_stat_value").textContent,
            "10",
            "should have 10 as value"
        );
        assert.containsNone(
            target,
            ".oe_stat_button .o_field_widget .o_stat_text",
            "should not have any label"
        );
    });
});
