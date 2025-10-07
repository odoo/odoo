import { addBuilderOption, setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { expect, test, describe } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

test("clean for save of option with selector that matches an element on the page", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
                <BuilderButtonGroup>
                    <BuilderButton classAction="'x'"/>
                </BuilderButtonGroup>
            `,
        cleanForSave: (_) => {
            expect.step("clean for save option");
        },
    });
    const { getEditor } = await setupHTMLBuilder(`<div class="test-options-target">a</div>`);
    const editor = getEditor();
    await contains(":iframe .test-options-target").click();
    // Add an option to mark the document as 'dirty' and trigger a "clean for
    // save" at the save of the page.
    await contains("[data-class-action='x']").click();
    await editor.shared.savePlugin.save();
    expect.verifySteps(["clean for save option"]);
});

test("clean for save of option with selector and exclude that matches an element on the page", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
                <BuilderButtonGroup>
                    <BuilderButton classAction="'x'"/>
                </BuilderButtonGroup>
            `,
        exclude: "div",
        cleanForSave: (_) => {
            expect.step("clean for save option");
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
    const { getEditor } = await setupHTMLBuilder(`<div class="test-options-target">a</div>`);
    const editor = getEditor();
    await contains(":iframe .test-options-target").click();
    // Add an option to mark the document as 'dirty' and trigger a "clean for
    // save" at the save of the page.
    await contains("[data-class-action='y']").click();
    await editor.shared.savePlugin.save();
    // Do not expect for a clean for save as the element on the page matches the
    // 'exclude' of the option having the 'cleanForSave'.
    expect.verifySteps([]);
});
