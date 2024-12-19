import { expect, test } from "@odoo/hoot";
import { animationFrame, click, fill, queryFirst } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import {
    addActionOption,
    addOption,
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "../../helpers";

defineWebsiteModels();

test("should get the initial value of the input", async () => {
    addActionOption({
        customAction: {
            getValue: ({ editingElement }) => editingElement.innerHTML,
            apply: ({ param }) => {
                expect.step(`customAction ${param}`);
            },
        },
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderNumberInput action="'customAction'"/>`,
    });
    await setupWebsiteBuilder(`
                <div class="test-options-target">10</div>
            `);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    const input = queryFirst(".options-container input");
    expect(input).toHaveValue("10");
});
test("should preview changes", async () => {
    addActionOption({
        customAction: {
            getValue: ({ editingElement }) => editingElement.innerHTML,
            apply: ({ editingElement, value }) => {
                expect.step(`customAction ${value}`);
                editingElement.innerHTML = value;
            },
        },
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderNumberInput action="'customAction'"/>`,
    });
    await setupWebsiteBuilder(`
                <div class="test-options-target">10</div>
            `);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    await click(".options-container input");
    await fill("2");
    expect.verifySteps(["customAction 102"]);
    expect(":iframe .test-options-target").toHaveInnerHTML("102");
    expect(".o-snippets-top-actions .fa-undo").not.toBeEnabled();
    expect(".o-snippets-top-actions .fa-repeat").not.toBeEnabled();
});
test("should commit changes", async () => {
    addActionOption({
        customAction: {
            getValue: ({ editingElement }) => editingElement.innerHTML,
            apply: ({ editingElement, value }) => {
                expect.step(`customAction ${value}`);
                editingElement.innerHTML = value;
            },
        },
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderNumberInput action="'customAction'"/>`,
    });
    await setupWebsiteBuilder(`
                <div class="test-options-target">10</div>
            `);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    await click(".options-container input");
    await fill("2");
    expect.verifySteps(["customAction 102"]);
    expect(":iframe .test-options-target").toHaveInnerHTML("102");
    await click(document.body);
    await animationFrame();
    expect.verifySteps(["customAction 102"]);
    expect(".o-snippets-top-actions .fa-undo").toBeEnabled();
    expect(".o-snippets-top-actions .fa-repeat").not.toBeEnabled();
});
test("hide/display base on applyTo", async () => {
    addOption({
        selector: ".parent-target",
        template: xml`<BuilderButton applyTo="'.child-target'" classAction="'my-custom-class'"/>`,
    });
    addOption({
        selector: ".parent-target",
        template: xml`<BuilderNumberInput applyTo="'.my-custom-class'" action="'customAction'"/>`,
    });
    addActionOption({
        customAction: {
            getValue: () => "customValue",
        },
    });

    const { getEditor } = await setupWebsiteBuilder(
        `<div class="parent-target"><div class="child-target">b</div></div>`
    );
    const editor = getEditor();
    await contains(":iframe .parent-target").click();
    expect(editor.editable).toHaveInnerHTML(
        `<div class="parent-target"><div class="child-target">b</div></div>`
    );
    expect("[data-class-action='my-custom-class']").not.toHaveClass("active");
    expect("[data-action-id='customAction']").toHaveCount(0);

    await contains("[data-class-action='my-custom-class']").click();
    expect(editor.editable).toHaveInnerHTML(
        `<div class="parent-target"><div class="child-target my-custom-class">b</div></div>`
    );
    expect("[data-class-action='my-custom-class']").toHaveClass("active");
    expect("[data-action-id='customAction']").toHaveCount(1);
    expect("[data-action-id='customAction'] input").toHaveValue("customValue");
});
