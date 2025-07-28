import {
    addBuilderAction,
    addBuilderOption,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { expect, test, describe } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

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
            static template = xml`<BuilderTextInput applyTo="'.my-custom-class'" action="'customAction'"/>`;
        }
    );
    addBuilderAction({
        customAction: class extends BuilderAction {
            static id = "customAction";
            getValue() {
                return "customValue";
            }
        },
    });

    const { getEditableContent } = await setupHTMLBuilder(
        `<div class="parent-target"><div class="child-target">b</div></div>`
    );
    const editableContent = getEditableContent();
    await contains(":iframe .parent-target").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="parent-target"><div class="child-target">b</div></div>`
    );
    expect("[data-class-action='my-custom-class']").not.toHaveClass("active");
    expect("[data-action-id='customAction']").toHaveCount(0);

    await contains("[data-class-action='my-custom-class']").click();
    expect(editableContent).toHaveInnerHTML(
        `<div class="parent-target"><div class="child-target my-custom-class">b</div></div>`
    );
    expect("[data-class-action='my-custom-class']").toHaveClass("active");
    expect("[data-action-id='customAction']").toHaveCount(1);
    expect("[data-action-id='customAction'] input").toHaveValue("customValue");
});
