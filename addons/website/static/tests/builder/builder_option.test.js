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

test("Undo/Redo correctly restore the container target", async () => {
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
    const { getEditor } = await setupWebsiteBuilder(`
        <div class="test-options-target target1">
            Homepage
        </div>
        <div class="test-options-target target2">
            Homepage2
        </div>

    `);
    const editor = getEditor();

    await contains(":iframe .target1").click();
    expectOptionContainerToInclude(editor, queryOne(":iframe .target1"));
    await contains("[data-action-id='customAction']").click();
    await contains(":iframe .target2").click();
    expectOptionContainerToInclude(editor, queryOne(":iframe .target2"));

    await contains(".o-snippets-top-actions .fa-undo").click();
    expectOptionContainerToInclude(editor, queryOne(":iframe .target1"));
    await contains(".o-snippets-top-actions .fa-repeat").click();
    expectOptionContainerToInclude(editor, queryOne(":iframe .target2"));
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
