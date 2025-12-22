import { expect, test } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { ColorList } from "@web/core/colorlist/colorlist";

class Parent extends Component {
    static template = xml`
        <t t-component="Component" t-props="componentProps"/>
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
            onColorSelected: (colorId) => expect.step("color #" + colorId + " is selected"),
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
            onColorSelected: (colorId) => expect.step("color #" + colorId + " is selected"),
        },
    });
    expect(".o_colorlist").toHaveCount(1);
    expect(".o_colorlist button").toHaveClass("o_colorlist_item_color_" + selectedColorId);

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
