/** @odoo-module **/
import { click, editInput, getFixture } from "@web/../tests/helpers/utils";
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
                        hex_color: { string: "hexadecimal color", type: "char" },
                    },
                    records: [
                        {
                            id: 1,
                        },
                        {
                            id: 2,
                            hex_color: "#ff4444",
                        },
                    ],
                },
            },
        };
        setupViewRegistries();
    });

    QUnit.module("ColorField");

    QUnit.test("field contains a color input", async function (assert) {
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `
                <form>
                    <group>
                        <field name="hex_color" widget="color" />
                    </group>
                </form>`,
        });
        assert.containsOnce(
            target,
            ".o_field_color input[type='color']",
            "native color input is used by the field"
        );
        // style returns the value in the rgb format
        assert.strictEqual(
            target.querySelector(".o_field_color div").style.backgroundColor,
            "rgb(0, 0, 0)",
            "field has the default color set as background if no value has been selected"
        );

        await editInput(target, ".o_field_color input", "#fefefe");
        assert.strictEqual(
            target.querySelector(".o_field_color div").style.backgroundColor,
            "rgb(254, 254, 254)",
            "field has the new color set as background"
        );
    });

    QUnit.test("color field in editable list view", async function (assert) {
        await makeView({
            type: "list",
            serverData,
            resModel: "partner",
            arch: `
                <tree editable="bottom">
                    <field name="hex_color" widget="color" />
                </tree>`,
        });

        assert.containsN(
            target,
            ".o_field_color input[type='color']",
            2,
            "native color input is used on each row"
        );

        await click(target.querySelector(".o_field_color input"));
        assert.doesNotHaveClass(target.querySelector(".o_data_row"), "o_selected_row");
    });
});
