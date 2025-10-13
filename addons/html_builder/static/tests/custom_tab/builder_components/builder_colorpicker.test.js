import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { undo } from "@html_editor/../tests/_helpers/user_actions";
import { before, describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, Deferred, hover, press, tick, waitFor } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

test("should apply backgroundColor to the editing element", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderColorPicker enabledTabs="['solid']" styleAction="'background-color'"/>`,
    });
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    await contains(".we-bg-options-container .o_we_color_preview").click();
    await click(".o-overlay-item [data-color='o-color-1']");
    await animationFrame();
    expect(":iframe .test-options-target").toHaveClass("test-options-target bg-o-color-1");
});

test("should apply color to the editing element", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderColorPicker enabledTabs="['solid']" styleAction="'color'"/>`,
    });
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    await contains(".we-bg-options-container .o_we_color_preview").click();
    await click(".o-overlay-item [data-color='o-color-1']");
    await animationFrame();
    expect(":iframe .test-options-target").toHaveClass("test-options-target text-o-color-1");
});

test("hide/display base on applyTo", async () => {
    addBuilderOption({
        selector: ".parent-target",
        template: xml`<BuilderButton applyTo="'.child-target'" classAction="'my-custom-class'"/>`,
    });
    addBuilderOption({
        selector: ".parent-target",
        template: xml`<BuilderColorPicker applyTo="'.my-custom-class'" styleAction="'background-color'"/>`,
    });
    const { getEditableContent } = await setupHTMLBuilder(
        `<div class="parent-target"><p class="child-target b">b</p></div>`
    );
    const editableContent = getEditableContent();
    await contains(":iframe .parent-target").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="parent-target"><p class="child-target b">b</p></div>`
    );
    expect("[data-class-action='my-custom-class']").not.toHaveClass("active");
    expect(".options-container .o_we_color_preview").toHaveCount(0);

    await contains("[data-class-action='my-custom-class']").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="parent-target"><p class="child-target b my-custom-class">b</p></div>`
    );
    expect("[data-class-action='my-custom-class']").toHaveClass("active");
    expect(".options-container .o_we_color_preview").toHaveCount(1);
});

test("apply color to a different style than color or backgroundColor", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderColorPicker enabledTabs="['solid']" styleAction="'border-top-color'"/>`,
    });
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    await contains(".we-bg-options-container .o_we_color_preview").click();
    await contains(".o-overlay-item [data-color='#FF0000']").click();
    expect(":iframe .test-options-target").toHaveStyle({
        borderTopColor: "rgb(255, 0, 0)",
    });
    expect(".we-bg-options-container .o_we_color_preview").toHaveStyle({
        "background-color": "rgb(255, 0, 0)",
    });
});

test("apply custom action", async () => {
    const styleName = "border-top-color";
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            async load() {
                expect.step("load");
            }
            async apply({ editingElement }) {
                expect.step(
                    `apply ${getComputedStyle(editingElement).getPropertyValue(styleName)}`
                );
            }
        },
    });
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderColorPicker enabledTabs="['solid']" styleAction="'${styleName}'" action="'customAction'"/>`,
    });
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    await contains(".we-bg-options-container .o_we_color_preview").click();
    await contains(".o-overlay-item [data-color='#FF0000']").click();
    // Applied twice for hover (preview) and click (commit).
    expect.verifySteps(["load", "apply rgb(255, 0, 0)", "load", "apply rgb(255, 0, 0)"]);
});

test("apply custom async action", async () => {
    const def = new Deferred();
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            getValue() {
                return "";
            }
            async apply({ editingElement }) {
                await def;
                editingElement.classList.add("applied");
            }
        },
    });
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderColorPicker action="'customAction'" enabledTabs="['solid']"/>
            <BuilderButton classAction="'test'" preview="false"/>
            `,
    });
    const { getEditor } = await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    const editor = getEditor();
    await contains(":iframe .test-options-target").click();
    await contains(".we-bg-options-container .o_we_color_preview").click();
    await contains(".o-overlay-item [data-color='#FF0000']").click();
    await contains("[data-class-action='test']").click();
    expect(":iframe .test-options-target").not.toHaveClass("test");
    expect(":iframe .test-options-target").not.toHaveClass("applied");

    def.resolve();
    await tick();
    expect(":iframe .test-options-target").toHaveClass("test");
    expect(":iframe .test-options-target").toHaveClass("applied");

    undo(editor);
    expect(":iframe .test-options-target").not.toHaveClass("test");
    expect(":iframe .test-options-target").toHaveClass("applied");

    undo(editor);
    expect(":iframe .test-options-target").not.toHaveClass("test");
    expect(":iframe .test-options-target").not.toHaveClass("applied");
});

test("should revert preview on escape", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderColorPicker enabledTabs="['solid']" styleAction="'background-color'"/>`,
    });
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(":iframe .test-options-target").toHaveStyle({ "background-color": "rgba(0, 0, 0, 0)" });
    expect(".options-container").toBeDisplayed();
    await contains(".we-bg-options-container .o_we_color_preview").click();
    await hover(".o-overlay-item [data-color='#FF0000']");
    expect(":iframe .test-options-target").toHaveStyle({ "background-color": "rgb(255, 0, 0)" });
    await press("escape");
    expect(":iframe .test-options-target").toHaveStyle({ "background-color": "rgba(0, 0, 0, 0)" });
});

test("should mark default color as selected when it is selected", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderColorPicker enabledTabs="['custom']" styleAction="'background-color'"/>`,
    });
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    await contains(".we-bg-options-container .o_we_color_preview").click();
    await contains(".o-overlay-item [data-color='900']").click();
    expect(":iframe .test-options-target").toHaveClass("bg-900");
    await contains(".we-bg-options-container .o_we_color_preview").click();
    expect(".o-overlay-item [data-color='900']").toHaveClass("selected");
});

test("should apply transparent color if no color is defined", async () => {
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            getValue({ editingElement }) {
                expect.step("getValue");
                return editingElement.dataset.color;
            }
            apply({ editingElement, value }) {
                expect.step("apply");
                editingElement.dataset.color = value;
            }
        },
    });
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderColorPicker action="'customAction'"/>`,
    });
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    await contains(".we-bg-options-container .o_we_color_preview").click();
    await contains(".o-overlay-item button:contains('Custom')").click();
    expect.verifySteps(["getValue"]);
    expect(".o-overlay-item .o_hex_input").toHaveValue("#FFFFFF00");
    expect(":iframe .test-options-target").not.toHaveAttribute("data-color");
    await contains(".o-overlay-item .o_color_pick_area").click({ top: "50%", left: "50%" });
    expect(".o-overlay-item .o_hex_input").not.toHaveValue("#FFFFFF00");
    expect(":iframe .test-options-target").toHaveAttribute("data-color");
    expect.verifySteps(["apply"]); // Preview
    await contains(".options-container-header").click(); // Close the popover by clicking outside.
    expect.verifySteps(["apply", "getValue"]); // Commit
});

describe("Custom colorpicker: preview and commit", () => {
    before(() => {
        addBuilderAction({
            customAction: class extends BuilderAction {
                static id = "customAction";
                getValue({ editingElement }) {
                    return editingElement.dataset.color;
                }
                apply({ editingElement, value }) {
                    expect.step("apply");
                    editingElement.dataset.color = value;
                }
            },
        });
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`<BuilderColorPicker action="'customAction'"/>`,
        });
    });

    /****************************************
     *************** POINTER ***************
     ***************************************/

    test("should preview while modifying custom pickers with mouse", async () => {
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        await contains(".we-bg-options-container .o_we_color_preview").click();
        await contains(".o-overlay-item button:contains('Custom')").click();
        expect(":iframe .test-options-target").not.toHaveAttribute("data-color");
        await contains(".o-overlay-item .o_color_pick_area").click({ top: "50%", left: "50%" });
        expect(":iframe .test-options-target").toHaveAttribute("data-color");
        expect.verifySteps(["apply"]); // Only once: preview
        await contains(".o-overlay-item .o_color_slider").click({ top: "50%", left: "50%" });
        expect.verifySteps(["apply"]); // Only once: preview
        await contains(".o-overlay-item .o_opacity_slider").click({ top: "50%", left: "50%" });
        expect.verifySteps(["apply"]); // Only once: preview
        expect(":iframe .test-options-target").toHaveAttribute("data-color");
        // Make sure it was just a preview: close with escape
        await press("escape"); // Undo preview
        await animationFrame();
        expect(":iframe .test-options-target").not.toHaveAttribute("data-color");
    });

    test("should commit when popover is closed by clicking outside", async () => {
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        await contains(".we-bg-options-container .o_we_color_preview").click();
        await contains(".o-overlay-item button:contains('Custom')").click();
        expect(":iframe .test-options-target").not.toHaveAttribute("data-color");
        await contains(".o-overlay-item .o_color_pick_area").click({ top: "50%", left: "50%" });
        expect(":iframe .test-options-target").toHaveAttribute("data-color");
        expect.verifySteps(["apply"]); // Only once: preview
        await contains(".options-container-header").click(); // Close the popover by clicking outside.
        expect.verifySteps(["apply"]); // Commit
        expect(":iframe .test-options-target").toHaveAttribute("data-color");
    });

    /****************************************
     *************** KEYBOARD ***************
     ***************************************/
    const prepareKeyboardSetup = async () => {
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        await contains(".we-bg-options-container .o_we_color_preview").click();
        await waitFor(".o-overlay-item button:contains('Custom')");
        await press("Tab");
        await press("Enter");
        await waitFor(".o-overlay-item .o_color_pick_area");
        expect(":iframe .test-options-target").not.toHaveAttribute("data-color");
        // Press shift+tab until it gets to the colorpicker area.
        for (let i = 0; i < 5; i++) {
            await press("Tab", { shiftKey: true });
        }
        expect(".o-overlay-item .o_color_pick_area .o_picker_pointer").toBeFocused();
    };

    test("should preview while modifying custom pickers with keyboard", async () => {
        await prepareKeyboardSetup();
        await press("ArrowRight");
        await animationFrame();
        expect.verifySteps(["apply"]); // Preview
        await press("ArrowDown");
        await animationFrame();
        expect.verifySteps(["apply"]); // Preview
        expect(":iframe .test-options-target").toHaveAttribute("data-color");
        await press("Tab"); // focus color slider
        expect(".o-overlay-item .o_color_slider .o_slider_pointer").toBeFocused();
        await press("ArrowUp");
        await animationFrame();
        expect.verifySteps(["apply"]); // Preview
        await press("Tab"); // focus opacity slider
        expect(".o-overlay-item .o_opacity_slider .o_opacity_pointer").toBeFocused();
        await press("ArrowDown");
        await animationFrame();
        expect.verifySteps(["apply"]); // Preview
        // Make sure it was just a preview: close with escape
        await press("escape");
        await animationFrame();
        expect(":iframe .test-options-target").not.toHaveAttribute("data-color");
    });

    test("should commit when validating with 'Enter'", async () => {
        await prepareKeyboardSetup();
        await press("ArrowRight");
        await animationFrame();
        expect.verifySteps(["apply"]); // Preview
        await press("ArrowDown");
        await animationFrame();
        expect.verifySteps(["apply"]); // Preview
        expect(":iframe .test-options-target").toHaveAttribute("data-color");
        await press("Enter"); // Validate
        await animationFrame();
        expect.verifySteps(["apply"]); // Commit
        await press("escape");
        await animationFrame();
        expect(":iframe .test-options-target").toHaveAttribute("data-color");
    });
});
