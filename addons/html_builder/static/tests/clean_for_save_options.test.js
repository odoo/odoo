import { expect, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";

defineWebsiteModels();

test("clean for save of option with selector that matches an element on the page", async () => {
    onRpc("ir.ui.view", "save", ({ args }) => true);
    addOption({
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
    await setupWebsiteBuilder(`<div class="test-options-target">a</div>`);
    await contains(":iframe .test-options-target").click();
    // Add an option to mark the document as 'dirty' and trigger a "clean for
    // save" at the save of the page.
    await contains("[data-class-action='x']").click();
    await contains(".o-snippets-top-actions button:contains(Save)").click();
    expect.verifySteps(["clean for save option"]);
});

test("clean for save of option with selector and exclude that matches an element on the page", async () => {
    onRpc("ir.ui.view", "save", ({ args }) => true);
    addOption({
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
    addOption({
        selector: ".test-options-target",
        template: xml`
                <BuilderButtonGroup>
                    <BuilderButton classAction="'y'"/>
                </BuilderButtonGroup>
            `,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">a</div>`);
    await contains(":iframe .test-options-target").click();
    // Add an option to mark the document as 'dirty' and trigger a "clean for
    // save" at the save of the page.
    await contains("[data-class-action='y']").click();
    await contains(".o-snippets-top-actions button:contains(Save)").click();
    // Do not expect for a clean for save as the element on the page matches the
    // 'exclude' of the option having the 'cleanForSave'.
    expect.verifySteps([]);
});
