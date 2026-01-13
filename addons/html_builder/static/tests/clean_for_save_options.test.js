import { addBuilderOption, setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { expect, test, describe } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains, onRpc } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

test("clean for save of option with selector that matches an element on the page", async () => {
    onRpc("ir.ui.view", "save_snippet", () => true);
    addBuilderOption({
        selector: ".test-options-target",
        Component: class extends BaseOptionComponent {
            static template = xml`
                <BuilderButtonGroup>
                    <BuilderButton classAction="'x'"/>
                </BuilderButtonGroup>
            `;
            static cleanForSave() {
                expect.step("clean for save option");
            }
        },
    });
    await setupHTMLBuilder(`<div class="test-options-target" data-snippet="s_test">a</div>`);
    await contains(":iframe .test-options-target").click();
    // Add an option to mark the document as 'dirty' and trigger a "clean for
    // save" at the save of the page.
    await contains("[data-class-action='x']").click();
    await contains("button.oe_snippet_save").click();
    expect.verifySteps(["clean for save option"]);
});

test("clean for save of option with selector and exclude that matches an element on the page", async () => {
    onRpc("ir.ui.view", "save_snippet", () => true);
    addBuilderOption({
        selector: ".test-options-target",
        exclude: "div",
        Component: class extends BaseOptionComponent {
            static template = xml`
                <BuilderButtonGroup>
                    <BuilderButton classAction="'x'"/>
                </BuilderButtonGroup>
            `;
            cleanForSave = (_) => {
                expect.step("clean for save option");
            };
        },
    });
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderButtonGroup>
                <BuilderButton classAction="'y'"/>
            </BuilderButtonGroup>
        `,
    });
    await setupHTMLBuilder(`<div class="test-options-target" data-snippet="s_test">a</div>`);
    await contains(":iframe .test-options-target").click();
    // Add an option to mark the document as 'dirty' and trigger a "clean for
    // save" at the save of the page.
    await contains("[data-class-action='y']").click();
    await contains("button.oe_snippet_save").click();
    // Do not expect for a clean for save as the element on the page matches the
    // 'exclude' of the option having the 'cleanForSave'.
    expect.verifySteps([]);
});
