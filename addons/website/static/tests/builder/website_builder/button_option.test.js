import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { getDragHelper, waitForEndOfOperation } from "@html_builder/../tests/helpers";

defineWebsiteModels();

test("Drag & drop a 'Button' snippet in a <div> should put it inside a <p>", async () => {
    const { getEditableContent } = await setupWebsiteBuilder(`<div><p>Text</p></div>`);
    const contentEl = getEditableContent();
    expect(contentEl).toHaveInnerHTML(`<div><p>Text</p></div>`);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    const { moveTo, drop } = await contains(
        ".o-website-builder_sidebar [name='Button'] .o_snippet_thumbnail"
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
        `<div><p>\ufeff<a class="btn btn-primary" href="/contactus">\ufeffButton\ufeff</a>\ufeff</p><p>Text</p></div>`
    );
    expect(".o-website-builder_sidebar .fa-undo").toBeEnabled();
});

test("Drag & drop a 'Button' snippet should align the button style with the button before it", async () => {
    const { getEditableContent } = await setupWebsiteBuilder(
        `<a href="http://test.com" class="btn btn-fill-secondary" style="line-height: 50px;">ButtonStyled</a>`
    );
    const contentEl = getEditableContent();
    expect(contentEl).toHaveInnerHTML(
        `<a href="http://test.com" class="btn btn-fill-secondary" style="line-height: 50px;">ButtonStyled</a>`
    );
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    const { moveTo, drop } = await contains(
        ".o-website-builder_sidebar [name='Button'] .o_snippet_thumbnail"
    ).drag();
    expect(":iframe .oe_drop_zone:nth-child(1)").toHaveCount(1);
    expect(":iframe .oe_drop_zone:nth-child(3)").toHaveCount(1);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    await moveTo(":iframe .oe_drop_zone:nth-child(3)");
    expect(":iframe .oe_drop_zone.invisible:nth-child(3)").toHaveCount(1);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    await drop(getDragHelper());
    await waitForEndOfOperation();
    expect(contentEl).toHaveInnerHTML(
        `<a href="http://test.com" class="btn btn-fill-secondary mb-2" style="line-height: 50px;"> ButtonStyled </a> <a class="btn mb-2 btn-fill-secondary" href="/contactus"> Button </a>`
    );
    expect(".o-website-builder_sidebar .fa-undo").toBeEnabled();
});

test("Drag & drop a 'Button' snippet over a dropzone should preview it correctly", async () => {
    const { getEditableContent } = await setupWebsiteBuilder(
        `<a href="http://test.com" class="btn btn-fill-secondary">ButtonStyled</a>
         <p style="padding-bottom: 50px;"><a href="http://test.com" class="btn btn-fill-secondary">ButtonStyled in a p</a></p>`
    );
    const contentEl = getEditableContent();
    expect(contentEl).toHaveInnerHTML(
        `<a href="http://test.com" class="btn btn-fill-secondary">ButtonStyled</a>
         <p style="padding-bottom: 50px;"><a href="http://test.com" class="btn btn-fill-secondary">ButtonStyled in a p</a></p>`
    );
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    const { moveTo, drop } = await contains(
        ".o-website-builder_sidebar [name='Button'] .o_snippet_thumbnail"
    ).drag();
    expect(":iframe .oe_drop_zone").toHaveCount(5);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    await moveTo(":iframe .oe_drop_zone");
    expect(":iframe .oe_drop_zone.invisible").toHaveCount(1);
    expect(":iframe [data-snippet='s_button']").toHaveClass("mb-2 btn-fill-secondary");

    await moveTo(":iframe .oe_drop_zone:last");
    expect(":iframe .oe_drop_zone.invisible:last").toHaveCount(1);
    expect(":iframe [data-snippet='s_button']").not.toHaveClass("mb-2 btn-fill-secondary");
    expect(":iframe [data-snippet='s_button']").toHaveClass("btn-primary");

    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    await drop(getDragHelper());
    await waitForEndOfOperation();
    expect(contentEl).toHaveInnerHTML(
        `<a href="http://test.com" class="btn btn-fill-secondary"> ButtonStyled </a>
         <p style="padding-bottom: 50px;"><a href="http://test.com" class="btn btn-fill-secondary"> ButtonStyled in a p </a></p>
         <p><a class="btn btn-primary" href="/contactus"> Button </a></p>`
    );
    expect(".o-website-builder_sidebar .fa-undo").toBeEnabled();
});
