// @ts-check

import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { Component, useState, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ColorList } from "@web/components/colorlist/colorlist";

class Parent extends Component {
    static template = xml`
        <t t-component="this.Component" t-props="this.componentProps"/>
        <div class="outsideDiv">Outside div</div>
    `;
    static props = ["*"];

    get Component() {
        return this.props.Component || ColorList;
    }

    get componentProps() {
        const props = { ...this.props };
        delete props.Component;
        if (!props.onColorSelected) {
            props.onColorSelected = () => {};
        }
        return props;
    }
}

test("basic rendering with forceExpanded props", async () => {
    await mountWithCleanup(Parent, {
        props: {
            colors: [0, 9],
            forceExpanded: true,
        },
    });

    expect(".o_colorlist").toHaveCount(1);
    expect(".o_colorlist button").toHaveCount(2);
    expect(".o_colorlist button:eq(1)").toHaveAttribute("title", "Raspberry");
    expect(".o_colorlist button:eq(1)").toHaveClass("o_colorlist_item_color_9");
});

test("color click does not open the list if canToggle props is not given", async () => {
    const selectedColorId = 0;
    await mountWithCleanup(Parent, {
        props: {
            colors: [4, 5, 6],
            selectedColor: selectedColorId,
            onColorSelected: (/** @type {any} */ colorId) =>
                expect.step("color #" + colorId + " is selected"),
        },
    });
    expect(".o_colorlist").toHaveCount(1);
    expect("button.o_colorlist_toggler").toHaveCount(1);

    await contains(".o_colorlist").click();
    expect("button.o_colorlist_toggler").toHaveCount(1);
});

test("open the list of colors if canToggle props is given", async function () {
    const selectedColorId = 0;
    await mountWithCleanup(Parent, {
        props: {
            canToggle: true,
            colors: [4, 5, 6],
            selectedColor: selectedColorId,
            onColorSelected: (/** @type {any} */ colorId) =>
                expect.step("color #" + colorId + " is selected"),
        },
    });
    expect(".o_colorlist").toHaveCount(1);
    expect(".o_colorlist button").toHaveClass(
        "o_colorlist_item_color_" + selectedColorId,
    );

    await contains(".o_colorlist button").click();
    expect("button.o_colorlist_toggler").toHaveCount(0);
    expect(".o_colorlist button").toHaveCount(3);

    await contains(".outsideDiv").click();
    expect(".o_colorlist button").toHaveCount(1);
    expect("button.o_colorlist_toggler").toHaveCount(1);

    await contains(".o_colorlist_toggler").click();
    await contains(".o_colorlist button:eq(2)").click();
    expect.verifySteps(["color #6 is selected"]);
});

test("the isExpanded prop is followed after it changes", async () => {
    class Controller extends Component {
        static template = xml`<ColorList colors="[1,2,3]" onColorSelected="() => {}" isExpanded="this.state.expanded" canToggle="true"/>`;
        static components = { ColorList };
        static props = /** @type {string[]} */ ([]);

        /** @type {{ expanded: boolean }} */
        state;

        setup() {
            this.state = useState({ expanded: false });
        }
    }
    const controller = await mountWithCleanup(Controller);
    expect(".o_colorlist_item_color_1").toHaveCount(0);

    controller.state.expanded = true;
    await animationFrame();
    expect(".o_colorlist_item_color_1").toHaveCount(1);

    controller.state.expanded = false;
    await animationFrame();
    expect(".o_colorlist_item_color_1").toHaveCount(0);
});

test("the isExpanded prop sync does not undo the user's own toggle", async () => {
    class Controller extends Component {
        static template = xml`
            <ColorList colors="[1,2,3]" onColorSelected="() => {}" isExpanded="this.state.expanded" canToggle="true"/>
            <span t-out="this.state.tick"/>`;
        static components = { ColorList };
        static props = /** @type {string[]} */ ([]);

        /** @type {{ expanded: boolean, tick: number }} */
        state;

        setup() {
            this.state = useState({ expanded: false, tick: 0 });
        }
    }
    const controller = await mountWithCleanup(Controller);
    await contains(".o_colorlist_toggler").click();
    expect(".o_colorlist_item_color_1").toHaveCount(1);

    controller.state.tick = 1;
    await animationFrame();
    expect(".o_colorlist_item_color_1").toHaveCount(1);
});

test("a list that arrives expanded does not take focus from the page", async () => {
    class Host extends Component {
        static template = xml`
            <input class="outside"/>
            <ColorList colors="[1,2,3]" isExpanded="true" canToggle="true" onColorSelected="() => {}"/>`;
        static components = { ColorList };
        static props = /** @type {string[]} */ ([]);
    }
    await mountWithCleanup(Host);
    expect(".o_colorlist_item_color_1").toHaveCount(1);
    expect(document.activeElement).not.toHaveClass("o_colorlist_item_color_1");

    await contains(".o_colorlist_item_color_1").click();
    await contains(".o_colorlist_toggler").click();
    expect(".o_colorlist_item_color_1").toBeFocused();
});
