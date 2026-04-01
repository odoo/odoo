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

test("snippets cannot be dropped next to elements inside excluded parent", async () => {
    const snippetContent = [
        `<div name="Image" data-oe-thumbnail="image.svg" data-snippet="s_image">
            <img src="/web/image/test.png" data-snippet="s_image" alt="Test Image"/>
        </div>`,
    ];
    const dropzoneSelectors = [
        {
            selector: "img",
            dropNear: "p, h1",
            excludeNearParent: ".second-div",
        },
    ];
    await setupHTMLBuilder(
        `<div class="first-div"><h1>Title</h1><p>Paragraph</p></div>
        <div class="second-div"><h1>Title</h1><p>Paragraph</p></div>`,
        { snippetContent, dropzoneSelectors }
    );

    await contains(".o-snippets-menu .o_snippet_thumbnail[data-snippet='s_image']").drag();
    // Should have 3 dropzones in first-div (not excluded)
    expect(":iframe .first-div .oe_drop_zone").toHaveCount(3);
    // Should have no dropzones in second-div (excluded by excludeNearParent)
    expect(":iframe .second-div .oe_drop_zone").toHaveCount(0);
});
