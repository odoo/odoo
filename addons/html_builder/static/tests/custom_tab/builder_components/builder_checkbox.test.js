import { addBuilderOption, setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { expect, test, describe } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

test("Click on checkbox", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderCheckbox classAction="'checkbox-action'"/>`;
        }
    );
    const { getEditableContent } = await setupHTMLBuilder(`<p class="test-options-target">b</p>`);
    const editableContent = getEditableContent();

    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    expect(".o-checkbox .form-check-input:checked").toHaveCount(0);
    expect(editableContent).toHaveInnerHTML(`<p class="test-options-target">b</p>`);

    await contains(".o-checkbox").click();
    expect(".o-checkbox .form-check-input:checked").toHaveCount(1);
    expect(editableContent).toHaveInnerHTML(`<p class="test-options-target checkbox-action">b</p>`);

    await contains(".o-checkbox").click();
    expect(".o-checkbox .form-check-input:checked").toHaveCount(0);
    expect(editableContent).toHaveInnerHTML(`<p class="test-options-target">b</p>`);
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
            static template = xml`<BuilderCheckbox classAction="'checkbox-action'" applyTo="'.my-custom-class'"/>`;
        }
    );
    const { getEditableContent } = await setupHTMLBuilder(
        `<div class="parent-target"><p class="child-target b">b</p></div>`
    );
    const editableContent = getEditableContent();

    await contains(":iframe .parent-target").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="parent-target"><p class="child-target b">b</p></div>`
    );
    expect("[data-class-action='my-custom-class']").not.toHaveClass("active");
    expect(".options-container .o-checkbox").toHaveCount(0);

    await contains("[data-class-action='my-custom-class']").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="parent-target"><p class="child-target b my-custom-class">b</p></div>`
    );
    expect("[data-class-action='my-custom-class']").toHaveClass("active");
    expect(".options-container .o-checkbox").toHaveCount(1);
});

test("click on BuilderCheckbox with inverseAction", async () => {
    addBuilderOption(
        class extends BaseOptionComponent {
            static selector = ".test-options-target";
            static template = xml`<BuilderCheckbox classAction="'my-custom-class'" inverseAction="true"/>`;
        }
    );
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(":iframe .test-options-target").not.toHaveClass("my-custom-class");
    expect(".o-checkbox .form-check-input:checked").toHaveCount(1);

    await contains(".o-checkbox").click();
    expect(":iframe .test-options-target").toHaveClass("my-custom-class");
    expect(".o-checkbox .form-check-input:checked").toHaveCount(0);
});
