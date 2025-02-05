import { expect, test } from "@odoo/hoot";
import { animationFrame, click, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
    setupWebsiteBuilderWithDummySnippet,
} from "./helpers";

defineWebsiteModels();

const initialDropZone = (hovered = false) => `
    <div class="oe_drop_zone oe_insert${
        hovered ? " o_dropzone_highlighted" : ""
    }" data-editor-message="DRAG BUILDING BLOCKS HERE"></div>`;

async function confirmSnippet() {
    expect(".o_add_snippet_dialog").toHaveCount(1);
    await waitFor(".o_add_snippet_dialog iframe.show.o_add_snippet_iframe", { timeout: 500 });
    const previewSelector =
        ".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap";
    await waitFor(previewSelector);
    await click(previewSelector);
    await animationFrame();
}

test("initial dropzone is visible after opening edit sidebar", async () => {
    const { getEditableContent } = await setupWebsiteBuilder("");

    const editableContent = getEditableContent();
    expect(editableContent).toHaveInnerHTML(initialDropZone());
});

test("drop beside dropzone inserts the snippet", async () => {
    const { getEditableContent, snippetContent } = await setupWebsiteBuilderWithDummySnippet();
    const editableContent = getEditableContent();
    expect(editableContent).toHaveInnerHTML(initialDropZone());
    const { moveTo, drop } = await contains(
        `.o-snippets-menu [data-category="snippet_groups"] div`
    ).drag();
    await moveTo(editableContent.ownerDocument.body);
    // The dropzone is not hovered, so not highlighted.
    expect(editableContent).toHaveInnerHTML(initialDropZone());
    await drop();
    await confirmSnippet();
    expect(".o_add_snippet_dialog").toHaveCount(0);
    expect(editableContent).toHaveInnerHTML(snippetContent);
});

test("initial dropzone appears after undo", async () => {
    const { getEditableContent, snippetContent } = await setupWebsiteBuilderWithDummySnippet();
    const editableContent = getEditableContent();
    expect(editableContent).toHaveInnerHTML(initialDropZone());

    const { moveTo, drop } = await contains(
        `.o-snippets-menu [data-category="snippet_groups"] div`
    ).drag();
    await moveTo(editableContent);
    expect(editableContent).toHaveInnerHTML(initialDropZone(true));
    await drop();
    await confirmSnippet();
    expect(".o_add_snippet_dialog").toHaveCount(0);
    expect(editableContent).toHaveInnerHTML(snippetContent);

    // Undo should display the dropzone
    await click(".o-snippets-menu button.fa-undo");
    await animationFrame();
    expect(editableContent).toHaveInnerHTML(initialDropZone());
});

test("initial dropzone appears after delete & redo", async () => {
    const startContent = `<section class="s_test"></section>`;
    const { getEditableContent } = await setupWebsiteBuilder(startContent);
    const editableContent = getEditableContent();

    expect(editableContent).toHaveInnerHTML(startContent);
    await click(editableContent.querySelector(".s_test"));
    await animationFrame();
    // Delete should display the initial dropzone
    await click(".oe_snippet_remove.fa-trash");
    await animationFrame();
    expect(editableContent).toHaveInnerHTML(initialDropZone());

    // Undo, then redo should display the initial dropzone
    await click(".o-snippets-menu button.fa-undo");
    await animationFrame();
    expect(editableContent).toHaveInnerHTML(startContent);
    await click(".o-snippets-menu button.fa-repeat");
    await animationFrame();
    expect(editableContent).toHaveInnerHTML(initialDropZone());
});
