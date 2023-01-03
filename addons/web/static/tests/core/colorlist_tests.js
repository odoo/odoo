/** @odoo-module **/

import { ColorList } from "@web/core/colorlist/colorlist";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { makeTestEnv } from "../helpers/mock_env";
import { click, getFixture, mount } from "../helpers/utils";

import { Component, xml } from "@odoo/owl";
const serviceRegistry = registry.category("services");

let target;

/**
 * @param {typeof ColorList} Picker
 * @param {Object} props
 * @returns {Promise<ColorList>}
 */
async function mountComponent(Picker, props) {
    serviceRegistry.add("ui", uiService);
    target = getFixture();

    class Parent extends Component {}
    Parent.template = xml/* xml */ `
        <t t-component="props.Picker" t-props="props.props"/>
        <div class="outsideDiv">Outside div</div>
    `;

    const env = await makeTestEnv();
    if (!props.onColorSelected) {
        props.onColorSelected = () => {};
    }
    const parent = await mount(Parent, target, { env, props: { Picker, props } });
    return parent;
}

QUnit.module("Components", () => {
    QUnit.module("ColorList");

    QUnit.test("basic rendering with forceExpanded props", async function (assert) {
        await mountComponent(ColorList, {
            colors: [0, 9],
            forceExpanded: true,
        });

        assert.containsOnce(target, ".o_colorlist");
        assert.containsN(target, ".o_colorlist button", 2, "two buttons are available");
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

    QUnit.test(
        "color click does not open the list if canToggle props is not given",
        async function (assert) {
            const selectedColorId = 0;
            await mountComponent(ColorList, {
                colors: [4, 5, 6],
                selectedColor: selectedColorId,
                onColorSelected: (colorId) => assert.step("color #" + colorId + " is selected"),
            });

            assert.containsOnce(target, ".o_colorlist");
            assert.containsOnce(
                target,
                "button.o_colorlist_toggler",
                "only the toggler button is available"
            );

            await click(target.querySelector(".o_colorlist button"));

            assert.containsOnce(target, "button.o_colorlist_toggler", "button is still visible");
        }
    );

    QUnit.test("open the list of colors if canToggle props is given", async function (assert) {
        const selectedColorId = 0;
        await mountComponent(ColorList, {
            canToggle: true,
            colors: [4, 5, 6],
            selectedColor: selectedColorId,
            onColorSelected: (colorId) => assert.step("color #" + colorId + " is selected"),
        });

        assert.containsOnce(target, ".o_colorlist");
        assert.hasClass(
            target.querySelector(".o_colorlist button"),
            "o_colorlist_item_color_" + selectedColorId,
            "toggler has the right class"
        );

        await click(target.querySelector(".o_colorlist button"));

        assert.containsNone(
            target,
            "button.o_colorlist_toggler",
            "toggler button is no longer visible"
        );
        assert.containsN(target, ".o_colorlist button", 3, "three buttons are available");

        await click(target.querySelector(".outsideDiv"));
        assert.containsOnce(target, ".o_colorlist button", "only one button is available");
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
