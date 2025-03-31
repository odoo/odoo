import { expect, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "../../website_helpers";

defineWebsiteModels();

test("Click on checkbox", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderCheckbox classAction="'checkbox-action'"/>`,
    });
    const { getEditableContent } = await setupWebsiteBuilder(
        `<div class="test-options-target o-paragraph">b</div>`
    );
    const editableContent = getEditableContent();

    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    expect(".o-checkbox .form-check-input:checked").toHaveCount(0);
    expect(editableContent).toHaveInnerHTML(`<div class="test-options-target o-paragraph">b</div>`);

    await contains(".o-checkbox").click();
    expect(".o-checkbox .form-check-input:checked").toHaveCount(1);
    expect(editableContent).toHaveInnerHTML(
        `<div class="test-options-target o-paragraph checkbox-action">b</div>`
    );

    await contains(".o-checkbox").click();
    expect(".o-checkbox .form-check-input:checked").toHaveCount(0);
    expect(editableContent).toHaveInnerHTML(`<div class="test-options-target o-paragraph">b</div>`);
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
    const { getEditableContent } = await setupWebsiteBuilder(
        `<div class="parent-target"><div class="child-target b">b</div></div>`
    );
    const editableContent = getEditableContent();

    await contains(":iframe .parent-target").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="parent-target"><div class="child-target b o-paragraph">b</div></div>`
    );
    expect("[data-class-action='my-custom-class']").not.toHaveClass("active");
    expect(".options-container .o-checkbox").toHaveCount(0);

    await contains("[data-class-action='my-custom-class']").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="parent-target"><div class="child-target b o-paragraph my-custom-class">b</div></div>`
    );
    expect("[data-class-action='my-custom-class']").toHaveClass("active");
    expect(".options-container .o-checkbox").toHaveCount(1);
});

test("click on BuilderCheckbox with inverseAction", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderCheckbox classAction="'my-custom-class'" inverseAction="true"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(":iframe .test-options-target").not.toHaveClass("my-custom-class");
    expect(".o-checkbox .form-check-input:checked").toHaveCount(1);

    await contains(".o-checkbox").click();
    expect(":iframe .test-options-target").toHaveClass("my-custom-class");
    expect(".o-checkbox .form-check-input:checked").toHaveCount(0);
});
