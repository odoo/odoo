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
                        {
                            id: 1,
                            foo: "first",
                            int_field: 0,
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("ColorPickerField");

    QUnit.test(
        "No chosen color is a red line with a white background (color 0)",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <group>
                            <field name="int_field" widget="color_picker"/>
                        </group>
                    </form>`,
            });

            // switch to edit mode
            await click(target, ".o_form_button_edit");

            assert.hasClass(
                target.querySelectorAll(".o_field_color_picker button"),
                "o_colorlist_item_color_0",
                "The default no color value does have the right class"
            );

            await click(target, ".o_field_color_picker button");

            assert.hasClass(
                target.querySelectorAll(".o_field_color_picker button"),
                "o_colorlist_item_color_0",
                "The no color item does have the right class in the list"
            );

            await click(target, ".o_field_color_picker .o_colorlist_item_color_3");
            await click(target, ".o_field_color_picker button");

            assert.hasClass(
                target.querySelectorAll(".o_field_color_picker button"),
                "o_colorlist_item_color_0",
                "The no color item still have the right class in the list"
            );
        }
    );

    QUnit.test("closes when color selected or outside click", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="int_field" widget="color_picker"/>
                        <field name="foo"/>
                    </group>
                </form>`,
        });

        // switch to edit mode
        await click(target, ".o_form_button_edit");

        await click(target, ".o_field_color_picker button");

        assert.strictEqual(
            target.querySelectorAll(".o_field_color_picker button").length > 1,
            true,
            "there should be more color elements when the component is opened"
        );

        await click(target, ".o_field_color_picker .o_colorlist_item_color_3");

        assert.strictEqual(
            target.querySelectorAll(".o_field_color_picker button").length,
            1,
            "there should be one color element when the component is closed"
        );

        await click(target, ".o_field_color_picker button");

        await click(target.querySelector('.o_field_widget[name="foo"] input'));

        assert.strictEqual(
            target.querySelectorAll(".o_field_color_picker button").length,
            1,
            "there should be one color element when the component is closed"
        );
    });

    QUnit.test(
        "stop event propagation on click to avoid oppening record on tree view",
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "partner",
                serverData,
                arch: `
                    <tree>
                        <field name="int_field" widget="color_picker"/>
                    </tree>`,
            });

            await click(target, ".o_field_color_picker button");

            assert.strictEqual(
                document.querySelectorAll(".o_list_renderer").length,
                1,
                "The current view should still be a list view"
            );

            await click(target, ".o_field_color_picker .o_colorlist_item_color_6");

            assert.strictEqual(
                document.querySelectorAll(".o_list_renderer").length,
                1,
                "The current view should still be a list view"
            );
        }
    );

    QUnit.test("column widths: dont overflow color picker in list", async function (assert) {
        serverData.models.partner.fields.date_field = {
            string: "Date field",
            type: "date",
        };

        await makeView({
            type: "list",
            serverData,
            resModel: "partner",
            arch: `
                 <tree editable="top">
                     <field name="date_field"/>
                     <field name="int_field" widget="color_picker"/>
                 </tree>`,
            domain: [["id", "<", 0]],
        });
        await click(target.querySelector(".o_list_button_add"));
        const date_column_width = target
            .querySelector('.o_list_table thead th[data-name="date_field"]')
            .style.width.replace("px", "");
        const int_field_column_width = target
            .querySelector('.o_list_table thead th[data-name="int_field"]')
            .style.width.replace("px", "");
        // Default values for date and int fields are: date: '92px', integer: '74px'
        // With the screen growing, the proportion is kept and thus int_field would remain smaller than date if
        // the color_picker wouldn't have widthInList set to '1'. With that property set, int_field size will be bigger
        // than date's one.
        assert.ok(
            parseFloat(date_column_width) < parseFloat(int_field_column_width),
            "colorpicker should display properly (Horizontly)"
        );
    });
});
