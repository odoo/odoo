/** @odoo-module **/

import { click, triggerEvent } from "../helpers/utils";
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

    QUnit.skip("can navigate away with TAB", async function (assert) {
        assert.expect(1);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form string="Partners">
                    <group>
                        <field name="int_field" widget="color_picker"/>
                        <field name="foo" />
                    </group>
                </form>`,
        });

        // switch to edit mode
        await click(form.el, ".o_form_button_edit");

        // click on the only element (because it's closed) to open the field component
        await click(form.el, "a");

        await triggerEvent(document.activeElement, null, "keydown", {
            which: 13, // tab
        });

        assert.strictEqual(
            document.activeElement,
            form.el.querySelector('input[name="foo"]'),
            "foo field should be focused"
        );
    });

    QUnit.test(
        "No chosen color is a red line with a white background (color 0)",
        async function (assert) {
            assert.expect(3);

            const form = await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                <form string="Partners">
                    <group>
                        <field name="int_field" widget="color_picker"/>
                    </group>
                </form>`,
            });

            // switch to edit mode
            await click(form.el, ".o_form_button_edit");

            assert.hasClass(
                form.el.querySelectorAll("a:first-child"),
                "o_field_color_picker_color_0",
                "The no color item doesn't have the right class"
            );

            await click(form.el, "a");

            assert.hasClass(
                form.el.querySelectorAll("a:first-child"),
                "o_field_color_picker_color_0",
                "The no color item doesn't have the right class"
            );

            await click(form.el, ".o_field_color_picker_color_3");
            await click(form.el, "a");

            assert.hasClass(
                form.el.querySelectorAll("a:first-child"),
                "o_field_color_picker_color_0",
                "The no color item doesn't have the right class"
            );
        }
    );

    QUnit.test("closes when color selected or outside click", async function (assert) {
        assert.expect(3);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form string="Partners">
                    <group>
                        <field name="int_field" widget="color_picker"/>
                        <field name="foo"/>
                    </group>
                </form>`,
        });

        // switch to edit mode
        await click(form.el, ".o_form_button_edit");

        await click(form.el, "a");

        assert.strictEqual(
            form.el.querySelectorAll("a").length > 1,
            true,
            "there should be more color elements when the component is opened"
        );

        await click(form.el, ".o_field_color_picker_color_3");

        assert.strictEqual(
            form.el.querySelectorAll("a").length,
            1,
            "there should be one color element when the component is closed"
        );

        await click(form.el, "a");

        await click(form.el.querySelector('input[name="foo"]'));

        assert.strictEqual(
            form.el.querySelectorAll("a").length,
            1,
            "there should be one color element when the component is closed"
        );
    });

    QUnit.test(
        "stop event propagation on click to avoid oppening record on tree view",
        async function (assert) {
            assert.expect(2);

            const list = await makeView({
                type: "list",
                resModel: "partner",
                serverData,
                arch: `
                <tree>
                        <field name="int_field" widget="color_picker"/>
                </tree>`,
            });

            await click(list.el, ".o_field_color_picker a");

            assert.strictEqual(
                document.querySelectorAll(".o_list_renderer").length,
                1,
                "The current view should still be a list view"
            );

            await click(list.el, ".o_field_color_picker_color_6");

            assert.strictEqual(
                document.querySelectorAll(".o_list_renderer").length,
                1,
                "The current view should still be a list view"
            );
        }
    );
});
