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
                        foo: { type: "char" },
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
        serverData.models.partner.onchanges = {
            hex_color: () => {},
        };
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
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.step(`onchange ${JSON.stringify(args.args)}`);
                }
            },
        });
        assert.containsOnce(
            target,
            ".o_field_color input[type='color']",
            "native color input is used by the field"
        );
        // style returns the value in the rgb format
        assert.strictEqual(
            target.querySelector(".o_field_color div").style.backgroundColor,
            "initial",
            "field has the transparent background if no color value has been selected"
        );

        assert.strictEqual(target.querySelector(".o_field_color input").value, "#000000");
        await editInput(target, ".o_field_color input", "#fefefe");
        assert.verifySteps([
            'onchange [[1],{"id":1,"hex_color":"#fefefe"},"hex_color",{"hex_color":"1"}]',
        ]);
        assert.strictEqual(target.querySelector(".o_field_color input").value, "#fefefe");
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

    QUnit.test("read-only color field in editable list view", async function (assert) {
        await makeView({
            type: "list",
            serverData,
            resModel: "partner",
            arch: `
                <tree editable="bottom">
                    <field name="hex_color" readonly="1" widget="color" />
                </tree>`,
        });

        assert.containsN(
            target,
            '.o_field_color input:disabled',
            2,
            "the field should not be editable"
        );
    });

    QUnit.test("color field change via another field's onchange", async (assert) => {
        serverData.models.partner.onchanges = {
            foo: (rec) => {
                rec.hex_color = "#fefefe";
            },
        };
        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `
                <form>
                    <field name="foo" />
                    <field name="hex_color" widget="color" />
                </form>`,
            mockRPC(route, args) {
                if (args.method === "onchange") {
                    assert.step(`onchange ${JSON.stringify(args.args)}`);
                }
            },
        });

        assert.strictEqual(
            target.querySelector(".o_field_color div").style.backgroundColor,
            "initial",
            "field has transparent background if no color value has been selected"
        );
        assert.strictEqual(target.querySelector(".o_field_color input").value, "#000000");
        await editInput(target, ".o_field_char[name='foo'] input", "someValue");
        assert.verifySteps([
            'onchange [[1],{"id":1,"foo":"someValue","hex_color":false},"foo",{"foo":"1","hex_color":""}]',
        ]);
        assert.strictEqual(target.querySelector(".o_field_color input").value, "#fefefe");
        assert.strictEqual(
            target.querySelector(".o_field_color div").style.backgroundColor,
            "rgb(254, 254, 254)",
            "field has the new color set as background"
        );
    });
});
