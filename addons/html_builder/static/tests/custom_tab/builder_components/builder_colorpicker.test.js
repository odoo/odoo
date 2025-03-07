import { expect, test } from "@odoo/hoot";
import { click, hover, press } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import {
    addActionOption,
    addOption,
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "../../website_helpers";

defineWebsiteModels();

test("should apply backgroundColor to the editing element", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderColorPicker styleAction="'background-color'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    await contains(".we-bg-options-container .o_we_color_preview").click();
    await click(".o-overlay-item [data-color='o-color-1']");
    expect(":iframe .test-options-target").toHaveClass("test-options-target bg-o-color-1");
});

test("should apply color to the editing element", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderColorPicker styleAction="'color'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    await contains(".we-bg-options-container .o_we_color_preview").click();
    await click(".o-overlay-item [data-color='o-color-1']");
    expect(":iframe .test-options-target").toHaveClass("test-options-target text-o-color-1");
});

test("hide/display base on applyTo", async () => {
    addOption({
        selector: ".parent-target",
        template: xml`<BuilderButton applyTo="'.child-target'" classAction="'my-custom-class'"/>`,
    });
    addOption({
        selector: ".parent-target",
        template: xml`<BuilderColorPicker applyTo="'.my-custom-class'" styleAction="'background-color'"/>`,
    });
    const { getEditableContent } = await setupWebsiteBuilder(
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
        `<div class="parent-target"><div class="child-target b my-custom-class o-paragraph">b</div></div>`
    );
    expect("[data-class-action='my-custom-class']").toHaveClass("active");
    expect(".options-container .o_we_color_preview").toHaveCount(1);
});

test("apply color to a different style than color or backgroundColor", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderColorPicker styleAction="'border-top-color'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
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
    addActionOption({
        customAction: {
            load: async () => {
                expect.step("load");
            },
            apply: async ({ editingElement }) => {
                expect.step(
                    `apply ${getComputedStyle(editingElement).getPropertyValue(styleName)}`
                );
            },
        },
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderColorPicker styleAction="'${styleName}'" action="'customAction'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    await contains(".we-bg-options-container .o_we_color_preview").click();
    await contains(".o-overlay-item [data-color='#FF0000']").click();
    // 3 times for hover (preview), focus (preview), click
    expect.verifySteps([
        "load",
        "apply rgb(255, 0, 0)",
        "load",
        "apply rgb(255, 0, 0)",
        "load",
        "apply rgb(255, 0, 0)",
    ]);
});

test("should revert preview on escape", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderColorPicker styleAction="'background-color'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
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
    addActionOption({
        customAction: {
            getValue: ({ editingElement }) => {
                expect.step("getValue");
                return editingElement.dataset.color;
            },
            apply: ({ editingElement, value }) => {
                editingElement.dataset.color = value;
            },
        },
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderColorPicker action="'customAction'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    await contains(".we-bg-options-container .o_we_color_preview").click();
    await contains(".o-overlay-item button:contains('Custom')").click();
    expect.verifySteps(["getValue"]);
    expect(".o-overlay-item .o_hex_input").toHaveValue("#FFFFFF");
    expect(":iframe .test-options-target").not.toHaveAttribute("data-color");
    await contains(".o-overlay-item .o_color_pick_area").click({ top: "50%", left: "50%" });
    expect(".o-overlay-item .o_hex_input").not.toHaveValue("#FFFFFF");
    expect(":iframe .test-options-target").toHaveAttribute("data-color");
    expect.verifySteps(["getValue"]);
});
