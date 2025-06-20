import { expect, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import {
    addActionOption,
    addOption,
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "../../website_helpers";
import { BuilderAction } from "@html_builder/core/builder_action";

defineWebsiteModels();

test("hide/display base on applyTo", async () => {
    addOption({
        selector: ".parent-target",
        template: xml`<BuilderButton applyTo="'.child-target'" classAction="'my-custom-class'"/>`,
    });
    addOption({
        selector: ".parent-target",
        template: xml`<BuilderTextInput applyTo="'.my-custom-class'" action="'customAction'"/>`,
    });
    addActionOption({
        customAction: class extends BuilderAction {
            static id = "customAction";
            getValue() {
                return "customValue";
            }
        },
    });

    const { getEditableContent } = await setupWebsiteBuilder(
        `<div class="parent-target"><div class="child-target">b</div></div>`
    );
    const editableContent = getEditableContent();
    await contains(":iframe .parent-target").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="parent-target"><div class="child-target o-paragraph">b</div></div>`
    );
    expect("[data-class-action='my-custom-class']").not.toHaveClass("active");
    expect("[data-action-id='customAction']").toHaveCount(0);

    await contains("[data-class-action='my-custom-class']").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="parent-target"><div class="child-target o-paragraph my-custom-class">b</div></div>`
    );
    expect("[data-class-action='my-custom-class']").toHaveClass("active");
    expect("[data-action-id='customAction']").toHaveCount(1);
    expect("[data-action-id='customAction'] input").toHaveValue("customValue");
});
