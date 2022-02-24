/** @odoo-module **/

import { ColorPicker } from "@web/core/colorpicker/colorpicker";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { makeTestEnv } from "../helpers/mock_env";
import { editInput, getFixture, mount, triggerEvent } from "../helpers/utils";

const { Component, xml } = owl;
const serviceRegistry = registry.category("services");

let target;

/**
 * @param {typeof ColorPicker} Picker
 * @param {Object} props
 * @param {DateTime} props.date
 * @returns {Promise<ColorPicker>}
 */
const mountPicker = async (Picker, props) => {
    serviceRegistry.add("ui", uiService);
    target = getFixture();

    class Parent extends Component {}
    Parent.template = xml/* xml */ `
        <t t-component="props.Picker" t-props="props.props"/>
    `;

    const env = await makeTestEnv();
    if (!props.onColorSelected) {
        props.onColorSelected = () => {};
    }
    const parent = await mount(Parent, target, { env, props: { Picker, props } });
    return parent;
};

QUnit.module("Components", () => {
    QUnit.module("ColorPicker");

    QUnit.test("basic rendering", async function (assert) {
        assert.expect(4);

        const picker = await mountPicker(ColorPicker, {});

        assert.containsOnce(target, ".o_colorpicker_widget");
        assert.containsOnce(picker, ".o_color_slider");
        assert.containsOnce(picker, ".o_color_pick_area");

        const input = target.querySelector(".o_hex_div input");
        assert.strictEqual(input.value, "#000000", "Default value should be #000000");
    });

    QUnit.test("change color value using the pick area", async function (assert) {
        assert.expect(7);

        const picker = await mountPicker(ColorPicker, {
            onColorSelected: () => {
                assert.step("color selected");
            },
        });

        assert.containsOnce(target, ".o_colorpicker_widget");
        assert.containsOnce(picker, ".o_color_slider");
        assert.containsOnce(picker, ".o_color_pick_area");

        const input = target.querySelector(".o_hex_div input");
        assert.strictEqual(input.value, "#000000", "default value should be #000000");

        const pickArea = target.querySelector(".o_color_pick_area");
        const pickAreaRect = pickArea.getBoundingClientRect();
        await triggerEvent(pickArea, null, "mousedown", {
            clientX: pickAreaRect.right,
            clientY: pickAreaRect.top + pickAreaRect.height / 2,
        });
        await triggerEvent(pickArea, null, "mouseup");

        assert.strictEqual(input.value, "#ff0000", "new value should be #ff0000");
        assert.verifySteps(["color selected"], "color has been selected");
    });

    QUnit.test("change color value using the text input", async function (assert) {
        assert.expect(7);

        const picker = await mountPicker(ColorPicker, {
            onColorSelected: () => {
                assert.step("color selected");
            },
        });

        assert.containsOnce(target, ".o_colorpicker_widget");
        assert.containsOnce(picker, ".o_color_slider");
        assert.containsOnce(picker, ".o_color_pick_area");

        const input = target.querySelector(".o_hex_div input");
        assert.strictEqual(input.value, "#000000", "Default value should be #000000");

        await editInput(target, ".o_hex_div input", "#abcdef");

        assert.strictEqual(input.value, "#abcdef", "new value should be #abcdef");
        assert.verifySteps(["color selected"], "color has been selected");
    });

    QUnit.test("picker outputs all values", async function (assert) {
        assert.expect(14);

        const picker = await mountPicker(ColorPicker, {
            onColorSelected: (colorData) => {
                Object.keys(colorData)
                    .sort()
                    .forEach((o) => assert.step(o));
            },
        });

        assert.containsOnce(target, ".o_colorpicker_widget");
        assert.containsOnce(picker, ".o_color_slider");
        assert.containsOnce(picker, ".o_color_pick_area");

        const input = target.querySelector(".o_hex_div input");
        assert.strictEqual(input.value, "#000000", "Default value should be #000000");

        await editInput(target, ".o_hex_div input", "#abcdef");

        assert.strictEqual(input.value, "#abcdef", "new value should be #abcdef");
        assert.verifySteps(
            ["blue", "green", "hex", "hue", "lightness", "opacity", "red", "saturation"],
            "all values have been outputed"
        );
    });
});
