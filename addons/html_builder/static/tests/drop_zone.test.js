import {
    setupHTMLBuilder,
    waitForEndOfOperation,
    confirmAddSnippet,
} from "@html_builder/../tests/helpers";
import { describe, expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

const dropzone = (hovered = false) => {
    const highlightClass = hovered ? " o_dropzone_highlighted" : "";
    return `<div class="oe_drop_zone oe_insert${highlightClass}" data-editor-message-default="true" data-editor-message="DRAG BUILDING BLOCKS HERE"></div>`;
};

test("wrapper element has the 'DRAG BUILDING BLOCKS HERE' message", async () => {
    const { contentEl } = await setupHTMLBuilder("");
    expect(contentEl).toHaveAttribute("data-editor-message", "DRAG BUILDING BLOCKS HERE");
});

test("drop beside dropzone inserts the snippet", async () => {
    const { contentEl } = await setupHTMLBuilder();
    const { moveTo, drop } = await contains(
        ".o-snippets-menu #snippet_groups .o_snippet_thumbnail"
    ).drag();
    await moveTo(contentEl.ownerDocument.body);
    // The dropzone is not hovered, so not highlighted.
    expect(contentEl).toHaveInnerHTML(dropzone());
    await drop();
    await confirmAddSnippet();
    expect(".o_add_snippet_dialog").toHaveCount(0);
    await waitForEndOfOperation();
    expect(contentEl)
        .toHaveInnerHTML(`<section class="s_test" data-snippet="s_test" data-name="Test">
    <div class="test_a"></div>
    </section>`);
});
