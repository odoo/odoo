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
            target.querySelector(".o_field_percent_pie.o_field_widget .o_pie .o_pie_value")
                .textContent,
            "10%",
            "should have 10% as pie value since int_field=10"
        );
        assert.strictEqual(
            target.querySelector(".o_field_percent_pie.o_field_widget .o_pie .o_mask").style
                .transform,
            "rotate(180deg)",
            "left mask should be covering the whole left side of the pie"
        );
        assert.strictEqual(
            target.querySelectorAll(".o_field_percent_pie.o_field_widget .o_pie .o_mask")[1].style
                .transform,
            "rotate(36deg)",
            "right mask should be rotated from 360*(10/100) = 36 degrees"
        );

        // switch to edit mode and check the result
        await click(target.querySelector(".o_form_button_edit"));
        assert.containsOnce(
            target,
            ".o_field_percent_pie.o_field_widget .o_pie",
            "should have a pie chart"
        );
        assert.strictEqual(
            target.querySelector(".o_field_percent_pie.o_field_widget .o_pie .o_pie_value")
                .textContent,
            "10%",
            "should have 10% as pie value since int_field=10"
        );
        assert.ok(
            _.str.include(
                target.querySelector(".o_field_percent_pie.o_field_widget .o_pie .o_mask").style
                    .transform,
                "rotate(180deg)"
            ),
            "left mask should be covering the whole left side of the pie"
        );
        assert.ok(
            _.str.include(
                target.querySelectorAll(".o_field_percent_pie.o_field_widget .o_pie .o_mask")[1]
                    .style.transform,
                "rotate(36deg)"
            ),
            "right mask should be rotated from 360*(10/100) = 36 degrees"
        );

        // save
        await click(target.querySelector(".o_form_button_save"));
        assert.containsOnce(
            target,
            ".o_field_percent_pie.o_field_widget .o_pie",
            "should have a pie chart"
        );
        assert.strictEqual(
            target.querySelector(".o_field_percent_pie.o_field_widget .o_pie .o_pie_value")
                .textContent,
            "10%",
            "should have 10% as pie value since int_field=10"
        );
        assert.strictEqual(
            target.querySelector(".o_field_percent_pie.o_field_widget .o_pie .o_mask").style
                .transform,
            "rotate(180deg)",
            "left mask should be covering the whole left side of the pie"
        );
        assert.strictEqual(
            target.querySelectorAll(".o_field_percent_pie.o_field_widget .o_pie .o_mask")[1].style
                .transform,
            "rotate(36deg)",
            "right mask should be rotated from 360*(10/100) = 36 degrees"
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
            target.querySelector(".o_field_percent_pie.o_field_widget .o_pie .o_pie_value")
                .textContent,
            "80%",
            "should have 80% as pie value since int_field=80"
        );
        assert.ok(
            _.str.include(
                target.querySelector(".o_field_percent_pie.o_field_widget .o_pie .o_mask").style
                    .transform,
                "rotate(288deg)"
            ),
            "left mask should be rotated from 360*(80/100) = 288 degrees"
        );
        assert.hasClass(
            target.querySelectorAll(".o_field_percent_pie.o_field_widget .o_pie .o_mask")[1],
            "o_full",
            "right mask should be hidden since the value > 50%"
        );

        // switch to edit mode and check the result
        await click(target.querySelector(".o_form_button_edit"));
        assert.containsOnce(
            target,
            ".o_field_percent_pie.o_field_widget .o_pie",
            "should have a pie chart"
        );
        assert.strictEqual(
            target.querySelector(".o_field_percent_pie.o_field_widget .o_pie .o_pie_value")
                .textContent,
            "80%",
            "should have 80% as pie value since int_field=80"
        );
        assert.strictEqual(
            target.querySelector(".o_field_percent_pie.o_field_widget .o_pie .o_mask").style
                .transform,
            "rotate(288deg)",
            "left mask should be rotated from 360*(80/100) = 288 degrees"
        );
        assert.hasClass(
            target.querySelectorAll(".o_field_percent_pie.o_field_widget .o_pie .o_mask")[1],
            "o_full",
            "right mask should be hidden since the value > 50%"
        );

        // save
        await click(target.querySelector(".o_form_button_save"));
        assert.containsOnce(
            target,
            ".o_field_percent_pie.o_field_widget .o_pie",
            "should have a pie chart"
        );
        assert.strictEqual(
            target.querySelector(".o_field_percent_pie.o_field_widget .o_pie .o_pie_value")
                .textContent,
            "80%",
            "should have 80% as pie value since int_field=80"
        );
        assert.strictEqual(
            target.querySelector(".o_field_percent_pie.o_field_widget .o_pie .o_mask").style
                .transform,
            "rotate(288deg)",
            "left mask should be rotated from 360*(80/100) = 288 degrees"
        );
        assert.hasClass(
            target.querySelectorAll(".o_field_percent_pie.o_field_widget .o_pie .o_mask")[1],
            "o_full",
            "right mask should be hidden since the value > 50%"
        );
    });

    // TODO: This test would pass without any issue since all the classes and
    //       custom style attributes are correctly set on the widget in list
    //       view, but since the scss itself for this widget currently only
    //       applies inside the form view, the widget is unusable. This test can
    //       be uncommented when we refactor the scss files so that this widget
    //       stylesheet applies in both form and list view.
    // QUnit.test('percentpie widget in editable list view', async function(assert) {
    //     assert.expect(10);
    //
    //     var list = await createView({
    //         View: ListView,
    //         model: 'partner',
    //         data: this.data,
    //         arch: '<tree editable="bottom">' +
    //                 '<field name="foo"/>' +
    //                 '<field name="int_field" widget="percentpie"/>' +
    //               '</tree>',
    //     });
    //
    //     assert.containsN(list, '.o_field_percent_pie .o_pie', 5,
    //         "should have five pie charts");
    //     assert.strictEqual(target.querySelector('.o_field_percent_pie:first .o_pie .o_pie_value').textContent,
    //         '10%', "should have 10% as pie value since int_field=10");
    //     assert.strictEqual(target.querySelector('.o_field_percent_pie:first .o_pie .o_mask').attr('style'),
    //         'rotate(180deg)', "left mask should be covering the whole left side of the pie");
    //     assert.strictEqual(target.querySelector('.o_field_percent_pie:first .o_pie .o_mask').last().attr('style'),
    //         'rotate(36deg)', "right mask should be rotated from 360*(10/100) = 36 degrees");
    //
    //     // switch to edit mode and check the result
    //    testUtils.dom.click(     target.querySelector('tbody td:not(.o_list_record_selector)'));
    //     assert.strictEqual(target.querySelector('.o_field_percent_pie:first .o_pie .o_pie_value').textContent,
    //         '10%', "should have 10% as pie value since int_field=10");
    //     assert.strictEqual(target.querySelector('.o_field_percent_pie:first .o_pie .o_mask').attr('style'),
    //         'rotate(180deg)', "left mask should be covering the whole right side of the pie");
    //     assert.strictEqual(target.querySelector('.o_field_percent_pie:first .o_pie .o_mask').last().attr('style'),
    //         'rotate(36deg)', "right mask should be rotated from 360*(10/100) = 36 degrees");
    //
    //     // save
    //    testUtils.dom.click(     list.$buttons.find('.o_list_button_save'));
    //     assert.strictEqual(target.querySelector('.o_field_percent_pie:first .o_pie .o_pie_value').textContent,
    //         '10%', "should have 10% as pie value since int_field=10");
    //     assert.strictEqual(target.querySelector('.o_field_percent_pie:first .o_pie .o_mask').attr('style'),
    //         'rotate(180deg)', "left mask should be covering the whole right side of the pie");
    //     assert.strictEqual(target.querySelector('.o_field_percent_pie:first .o_pie .o_mask').last().attr('style'),
    //         'rotate(36deg)', "right mask should be rotated from 360*(10/100) = 36 degrees");
    //
    //     list.destroy();
    // });
});
