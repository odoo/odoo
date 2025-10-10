import { test, expect } from "@odoo/hoot";
import { press, click, animationFrame, queryOne } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
import { defineStyle, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ColorPicker, DEFAULT_COLORS } from "@web/core/color_picker/color_picker";
import { CustomColorPicker } from "@web/core/color_picker/custom_color_picker/custom_color_picker";
import { registry } from "@web/core/registry";

test("basic rendering", async () => {
    await mountWithCleanup(ColorPicker, {
        props: {
            state: {
                selectedColor: "",
                defaultTab: "",
            },
            getUsedCustomColors: () => [],
            applyColor() {},
            applyColorPreview() {},
            applyColorResetPreview() {},
            colorPrefix: "",
        },
    });
    expect(".o_font_color_selector").toHaveCount(1);
    expect(".o_font_color_selector .btn-tab").toHaveCount(2);
    expect(".o_font_color_selector .btn.fa-trash").toHaveCount(1);
    expect(".o_font_color_selector .o_colorpicker_section").toHaveCount(1);
    expect(".o_font_color_selector .o_colorpicker_section .o_color_button").toHaveCount(5);
    expect(".o_font_color_selector .o_color_section .o_color_button[data-color]").toHaveCount(
        DEFAULT_COLORS.flat().length
    );
});

test("basic rendering with selected color", async () => {
    await mountWithCleanup(ColorPicker, {
        props: {
            state: {
                selectedColor: "#B5D6A5",
                defaultTab: "",
            },
            getUsedCustomColors: () => [],
            applyColor() {},
            applyColorPreview() {},
            applyColorResetPreview() {},
            colorPrefix: "",
        },
    });
    expect(".o_font_color_selector").toHaveCount(1);
    expect(".o_font_color_selector .o_color_section .o_color_button[data-color]").toHaveCount(
        DEFAULT_COLORS.flat().length
    );
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color='#B5D6A5'].selected"
    ).toHaveCount(1);
});

test("keyboard navigation", async () => {
    await mountWithCleanup(ColorPicker, {
        props: {
            state: {
                selectedColor: "",
                defaultTab: "",
            },
            getUsedCustomColors: () => [],
            applyColor() {},
            applyColorPreview() {},
            applyColorResetPreview() {},
            colorPrefix: "",
        },
    });
    // select the first color
    await click(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:first-of-type"
    );
    await animationFrame();
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:first-of-type"
    ).toBeFocused();

    // move to the second color
    await press("arrowright");
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:nth-of-type(2)"
    ).toBeFocused();

    // select the second color using Enter key
    await press("enter");
    await animationFrame();
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:nth-of-type(2)"
    ).toHaveClass("selected");

    // move back to the first color
    await press("arrowleft");
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:first-of-type"
    ).toBeFocused();

    // cannot move if no previous color
    await press("arrowleft");
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:first-of-type"
    ).toBeFocused();

    // move the color below
    await press("arrowdown");
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:nth-of-type(9)"
    ).toBeFocused();

    // move back to the first color
    await press("arrowup");
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:first-of-type"
    ).toBeFocused();

    // select the last color of the first row
    await click(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:nth-of-type(8)"
    );
    await animationFrame();

    // move to the first color of the second row
    await press("arrowright");
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:nth-of-type(9)"
    ).toBeFocused();

    // move back to the last color of the first row
    await press("arrowleft");
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:nth-of-type(8)"
    ).toBeFocused();

    // select the last color
    await click(".o_font_color_selector .o_color_section .o_color_button[data-color]:last-of-type");
    await animationFrame();
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:last-of-type"
    ).toBeFocused();

    // cannot move if no next color
    await press("arrowright");
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:last-of-type"
    ).toBeFocused();
});

test("colorpicker inside the builder are linked to the builder theme colors", async () => {
    await mountWithCleanup(ColorPicker, {
        props: {
            state: {
                selectedColor: "",
                defaultTab: "",
            },
            getUsedCustomColors: () => [],
            applyColor() {},
            applyColorPreview() {},
            applyColorResetPreview() {},
            colorPrefix: "",
            cssVarColorPrefix: "xyz-",
        },
    });
    const getButtonColor = (sel) => getComputedStyle(queryOne(sel)).backgroundColor;

    defineStyle(`
        :root {
            --o-color-1: rgb(113, 75, 103);
            --o-color-2: rgb(45, 49, 66);
            --xyz-o-color-1: rgb(113, 75, 103);
            --xyz-o-color-2: rgb(45, 49, 66);
        }
    `);
    expect(getButtonColor("button[data-color='o-color-1']")).toBe("rgb(113, 75, 103)");
    expect(getButtonColor("button[data-color='o-color-2']")).toBe("rgb(45, 49, 66)");

    defineStyle(`
        :root {
            --xyz-o-color-1: rgb(0, 0, 255);
            --xyz-o-color-2: rgb(0, 255, 0);
        }
    `);
    expect(getButtonColor("button[data-color='o-color-1']")).toBe("rgb(0, 0, 255)");
    expect(getButtonColor("button[data-color='o-color-2']")).toBe("rgb(0, 255, 0)");
});

test("colorpicker outside the builder are not linked to the builder theme colors", async () => {
    await mountWithCleanup(ColorPicker, {
        props: {
            state: {
                selectedColor: "",
                defaultTab: "",
            },
            getUsedCustomColors: () => [],
            applyColor() {},
            applyColorPreview() {},
            applyColorResetPreview() {},
            colorPrefix: "",
            cssVarColorPrefix: "",
        },
    });
    const getButtonColor = (sel) => getComputedStyle(queryOne(sel)).backgroundColor;

    defineStyle(`
        :root {
            --o-color-1: rgb(113, 75, 103);
            --o-color-2: rgb(45, 49, 66);
            --xyz-o-color-1: rgb(113, 75, 103);
            --xyz-o-color-2: rgb(45, 49, 66);
        }
    `);
    expect(getButtonColor("button[data-color='o-color-1']")).toBe("rgb(113, 75, 103)");
    expect(getButtonColor("button[data-color='o-color-2']")).toBe("rgb(45, 49, 66)");

    defineStyle(`
        :root {
            --xyz-o-color-1: rgb(0, 0, 255);
            --xyz-o-color-2: rgb(0, 255, 0);
        }
    `);
    expect(getButtonColor("button[data-color='o-color-1']")).toBe("rgb(113, 75, 103)");
    expect(getButtonColor("button[data-color='o-color-2']")).toBe("rgb(45, 49, 66)");
});

test("custom color picker sets default color as selected", async () => {
    await mountWithCleanup(CustomColorPicker, {
        props: {
            defaultColor: "#FF0000",
        },
    });
    expect("input.o_hex_input").toHaveValue("#FF0000");
});

test("custom color picker change color on click in hue slider", async () => {
    await mountWithCleanup(CustomColorPicker, { props: { selectedColor: "#FF0000" } });
    expect("input.o_hex_input").toHaveValue("#FF0000");
    await click(".o_color_slider");
    expect("input.o_hex_input").not.toHaveValue("#FF0000");
});

class ExtraTab extends Component {
    static template = xml`<p>Color picker extra tab</p>`;
    static props = ["*"];
}

test("can register an extra tab", async () => {
    registry.category("color_picker_tabs").add("web.extra", {
        id: "extra",
        name: "Extra",
        component: ExtraTab,
    });
    await mountWithCleanup(ColorPicker, {
        props: {
            state: {
                selectedColor: "#FF0000",
                defaultTab: "",
            },
            getUsedCustomColors: () => [],
            applyColor() {},
            applyColorPreview() {},
            applyColorResetPreview() {},
            colorPrefix: "",
            enabledTabs: ["solid", "custom", "extra"],
        },
    });
    expect(".o_font_color_selector .btn-tab").toHaveCount(3);
    await click("button.extra-tab");
    await animationFrame();
    expect("button.extra-tab").toHaveClass("active");
    expect(".o_font_color_selector>p:last-child").toHaveText("Color picker extra tab");
    registry.category("color_picker_tabs").remove("web.extra");
});

test("should mark default color as selected when it is selected", async () => {
    defineStyle(`
        :root {
            --900: #212527;
        }
    `);
    await mountWithCleanup(ColorPicker, {
        props: {
            state: {
                selectedColor: "#212527",
                defaultTab: "custom",
            },
            getUsedCustomColors: () => [],
            applyColor() {},
            applyColorPreview() {},
            applyColorResetPreview() {},
            colorPrefix: "",
        },
    });
    expect(".o_color_button[data-color='900']").toHaveClass("selected");
});
