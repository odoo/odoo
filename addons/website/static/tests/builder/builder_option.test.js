import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    addActionOption,
    addOption,
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "./website_helpers";
import { xml } from "@odoo/owl";
import { queryOne } from "@odoo/hoot-dom";

function expectOptionContainerToInclude(editor, elem) {
    expect(
        editor.shared["builder-options"].getContainers().map((container) => container.element)
    ).toInclude(elem);
}

defineWebsiteModels();

test("Undo/Redo correctly restores the stored container target", async () => {
    addActionOption({
        customAction: {
            apply: ({ editingElement }) => {
                editingElement.remove();
            },
        },
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderButton action="'customAction'">Test</BuilderButton>`,
    });
    await setupWebsiteBuilder(`
        <div data-name="Target 1" class="test-options-target target1">
            Homepage
        </div>
        <div data-name="Target 2" class="test-options-target target2">
            Homepage2
        </div>

    `);

    await contains(":iframe .target1").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 1");
    await contains("[data-action-id='customAction']").click();
    await contains(":iframe .target2").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 2");

    await contains(".o-snippets-top-actions .fa-undo").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 1");
    await contains(".o-snippets-top-actions .fa-repeat").click();
    expect(".options-container").toHaveCount(0);
});

test("Undo/Redo multiple actions always restores the action container target", async () => {
    addActionOption({
        customAction: {
            apply: ({ editingElement }) => {
                editingElement.classList.add("test");
            },
        },
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderButton action="'customAction'">Test</BuilderButton>`,
    });
    await setupWebsiteBuilder(`
        <div data-name="Target 1" class="test-options-target target1">
            Homepage
        </div>
        <div data-name="Target 2" class="test-options-target target2">
            Homepage2
        </div>

    `);

    await contains(":iframe .target1").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 1");
    await contains("[data-action-id='customAction']").click();
    await contains(":iframe .target2").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 2");
    await contains("[data-action-id='customAction']").click();
    expect(":iframe .test-options-target.test").toHaveCount(2);
    // Undo everything.
    await contains(".o-snippets-top-actions .fa-undo").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 2");
    await contains(".o-snippets-top-actions .fa-undo").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 1");
    expect(":iframe .test-options-target.test").toHaveCount(0);
    // Redo everything.
    await contains(".o-snippets-top-actions .fa-repeat").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 1");
    await contains(".o-snippets-top-actions .fa-repeat").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 2");
    expect(":iframe .test-options-target.test").toHaveCount(2);
});

test("Undo/Redo an action that activates another target restores the old one on undo and the new one on redo", async () => {
    let editor;
    addActionOption({
        customAction: {
            apply: ({ editingElement }) => {
                editingElement.classList.add("test");
                editor.shared["builder-options"].setNextTarget(editingElement.nextElementSibling);
            },
        },
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderButton action="'customAction'">Test</BuilderButton>`,
    });
    const { getEditor } = await setupWebsiteBuilder(`
        <div data-name="Target 1" class="test-options-target target1">
            Homepage
        </div>
        <div data-name="Target 2" class="test-options-target target2">
            Homepage2
        </div>

    `);
    editor = getEditor();

    await contains(":iframe .target1").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 1");
    await contains("[data-action-id='customAction']").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 2");
    // Undo everything.
    await contains(".o-snippets-top-actions .fa-undo").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 1");
    await contains(".o-snippets-top-actions .fa-repeat").click();
    expect(".options-container").toHaveAttribute("data-container-title", "Target 2");
});

test("Container fallback to a valid ancestor if target dissapear", async () => {
    addActionOption({
        customAction: {
            apply: ({ editingElement }) => {
                editingElement.remove();
            },
        },
        ancestorAction: {
            apply: ({ editingElement }) => {
                editingElement.remove();
            },
        },
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderButton action="'customAction'">Test</BuilderButton>`,
    });
    addOption({
        selector: ".test-ancestor",
        template: xml`<BuilderButton action="'ancestorAction'">Ancestor selected</BuilderButton>`,
    });
    const { getEditor } = await setupWebsiteBuilder(`
        <div class="test-ancestor">
            Hey I'm an ancestor
            <div class="test-options-target target1">
                Homepage
            </div>
        </div>

    `);
    const editor = getEditor();

    await contains(":iframe .target1").click();
    expectOptionContainerToInclude(editor, queryOne(":iframe .target1"));
    await contains("[data-action-id='customAction']").click();
    expectOptionContainerToInclude(editor, queryOne(":iframe .test-ancestor"));
    expect("[data-action-id='ancestorAction']").toHaveCount(1);
});

test("Remove element, undo should restore the selection to the removed element", async () => {
    addActionOption({
        customAction: {
            apply: ({ editingElement }) => {
                editingElement.remove();
            },
        },
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderButton action="'customAction'">Test</BuilderButton>`,
        title: "child",
    });
    const { getEditor } = await setupWebsiteBuilder(`
        <div class="test-ancestor">
            Hey I'm an ancestor
            <div class="test-options-target target1">
                Homepage
            </div>
        </div>

    `);
    const editor = getEditor();

    await contains(":iframe .target1").click();
    expectOptionContainerToInclude(editor, queryOne(":iframe .target1"));
    await contains("[data-container-title='child'] button.fa-trash").click();
    await contains(".o-snippets-top-actions .fa-undo").click();
    expectOptionContainerToInclude(editor, queryOne(":iframe .target1"));
});
