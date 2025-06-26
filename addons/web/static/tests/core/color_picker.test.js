import { test, expect } from "@odoo/hoot";
import { press, click, animationFrame } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { ColorPicker, DEFAULT_COLORS } from "@web/core/color_picker/color_picker";

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
    expect(".o_font_color_selector .btn-tab").toHaveCount(3);
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
