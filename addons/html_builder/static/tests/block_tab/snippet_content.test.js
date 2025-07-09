import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, queryAll, queryAllTexts } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { getDragHelper, waitForEndOfOperation } from "../website_helpers";

describe.current.tags("desktop");

const snippetContent = [
    `<div name="Button A" data-oe-thumbnail="buttonA.svg" data-oe-snippet-id="123">
        <a class="btn btn-primary" href="#" data-snippet="s_button">Button A</a>
    </div>`,
    `<div name="Button B" data-oe-thumbnail="buttonB.svg" data-oe-snippet-id="123">
        <a class="btn btn-primary" href="#" data-snippet="s_button">Button B</a>
    </div>`,
];

const dropzoneSelectors = [
    {
        selector: "*",
        dropNear: "p",
    },
];

test("Display inner content snippet", async () => {
    await setupHTMLBuilder("<div><p>Text</p></div>", {
        snippetContent,
        dropzoneSelectors,
    });
    const snippetInnerContentSelector = ".o-snippets-menu #snippet_content .o_snippet";
    expect(snippetInnerContentSelector).toHaveCount(2);
    expect(queryAllTexts(snippetInnerContentSelector)).toEqual(["Button A", "Button B"]);
    const thumbnailImgUrls = queryAll(
        `${snippetInnerContentSelector} .o_snippet_thumbnail_img`
    ).map((thumbnail) => thumbnail.style.backgroundImage);
    expect(thumbnailImgUrls).toEqual(['url("buttonA.svg")', 'url("buttonB.svg")']);
});

test("Drag & drop inner content block", async () => {
    const { contentEl } = await setupHTMLBuilder("<div><p>Text</p></div>", {
        snippetContent,
        dropzoneSelectors,
    });
    expect(contentEl).toHaveInnerHTML(`<div><p>Text</p></div>`);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    const { moveTo, drop } = await contains(
        ".o-website-builder_sidebar [name='Button A'] .o_snippet_thumbnail"
    ).drag();
    expect(":iframe .oe_drop_zone:nth-child(1)").toHaveCount(1);
    expect(":iframe .oe_drop_zone:nth-child(3)").toHaveCount(1);

    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    await moveTo(":iframe .oe_drop_zone");
    expect(":iframe .oe_drop_zone.invisible:nth-child(1)").toHaveCount(1);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    await drop(getDragHelper());
    await waitForEndOfOperation();

    expect(contentEl).toHaveInnerHTML(
        `<div>\ufeff<a class="btn btn-primary" href="#" data-snippet="s_button" data-name="Button A">\ufeffButton A\ufeff</a>\ufeff<p>Text</p></div>`
    );
    expect(".o-website-builder_sidebar .fa-undo").toBeEnabled();
});

test("Drag & drop inner content block + undo/redo", async () => {
    const { contentEl } = await setupHTMLBuilder("<div><p>Text</p></div>", {
        snippetContent,
        dropzoneSelectors,
    });
    expect(contentEl).toHaveInnerHTML(`<div><p>Text</p></div>`);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();
    expect(".o-website-builder_sidebar .fa-repeat").not.toBeEnabled();

    await click(".o-website-builder_sidebar .fa-undo");
    const { moveTo, drop } = await contains(
        ".o-website-builder_sidebar [name='Button A'] .o_snippet_thumbnail"
    ).drag();
    await moveTo(":iframe .oe_drop_zone");
    await drop(getDragHelper());
    await waitForEndOfOperation();

    expect(contentEl).toHaveInnerHTML(
        `<div>\ufeff<a class="btn btn-primary" href="#" data-snippet="s_button" data-name="Button A">\ufeffButton A\ufeff</a>\ufeff<p>Text</p></div>`
    );
    expect(".o-website-builder_sidebar .fa-undo").toBeEnabled();
    expect(".o-website-builder_sidebar .fa-repeat").not.toBeEnabled();

    await click(".o-website-builder_sidebar .fa-undo");
    await animationFrame();
    expect(contentEl).toHaveInnerHTML(`<div><p>Text</p></div>`);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();
    expect(".o-website-builder_sidebar .fa-repeat").toBeEnabled();
});

test("Drag inner content and drop it outside of a dropzone", async () => {
    const { contentEl, builderEl } = await setupHTMLBuilder("<div><p>Text</p></div>", {
        snippetContent,
        dropzoneSelectors,
    });
    expect(contentEl).toHaveInnerHTML(`<div><p>Text</p></div>`);

    const { moveTo, drop } = await contains(
        ".o-website-builder_sidebar [name='Button A'] .o_snippet_thumbnail"
    ).drag();
    expect(":iframe .oe_drop_zone:nth-child(1)").toHaveCount(1);
    expect(":iframe .oe_drop_zone:nth-child(3)").toHaveCount(1);

    await moveTo(builderEl);
    await drop(getDragHelper());
    await waitForEndOfOperation();

    expect(contentEl).toHaveInnerHTML(`<div><p>Text</p></div>`);
});

test("A snippet should appear disabled if there is nowhere to drop it", async () => {
    const { contentEl } = await setupHTMLBuilder("", {
        snippetContent,
        dropzoneSelectors,
    });
    expect(contentEl).toHaveInnerHTML("");
    expect(".o_block_tab .o_snippet.o_disabled").toHaveCount(2);
});
