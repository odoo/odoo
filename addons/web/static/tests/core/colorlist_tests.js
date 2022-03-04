/** @odoo-module **/

import { ColorList } from "@web/core/colorlist/colorlist";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { makeTestEnv } from "../helpers/mock_env";
import { click, getFixture, mount } from "../helpers/utils";

const { Component, xml } = owl;
const serviceRegistry = registry.category("services");

let target;

/**
 * @param {typeof ColorList} Picker
 * @param {Object} props
 * @returns {Promise<ColorList>}
 */
const mountComponent = async (Picker, props) => {
    serviceRegistry.add("ui", uiService);
    target = getFixture();

    class Parent extends Component {}
    Parent.template = xml/* xml */ `
        <t t-component="props.Picker" t-props="props.props"/>
        <div class="outsideDiv"/>
    `;

    const env = await makeTestEnv();
    if (!props.onColorSelected) {
        props.onColorSelected = () => {};
    }
    const parent = await mount(Parent, target, { env, props: { Picker, props } });
    return parent;
};

QUnit.module("Components", () => {
    QUnit.module("ColorList");

    QUnit.test("basic rendering", async function (assert) {
        assert.expect(4);

        await mountComponent(ColorList, {
            colors: [0, 9],
        });

        assert.containsOnce(target, ".o_colorlist");
        assert.containsN(target, "button", 2, "two buttons are available");
        const secondBtn = target.querySelectorAll(".o_colorlist button")[1];
        assert.strictEqual(
            secondBtn.attributes.title.value,
            "Fuchsia",
            "second button color is Fuchsia"
        );
        assert.hasClass(
            secondBtn,
            "o_colorlist_item_color_9",
            "second button has the corresponding class"
        );
    });

    QUnit.test("toggler is available if togglerColor props is given", async function (assert) {
        assert.expect(9);

        const togglerColorId = 0;
        await mountComponent(ColorList, {
            colors: [4, 5, 6],
            togglerColor: togglerColorId,
            onColorSelected: (colorId) => assert.step("color #" + colorId + " is selected"),
        });

        assert.containsOnce(target, ".o_colorlist");
        assert.containsOnce(
            target,
            "button.o_colorlist_toggler",
            "only the toggler button is available"
        );
        assert.hasClass(
            target.querySelector(".o_colorlist button"),
            "o_colorlist_item_color_" + togglerColorId,
            "toggler has the right class"
        );

        await click(target.querySelector(".o_colorlist button"));

        assert.containsNone(
            target,
            "button.o_colorlist_toggler",
            "toggler button is no longer visible"
        );
        assert.containsN(target, "button", 3, "three buttons are available");

        await click(target.querySelector(".outsideDiv"));
        assert.containsN(target, "button", 1, "only one button is available");
        assert.containsOnce(
            target,
            "button.o_colorlist_toggler",
            "colorlist has been closed and toggler is visible"
        );

        // reopen the colorlist and select a color
        await click(target.querySelector(".o_colorlist_toggler"));
        await click(target.querySelectorAll(".o_colorlist button")[2]);

        assert.verifySteps(["color #6 is selected"]);
    });
});
