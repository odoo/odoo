import { expect, test } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { ColorList } from "@web/core/colorlist/colorlist";

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

test("basic rendering", async () => {
    await mountWithCleanup(Parent, {
        props: {
            onColorSelected:(color) => expect.step(`color ${color} selected`),
        },
    });

    expect(".o_colorlist button").toHaveCount(12);
    expect(".o_colorlist button:eq(0)").toHaveAttribute("title", "No color");
    expect(".o_colorlist button:eq(0)").toHaveClass("o_colorlist_item_color_0");
    await contains(".o_colorlist button:eq(9)").click();
    expect.verifySteps(["color 9 selected"]);
});

test("use 'disableTransparent' props to hide the transparent option", async () => {
    await mountWithCleanup(Parent, {
        props: {
            disableTransparent: true,
            onColorSelected:(color) => expect.step(`color ${color} selected`),
        },
    });

    expect(".o_colorlist button").toHaveCount(11);
    expect(".o_colorlist button:eq(0)").toHaveAttribute("title", "Red");
    expect(".o_colorlist button:eq(0)").toHaveClass("o_colorlist_item_color_1");
    await contains(".o_colorlist button:eq(9)").click();
    expect.verifySteps(["color 10 selected"]);
});

test("use 'selectedColor' props to highlight the selected color", async () => {
    await mountWithCleanup(Parent, {
        props: {
            selectedColor: 3,
        },
    });

    expect(".o_colorlist button.o_colorlist_item_color_3.active").toHaveCount(1);
});
