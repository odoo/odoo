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
    <div class="test_a o-paragraph">
        <br>
    </div>
</section>`);
});

test("excludeParent correctly disables dropzones", async () => {
    const snippetContent = [
        `<div name="button" data-oe-snippet-id="123">
            <a class="btn btn-primary" href="#" data-snippet="s_button">Button</a>
        </div>`,
    ];
    const dropzoneSelectors = [
        {
            selector: "a",
            dropNear: "strong",
            excludeParent: ".drop_disabled",
        },
    ];
    const { contentEl } = await setupHTMLBuilder(
        `<p class="drop_enabled">
            <strong>Can drop an 'a' element as a sibling here </strong>
        </p>
        <p class="drop_disabled">
            <strong>Can't drop an 'a' element as a sibling here </strong>
        </p>`,
        {
            snippetContent,
            dropzoneSelectors,
        }
    );
    const { moveTo, drop } = await contains(
        ".o-snippets-menu #snippet_content .o_snippet_thumbnail[data-snippet='s_button']"
    ).drag();

    // .drop_disabled element shouldn't have any dropzones
    expect(":iframe .drop_disabled .oe_drop_zone").toHaveCount(0);
    expect(":iframe .drop_enabled .oe_drop_zone").toHaveCount(2);

    await moveTo(contentEl.querySelector(".drop_disabled"));
    await drop();
    // should drop it inside the drop_enabled element
    expect(":iframe .drop_disabled a.btn").toHaveCount(0);
    expect(":iframe .drop_enabled a.btn").toHaveCount(1);
});
