import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { setupHTMLBuilder } from "./helpers";

describe.current.tags("desktop");

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
    const { contentEl } = await setupHTMLBuilder("");
    expect(contentEl).toHaveInnerHTML(initialDropZone());
});

test("drop beside dropzone inserts the snippet", async () => {
    const { contentEl, snippetContent } = await setupHTMLBuilder();
    expect(contentEl).toHaveInnerHTML(initialDropZone());
    const { moveTo, drop } = await contains(
        `.o-snippets-menu [data-category="snippet_groups"] div`
    ).drag();
    await moveTo(contentEl.ownerDocument.body);
    // The dropzone is not hovered, so not highlighted.
    expect(contentEl).toHaveInnerHTML(initialDropZone());
    await drop();
    await confirmSnippet();
    expect(".o_add_snippet_dialog").toHaveCount(0);
    expect(contentEl).toHaveInnerHTML(snippetContent);
});

test("initial dropzone appears after undo", async () => {
    const { contentEl, snippetContent } = await setupHTMLBuilder();
    expect(contentEl).toHaveInnerHTML(initialDropZone());

    const { moveTo, drop } = await contains(
        `.o-snippets-menu [data-category="snippet_groups"] div`
    ).drag();
    await moveTo(contentEl);
    expect(contentEl).toHaveInnerHTML(initialDropZone(true));
    await drop();
    await confirmSnippet();
    expect(".o_add_snippet_dialog").toHaveCount(0);
    expect(contentEl).toHaveInnerHTML(snippetContent);

    // Undo should display the dropzone
    await click(".o-snippets-menu button.fa-undo");
    await animationFrame();
    expect(contentEl).toHaveInnerHTML(initialDropZone());
});

test("initial dropzone appears after delete & redo", async () => {
    const startContent = `<section class="s_test"></section>`;
    const { contentEl } = await setupHTMLBuilder(startContent);

    expect(contentEl).toHaveInnerHTML(startContent);
    await click(contentEl.querySelector(".s_test"));
    await animationFrame();
    // Delete should display the initial dropzone
    await click(".oe_snippet_remove.fa-trash");
    await animationFrame();
    expect(contentEl).toHaveInnerHTML(initialDropZone());

    // Undo, then redo should display the initial dropzone
    await click(".o-snippets-menu button.fa-undo");
    await animationFrame();
    expect(contentEl).toHaveInnerHTML(startContent);
    await click(".o-snippets-menu button.fa-repeat");
    await animationFrame();
    expect(contentEl).toHaveInnerHTML(initialDropZone());
});
