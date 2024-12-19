import { expect, test } from "@odoo/hoot";
import { animationFrame, click } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "../../helpers";

defineWebsiteModels();

test("should apply color to the editing element", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderColorpicker/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    await click(".we-bg-options-container .dropdown");
    await animationFrame();
    await click(".o-overlay-item [data-color='o-color-1']");
    expect(":iframe .test-options-target").toHaveClass("test-options-target bg-o-color-1");
});
test("hide/display base on applyTo", async () => {
    addOption({
        selector: ".parent-target",
        template: xml`<BuilderButton applyTo="'.child-target'" classAction="'my-custom-class'"/>`,
    });
    addOption({
        selector: ".parent-target",
        template: xml`<BuilderColorpicker applyTo="'.my-custom-class'"/>`,
    });
    const { getEditor } = await setupWebsiteBuilder(
        `<div class="parent-target"><div class="child-target b">b</div></div>`
    );
    const editor = getEditor();
    await contains(":iframe .parent-target").click();
    expect(editor.editable).toHaveInnerHTML(
        `<div class="parent-target"><div class="child-target b">b</div></div>`
    );
    expect("[data-class-action='my-custom-class']").not.toHaveClass("active");
    expect(".options-container .o_we_color_preview").toHaveCount(0);

    await contains("[data-class-action='my-custom-class']").click();
    expect(editor.editable).toHaveInnerHTML(
        `<div class="parent-target"><div class="child-target b my-custom-class">b</div></div>`
    );
    expect("[data-class-action='my-custom-class']").toHaveClass("active");
    expect(".options-container .o_we_color_preview").toHaveCount(1);
});
