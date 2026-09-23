// @ts-check

import { expect, test } from "@odoo/hoot";
import {
    animationFrame,
    click,
    manuallyDispatchProgrammaticEvent,
    press,
    queryAll,
    queryOne,
} from "@odoo/hoot-dom";
import { Component, useState, xml } from "@odoo/owl";
import {
    contains,
    defineStyle,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import {
    ColorPicker,
    DEFAULT_COLORS,
    useColorPicker,
} from "@web/components/color_picker/color_picker";
import { CustomColorPicker } from "@web/components/color_picker/custom_color_picker/custom_color_picker";
import { registry } from "@web/core/registry";

test("basic rendering", async () => {
    await mountWithCleanup(ColorPicker, {
        props: {
            state: {
                selectedColor: "",
                defaultTab: "",
            },
            getUsedCustomColors: () => /** @type {string[]} */ ([]),
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
    expect(".o_font_color_selector .o_colorpicker_section .o_color_button").toHaveCount(
        5,
    );
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]",
    ).toHaveCount(DEFAULT_COLORS.flat().length);
});

test("basic rendering with selected color", async () => {
    await mountWithCleanup(ColorPicker, {
        props: {
            state: {
                selectedColor: "#B5D6A5",
                defaultTab: "",
            },
            getUsedCustomColors: () => /** @type {string[]} */ ([]),
            applyColor() {},
            applyColorPreview() {},
            applyColorResetPreview() {},
            colorPrefix: "",
        },
    });
    expect(".o_font_color_selector").toHaveCount(1);
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]",
    ).toHaveCount(DEFAULT_COLORS.flat().length);
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color='#B5D6A5'].selected",
    ).toHaveCount(1);
});

test("keyboard navigation", async () => {
    await mountWithCleanup(ColorPicker, {
        props: {
            state: {
                selectedColor: "",
                defaultTab: "",
            },
            getUsedCustomColors: () => /** @type {string[]} */ ([]),
            applyColor() {},
            applyColorPreview() {},
            applyColorResetPreview() {},
            colorPrefix: "",
        },
    });
    await click(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:first-of-type",
    );
    await animationFrame();
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:first-of-type",
    ).toBeFocused();

    await press("arrowright");
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:nth-of-type(2)",
    ).toBeFocused();

    await press("enter");
    await animationFrame();
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:nth-of-type(2)",
    ).toHaveClass("selected");

    await press("arrowleft");
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:first-of-type",
    ).toBeFocused();

    await press("arrowleft");
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:first-of-type",
    ).toBeFocused();

    await press("arrowdown");
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:nth-of-type(9)",
    ).toBeFocused();

    await press("arrowup");
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:first-of-type",
    ).toBeFocused();

    await click(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:nth-of-type(8)",
    );
    await animationFrame();

    await press("arrowright");
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:nth-of-type(9)",
    ).toBeFocused();

    await press("arrowleft");
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:nth-of-type(8)",
    ).toBeFocused();

    await click(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:last-of-type",
    );
    await animationFrame();
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:last-of-type",
    ).toBeFocused();

    await press("arrowright");
    expect(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:last-of-type",
    ).toBeFocused();
});

test("colorpicker inside the builder are linked to the builder theme colors", async () => {
    await mountWithCleanup(ColorPicker, {
        props: {
            state: {
                selectedColor: "",
                defaultTab: "",
            },
            getUsedCustomColors: () => /** @type {string[]} */ ([]),
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
            getUsedCustomColors: () => /** @type {string[]} */ ([]),
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

test("custom color picker does not mutate its props", async () => {
    const picker = await mountWithCleanup(CustomColorPicker, {
        props: { defaultColor: "#FF0000", defaultOpacity: 0.5 },
    });
    expect(picker.props.defaultColor).toBe("#FF0000");
    expect(picker.props.defaultOpacity).toBe(0.5);
    expect(picker.defaultOpacity).toBe(50);
    expect(picker.defaultColor).toBe("#FF000080");
    expect(picker.selectedColor).toBe("#FF000080");
});

test("should preserve color slider when picking max lightness color", async () => {
    class TestColorPicker extends Component {
        static template = xml`
            <div style="width: 222px">
                <CustomColorPicker selectedColor="this.state.color" onColorPreview.bind="this.onColorChange" onColorSelect.bind="this.onColorChange"/>
            </div>`;
        static components = { CustomColorPicker };
        static props = ["*"];
        setup() {
            this.state = useState({
                color: "#FFFF00",
            });
        }
        onColorChange({ cssColor }) {
            this.state.color = cssColor;
        }
    }
    await mountWithCleanup(TestColorPicker);
    const colorPickerArea = queryOne(".o_color_pick_area");
    const colorPickerRect = colorPickerArea.getBoundingClientRect();

    const clientX = colorPickerRect.left + colorPickerRect.width / 2;
    const clientY = colorPickerRect.top;
    manuallyDispatchProgrammaticEvent(colorPickerArea, "pointerdown", {
        clientX,
        clientY,
    });
    manuallyDispatchProgrammaticEvent(colorPickerArea, "pointerup", {
        clientX,
        clientY,
    });

    await animationFrame();
    expect(colorPickerArea).toHaveStyle({ backgroundColor: "rgb(255, 255, 0)" });
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
            getUsedCustomColors: () => /** @type {string[]} */ ([]),
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

test("useColorPicker commits the previewed custom color on close without a caller onClose", async () => {
    /** @type {Record<string, any>} */
    const pickerOptions = {};
    class Host extends Component {
        static template = xml`<button class="test-color-btn" t-ref="colorButton">color</button>`;
        static props = ["*"];
        setup() {
            this.colorState = useState({
                selectedColor: "#FF0000",
                defaultTab: "custom",
            });
            this.picker = useColorPicker(
                "colorButton",
                {
                    state: this.colorState,
                    getUsedCustomColors: () => /** @type {string[]} */ ([]),
                    applyColor: () => expect.step("applyColor"),
                    applyColorPreview: () => {},
                    applyColorResetPreview: () => {},
                    colorPrefix: "",
                },
                pickerOptions,
            );
        }
    }
    const comp = await mountWithCleanup(Host);
    await click(".test-color-btn");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);
    expect(".o_color_pick_area").toHaveCount(1);

    const colorPickerArea = queryOne(".o_color_pick_area");
    const colorPickerRect = colorPickerArea.getBoundingClientRect();
    const clientX = colorPickerRect.left + colorPickerRect.width / 2;
    const clientY = colorPickerRect.top + colorPickerRect.height / 2;
    manuallyDispatchProgrammaticEvent(colorPickerArea, "pointerdown", {
        clientX,
        clientY,
    });
    manuallyDispatchProgrammaticEvent(colorPickerArea, "pointerup", {
        clientX,
        clientY,
    });
    await animationFrame();
    expect.verifySteps([]);

    /** @type {any} */ (comp).picker.close();
    await animationFrame();
    expect.verifySteps(["applyColor"]);
    expect("onClose" in pickerOptions).toBe(false);
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
            getUsedCustomColors: () => /** @type {string[]} */ ([]),
            applyColor() {},
            applyColorPreview() {},
            applyColorResetPreview() {},
            colorPrefix: "",
        },
    });
    expect(".o_color_button[data-color='900']").toHaveClass("selected");
});

test("the used-custom-colours list follows what has been applied", async () => {
    const used = [];
    const picker = await mountWithCleanup(ColorPicker, {
        props: {
            state: { selectedColor: "", defaultTab: "" },
            getUsedCustomColors: () => [...used],
            applyColor(color) {
                used.push(color);
            },
            applyColorPreview() {},
            applyColorResetPreview() {},
            colorPrefix: "",
        },
    });
    expect(picker.usedCustomColors).toEqual([]);

    picker.selectColor("#FF0000");
    expect(picker.usedCustomColors).toEqual(["#FF0000"]);
});

test("a preview that moves focus off the swatch does not re-enter onColorFocusin", async () => {
    let previews = 0;
    await mountWithCleanup(ColorPicker, {
        props: {
            state: { selectedColor: "", defaultTab: "" },
            getUsedCustomColors: () => /** @type {string[]} */ ([]),
            applyColor() {},
            applyColorPreview() {
                previews++;
                if (previews > 5) {
                    return;
                }
                /** @type {HTMLElement | null} */ (document.activeElement)?.blur();
            },
            applyColorResetPreview() {},
            colorPrefix: "",
        },
    });

    queryOne(
        ".o_font_color_selector .o_color_section .o_color_button[data-color]:first-of-type",
    ).focus();
    await animationFrame();

    expect(previews).toBe(1);
});

test("useColorPicker re-reads its props on every open when given a getter", async () => {
    /** @type {string[]} */
    const opened = [];
    let prefix = "first-";
    class Parent extends Component {
        static template = xml`<button t-ref="root">pick</button>`;
        static props = ["*"];
        setup() {
            this.picker = useColorPicker("root", () => ({
                state: { selectedColor: "", defaultTab: "" },
                getUsedCustomColors: () => /** @type {string[]} */ ([]),
                applyColor: () => {},
                applyColorPreview: () => {},
                applyColorResetPreview: () => {},
                colorPrefix: prefix,
            }));
        }
    }
    patchWithCleanup(ColorPicker.prototype, {
        setup() {
            opened.push(this.props.colorPrefix);
            return super.setup();
        },
    });

    await mountWithCleanup(Parent);
    await contains("button").click();
    await animationFrame();
    expect(opened).toEqual(["first-"]);

    await contains("button").click();
    await animationFrame();
    prefix = "second-";
    await contains("button").click();
    await animationFrame();
    expect(opened).toEqual(["first-", "second-"]);
});

/** @param {string} tab */
async function focusCycleOnSwatch(tab) {
    /** @type {string[]} */
    const applied = [];
    await mountWithCleanup(ColorPicker, {
        props: {
            state: { selectedColor: "#FF0000", defaultTab: tab },
            getUsedCustomColors: () => ["#123456", "#654321"],
            applyColor() {},
            applyColorPreview: (/** @type {string} */ c) =>
                applied.push(`preview:${c}`),
            applyColorResetPreview: () => applied.push("reset"),
            colorPrefix: "",
        },
    });
    const [swatch, sibling] = queryAll(
        ".o_colorpicker_section .o_color_button[data-color]",
    );
    /** @param {(el: HTMLElement) => void} act */
    const record = async (act) => {
        applied.length = 0;
        act(swatch);
        await animationFrame();
        return [...applied];
    };
    return {
        focusedOnce: await record((el) =>
            el.dispatchEvent(new FocusEvent("focusin", { bubbles: true })),
        ),
        leftForSibling: await record((el) =>
            el.dispatchEvent(
                new FocusEvent("focusout", { bubbles: true, relatedTarget: sibling }),
            ),
        ),
        focusedAgain: await record((el) =>
            el.dispatchEvent(new FocusEvent("focusin", { bubbles: true })),
        ),
    };
}

test("the solid tab re-previews a swatch focused, left and focused again", async () => {
    const cycle = await focusCycleOnSwatch("solid");
    expect(cycle.focusedOnce.length).toBe(1);
    expect(cycle.leftForSibling).toEqual(["reset"]);
    expect(cycle.focusedAgain.length).toBe(1);
});

test("the custom tab re-previews a swatch focused, left and focused again", async () => {
    const cycle = await focusCycleOnSwatch("custom");
    expect(cycle.focusedOnce.length).toBe(1);
    expect(cycle.leftForSibling).toEqual(["reset"]);
    expect(cycle.focusedAgain.length).toBe(1);
});

test("a colour applied from the hex input is offered as a swatch on the next apply", async () => {
    /** @type {Set<string>} */
    const applied = new Set();
    await mountWithCleanup(ColorPicker, {
        props: {
            state: { selectedColor: "", defaultTab: "custom" },
            getUsedCustomColors: () => [...applied],
            applyColor: (/** @type {string} */ color) => applied.add(color),
            applyColorPreview() {},
            applyColorResetPreview() {},
            colorPrefix: "",
        },
    });
    expect(".o_colorpicker_section:first .o_color_button[data-color]").toHaveCount(0);

    await contains(".o_hex_input").edit("#123456");
    await contains(".o_hex_input").edit("#654321");
    expect(applied.size).toBe(2);
    expect(
        ".o_colorpicker_section:first .o_color_button[data-color='#123456']",
    ).toHaveCount(1);
});
