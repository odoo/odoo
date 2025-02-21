import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { animationFrame } from "@odoo/hoot-dom";
import { defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";

defineWebsiteModels();

test("drag & drop a button snippet to a div should put it to a p", async () => {
    const { getEditableContent } = await setupWebsiteBuilder(`<div><p>Text</p></div>`);
    const contentEl = getEditableContent();
    expect(contentEl).toHaveInnerHTML(`<div><p>Text</p></div>`);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    const { moveTo, drop } = await contains(".o-website-builder_sidebar [name='Button']").drag();
    await animationFrame(); // TODO we should remove it maybe bug utils hoot
    expect(contentEl).toHaveInnerHTML(
        `<div><div class="oe_drop_zone oe_insert" data-editor-message="DRAG BUILDING BLOCKS HERE"></div><p>Text</p><div class="oe_drop_zone oe_insert" data-editor-message="DRAG BUILDING BLOCKS HERE"></div></div>`
    );
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    await moveTo(contentEl.querySelector(".oe_drop_zone"));
    expect(contentEl).toHaveInnerHTML(
        `<div><div class="oe_drop_zone oe_insert o_dropzone_highlighted" data-editor-message="DRAG BUILDING BLOCKS HERE"></div><p>Text</p><div class="oe_drop_zone oe_insert" data-editor-message="DRAG BUILDING BLOCKS HERE"></div></div>`
    );
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    await drop(contentEl.querySelector(".oe_drop_zone"));
    expect(contentEl).toHaveInnerHTML(
        `<div><p>\ufeff<a class="btn btn-primary o_snippet_drop_in_only" href="#" data-snippet="s_button" data-name="Button">\ufeffButton\ufeff</a>\ufeff</p><p>Text</p></div>`
    );
});

test("drag & drop  a button snippet should align the button style with the button before it", async () => {
    const { getEditableContent } = await setupWebsiteBuilder(
        `<a href="http://test.com" class="btn btn-fill-secondary">ButtonStyled</a>`
    );
    const contentEl = getEditableContent();
    expect(contentEl).toHaveInnerHTML(
        `<a href="http://test.com" class="btn btn-fill-secondary">ButtonStyled</a>`
    );
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    const { moveTo, drop } = await contains(".o-website-builder_sidebar [name='Button']").drag();
    await animationFrame(); // TODO we should remove it maybe bug utils hoot
    expect(contentEl).toHaveInnerHTML(
        `<div class="oe_drop_zone oe_insert" data-editor-message="DRAG BUILDING BLOCKS HERE"></div><a href="http://test.com" class="btn btn-fill-secondary">ButtonStyled</a><div class="oe_drop_zone oe_insert" data-editor-message="DRAG BUILDING BLOCKS HERE"></div>`
    );
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    const dropZones = contentEl.querySelectorAll(".oe_drop_zone");
    const lastDropZone = dropZones[dropZones.length - 1];
    await moveTo(lastDropZone);
    expect(contentEl).toHaveInnerHTML(
        `<div class="oe_drop_zone oe_insert" data-editor-message="DRAG BUILDING BLOCKS HERE"></div><a href="http://test.com" class="btn btn-fill-secondary">ButtonStyled</a><div class="oe_drop_zone oe_insert o_dropzone_highlighted" data-editor-message="DRAG BUILDING BLOCKS HERE"></div>`
    );
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    await drop(lastDropZone);
    expect(contentEl).toHaveInnerHTML(
        `<a href="http://test.com" class="btn btn-fill-secondary mb-2"> ButtonStyled </a> <a class="btn o_snippet_drop_in_only mb-2 btn-fill-secondary" href="#" data-snippet="s_button" data-name="Button"> Button </a>`
    );
});
