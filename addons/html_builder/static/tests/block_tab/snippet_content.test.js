import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, click, queryAll, queryAllTexts } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { setupHTMLBuilder } from "../helpers";

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

test("display inner content snippet", async () => {
    await setupHTMLBuilder("<div><p>Text</p></div>", {
        snippetContent,
        dropzoneSelectors,
    });
    const snippetInnerContentSelector = `.o-snippets-menu [data-category="snippet_content"]`;
    expect(snippetInnerContentSelector).toHaveCount(2);
    expect(queryAllTexts(snippetInnerContentSelector)).toEqual(["Button A", "Button B"]);
    const imgSrc = queryAll(`${snippetInnerContentSelector} img`).map((img) => img.dataset.src);
    expect(imgSrc).toEqual(["buttonA.svg", "buttonB.svg"]);
});

test("drag & drop inner content block", async () => {
    const { contentEl } = await setupHTMLBuilder("<div><p>Text</p></div>", {
        snippetContent,
        dropzoneSelectors,
    });
    expect(contentEl).toHaveInnerHTML(`<div><p>Text</p></div>`);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    const { moveTo, drop } = await contains(".o-website-builder_sidebar [name='Button A']").drag();
    await animationFrame(); // TODO we should remove it maybe bug utils hoot
    expect(":iframe .oe_drop_zone:nth-child(1)").toHaveCount(1);
    expect(":iframe .oe_drop_zone:nth-child(3)").toHaveCount(1);

    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    await moveTo(contentEl.querySelector(".oe_drop_zone"));
    expect(":iframe .oe_drop_zone.o_dropzone_highlighted:nth-child(1)").toHaveCount(1);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    await drop(contentEl.querySelector(".oe_drop_zone"));
    expect(contentEl).toHaveInnerHTML(
        `<div>\ufeff<a class="btn btn-primary" href="#" data-snippet="s_button" data-name="Button A">\ufeffButton A\ufeff</a>\ufeff<p>Text</p></div>`
    );
    expect(".o-website-builder_sidebar .fa-undo").toBeEnabled();
});

test("drag & drop inner content block + undo/redo", async () => {
    const { contentEl } = await setupHTMLBuilder("<div><p>Text</p></div>", {
        snippetContent,
        dropzoneSelectors,
    });
    expect(contentEl).toHaveInnerHTML(`<div><p>Text</p></div>`);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();
    expect(".o-website-builder_sidebar .fa-repeat").not.toBeEnabled();

    const { drop } = await contains(".o-website-builder_sidebar [name='Button A']").drag();
    await drop(contentEl.querySelector(".oe_drop_zone"));
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

test("drag inner content & drop in outside of a dropzone", async () => {
    const { contentEl, builderEl } = await setupHTMLBuilder("<div><p>Text</p></div>", {
        snippetContent,
        dropzoneSelectors,
    });
    expect(contentEl).toHaveInnerHTML(`<div><p>Text</p></div>`);

    const { drop } = await contains(".o-website-builder_sidebar [name='Button A']").drag();
    expect(":iframe .oe_drop_zone:nth-child(1)").toHaveCount(1);
    expect(":iframe .oe_drop_zone:nth-child(3)").toHaveCount(1);

    await drop(builderEl);
    expect(contentEl).toHaveInnerHTML(`<div><p>Text</p></div>`);
});
