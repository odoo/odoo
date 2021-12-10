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
                        currency_id: {
                            string: "Currency",
                            type: "many2one",
                            relation: "currency",
                            searchable: true,
                        },
                        monetary: { string: "Monetary", type: "monetary" },
                    },
                    records: [
                        {
                            id: 1,
                            foo: "yop",
                            int_field: 10,
                            qux: 0.44444,
                            currency_id: 1,
                            monetary: 9.999999,
                        },
                    ],
                },
                currency: {
                    fields: {
                        digits: { string: "Digits" },
                        symbol: { string: "Currency Sumbol", type: "char", searchable: true },
                        position: { string: "Currency Position", type: "char", searchable: true },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "$",
                            symbol: "$",
                            position: "before",
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
        assert.expect(2);

        const form = await makeView({
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
                </form>
            `,
        });

        // formatFloat renders according to this.field.digits
        assert.strictEqual(
            form.el.querySelectorAll(".oe_stat_button .o_field_widget.o_stat_info .o_stat_value")[0]
                .textContent,
            "0.4",
            "Default precision should be [16,1]"
        );
        assert.strictEqual(
            form.el.querySelectorAll(".oe_stat_button .o_field_widget.o_stat_info .o_stat_value")[1]
                .textContent,
            "10.00",
            "Currency decimal precision should be 2"
        );
    });

    QUnit.test("StatInfoField in form view", async function (assert) {
        assert.expect(9);

        const form = await makeView({
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
                </form>
            `,
        });

        assert.containsOnce(
            form.el,
            ".oe_stat_button .o_field_widget.o_stat_info",
            "should have one stat button"
        );
        assert.strictEqual(
            form.el.querySelector(".oe_stat_button .o_field_widget.o_stat_info .o_stat_value")
                .textContent,
            "10",
            "should have 10 as value"
        );
        assert.strictEqual(
            form.el.querySelector(".oe_stat_button .o_field_widget.o_stat_info .o_stat_text")
                .textContent,
            "int_field",
            "should have 'int_field' as text"
        );

        // switch to edit mode and check the result
        await click(form.el, ".o_form_button_edit");
        assert.containsOnce(
            form.el,
            ".oe_stat_button .o_field_widget.o_stat_info",
            "should still have one stat button"
        );
        assert.strictEqual(
            form.el.querySelector(".oe_stat_button .o_field_widget.o_stat_info .o_stat_value")
                .textContent,
            "10",
            "should still have 10 as value"
        );
        assert.strictEqual(
            form.el.querySelector(".oe_stat_button .o_field_widget.o_stat_info .o_stat_text")
                .textContent,
            "int_field",
            "should have 'int_field' as text"
        );

        // save
        await click(form.el, ".o_form_button_save");
        assert.containsOnce(
            form.el,
            ".oe_stat_button .o_field_widget.o_stat_info",
            "should have one stat button"
        );
        assert.strictEqual(
            form.el.querySelector(".oe_stat_button .o_field_widget.o_stat_info .o_stat_value")
                .textContent,
            "10",
            "should have 10 as value"
        );
        assert.strictEqual(
            form.el.querySelector(".oe_stat_button .o_field_widget.o_stat_info .o_stat_text")
                .textContent,
            "int_field",
            "should have 'int_field' as text"
        );
    });

    QUnit.test("StatInfoField in form view with specific label_field", async function (assert) {
        assert.expect(9);

        const form = await makeView({
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
                </form>
            `,
        });

        assert.containsOnce(
            form,
            ".oe_stat_button .o_field_widget.o_stat_info",
            "should have one stat button"
        );
        assert.strictEqual(
            form.el.querySelector(".oe_stat_button .o_field_widget.o_stat_info .o_stat_value")
                .textContent,
            "10",
            "should have 10 as value"
        );
        assert.strictEqual(
            form.el.querySelector(".oe_stat_button .o_field_widget.o_stat_info .o_stat_text")
                .textContent,
            "yop",
            "should have 'yop' as text, since it is the value of field foo"
        );

        // switch to edit mode and check the result
        await click(form.el, ".o_form_button_edit");
        assert.containsOnce(
            form,
            ".oe_stat_button .o_field_widget.o_stat_info",
            "should still have one stat button"
        );
        assert.strictEqual(
            form.el.querySelector(".oe_stat_button .o_field_widget.o_stat_info .o_stat_value")
                .textContent,
            "10",
            "should still have 10 as value"
        );
        assert.strictEqual(
            form.el.querySelector(".oe_stat_button .o_field_widget.o_stat_info .o_stat_text")
                .textContent,
            "yop",
            "should have 'yop' as text, since it is the value of field foo"
        );

        // save
        await click(form.el, ".o_form_button_save");
        assert.containsOnce(
            form,
            ".oe_stat_button .o_field_widget.o_stat_info",
            "should have one stat button"
        );
        assert.strictEqual(
            form.el.querySelector(".oe_stat_button .o_field_widget.o_stat_info .o_stat_value")
                .textContent,
            "10",
            "should have 10 as value"
        );
        assert.strictEqual(
            form.el.querySelector(".oe_stat_button .o_field_widget.o_stat_info .o_stat_text")
                .textContent,
            "yop",
            "should have 'yop' as text, since it is the value of field foo"
        );
    });

    QUnit.test("StatInfoField in form view with no label", async function (assert) {
        assert.expect(9);

        const form = await makeView({
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
                </form>
            `,
        });

        assert.containsOnce(
            form,
            ".oe_stat_button .o_field_widget.o_stat_info",
            "should have one stat button"
        );
        assert.strictEqual(
            form.el.querySelector(".oe_stat_button .o_field_widget.o_stat_info .o_stat_value")
                .textContent,
            "10",
            "should have 10 as value"
        );
        assert.containsNone(
            form.el,
            ".oe_stat_button .o_field_widget.o_stat_info .o_stat_text",
            "should not have any label"
        );

        // switch to edit mode and check the result
        await click(form.el, ".o_form_button_edit");
        assert.containsOnce(
            form,
            ".oe_stat_button .o_field_widget.o_stat_info",
            "should still have one stat button"
        );
        assert.strictEqual(
            form.el.querySelector(".oe_stat_button .o_field_widget.o_stat_info .o_stat_value")
                .textContent,
            "10",
            "should still have 10 as value"
        );
        assert.containsNone(
            form.el,
            ".oe_stat_button .o_field_widget.o_stat_info .o_stat_text",
            "should not have any label"
        );

        // save
        await click(form.el, ".o_form_button_save");
        assert.containsOnce(
            form,
            ".oe_stat_button .o_field_widget.o_stat_info",
            "should have one stat button"
        );
        assert.strictEqual(
            form.el.querySelector(".oe_stat_button .o_field_widget.o_stat_info .o_stat_value")
                .textContent,
            "10",
            "should have 10 as value"
        );
        assert.containsNone(
            form.el,
            ".oe_stat_button .o_field_widget.o_stat_info .o_stat_text",
            "should not have any label"
        );
    });
});
