import { expect, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "../../helpers";

defineWebsiteModels();

test("Click on checkbox", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderCheckbox classAction="'checkbox-action'"/>`,
    });
    const { getEditor } = await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    const editor = getEditor();

    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    expect(".o-checkbox .form-check-input:checked").toHaveCount(0);
    expect(editor.editable).toHaveInnerHTML(`<div class="test-options-target">b</div>`);

    await contains(".o-checkbox").click();
    expect(".o-checkbox .form-check-input:checked").toHaveCount(1);
    expect(editor.editable).toHaveInnerHTML(
        `<div class="test-options-target checkbox-action">b</div>`
    );

    await contains(".o-checkbox").click();
    expect(".o-checkbox .form-check-input:checked").toHaveCount(0);
    expect(editor.editable).toHaveInnerHTML(`<div class="test-options-target">b</div>`);
});
test("hide/display base on applyTo", async () => {
    addOption({
        selector: ".parent-target",
        template: xml`<BuilderButton applyTo="'.child-target'" classAction="'my-custom-class'"/>`,
    });
    addOption({
        selector: ".parent-target",
        template: xml`<BuilderCheckbox classAction="'checkbox-action'" applyTo="'.my-custom-class'"/>`,
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
    expect(".options-container .o-checkbox").toHaveCount(0);

    await contains("[data-class-action='my-custom-class']").click();
    expect(editor.editable).toHaveInnerHTML(
        `<div class="parent-target"><div class="child-target b my-custom-class">b</div></div>`
    );
    expect("[data-class-action='my-custom-class']").toHaveClass("active");
    expect(".options-container .o-checkbox").toHaveCount(1);
});
