import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { undo } from "@html_editor/../tests/_helpers/user_actions";
import { expect, test, describe } from "@odoo/hoot";
import { animationFrame, click, Deferred, hover, press, tick } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

test("should apply backgroundColor to the editing element", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderColorPicker enabledTabs="['solid']" styleAction="'background-color'"/>`;
        }
    );
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    await contains(".we-bg-options-container .o_we_color_preview").click();
    await click(".o-overlay-item [data-color='o-color-1']");
    await animationFrame();
    expect(":iframe .test-options-target").toHaveClass("test-options-target bg-o-color-1");
});

test("should apply color to the editing element", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderColorPicker enabledTabs="['solid']" styleAction="'color'"/>`;
        }
    );
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    await contains(".we-bg-options-container .o_we_color_preview").click();
    await click(".o-overlay-item [data-color='o-color-1']");
    await animationFrame();
    expect(":iframe .test-options-target").toHaveClass("test-options-target text-o-color-1");
});

test("hide/display base on applyTo", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".parent-target";
            static template = xml`<BuilderButton applyTo="'.child-target'" classAction="'my-custom-class'"/>`;
        }
    );
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".parent-target";
            static template = xml`<BuilderColorPicker applyTo="'.my-custom-class'" styleAction="'background-color'"/>`;
        }
    );
    const { getEditableContent } = await setupHTMLBuilder(
        `<div class="parent-target"><div class="child-target b">b</div></div>`
    );
    const editableContent = getEditableContent();
    await contains(":iframe .parent-target").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="parent-target"><div class="child-target b o-paragraph">b</div></div>`
    );
    expect("[data-class-action='my-custom-class']").not.toHaveClass("active");
    expect(".options-container .o_we_color_preview").toHaveCount(0);

    await contains("[data-class-action='my-custom-class']").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="parent-target"><div class="child-target b o-paragraph my-custom-class">b</div></div>`
    );
    expect("[data-class-action='my-custom-class']").toHaveClass("active");
    expect(".options-container .o_we_color_preview").toHaveCount(1);
});

test("apply color to a different style than color or backgroundColor", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderColorPicker enabledTabs="['solid']" styleAction="'border-top-color'"/>`;
        }
    );
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
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderColorPicker enabledTabs="['solid']" styleAction="'${styleName}'" action="'customAction'"/>`;
        }
    );
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
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`
                <BuilderColorPicker action="'customAction'" enabledTabs="['solid']"/>
                <BuilderButton classAction="'test'" preview="false"/>
            `;
        }
    );
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
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderColorPicker enabledTabs="['solid']" styleAction="'background-color'"/>`;
        }
    );
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

test("should apply transparent color if no color is defined", async () => {
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            getValue({ editingElement }) {
                expect.step("getValue");
                return editingElement.dataset.color;
            }
            apply({ editingElement, value }) {
                editingElement.dataset.color = value;
            }
        },
    });
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderColorPicker action="'customAction'"/>`;
        }
    );
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
    expect.verifySteps(["getValue"]);
});

test("should open the last used tab", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderColorPicker styleAction="'background-color'"/>`;
        }
    );
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();

    await contains(".we-bg-options-container .o_we_color_preview").click();
    await click(".theme-tab");
    await animationFrame();
    expect(".theme-tab.active").toHaveCount(1);

    await click(".custom-tab");
    await animationFrame();
    await click(".o_red_input");
    await press("enter");
    await press("escape");
    await animationFrame();
    await contains(".we-bg-options-container .o_we_color_preview").click();
    expect(".custom-tab.active").toHaveCount(1);

    await click(".gradient-tab");
    await animationFrame();
    await click(".o_gradient_color_button");
    await animationFrame();
    await contains(".we-bg-options-container .o_we_color_preview").click();
    expect(".gradient-tab.active").toHaveCount(1);

    await click("button[title='Reset']");
    await animationFrame();
    await contains(".we-bg-options-container .o_we_color_preview").click();
    expect(".theme-tab.active").toHaveCount(1);
});
