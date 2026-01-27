import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import {
    getDragHelper,
    getInnerContent,
    waitForEndOfOperation,
} from "@html_builder/../tests/helpers";

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
        `<div><a href="http://test.com" class="btn btn-fill-secondary" style="line-height: 50px;">ButtonStyled</a></div>`
    );
    const contentEl = getEditableContent();
    expect(contentEl).toHaveInnerHTML(
        `<div><a href="http://test.com" class="btn btn-fill-secondary" style="line-height: 50px;">ButtonStyled</a></div>`
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
        `<div><a href="http://test.com" class="btn btn-fill-secondary mb-2" style="line-height: 50px;"> ButtonStyled </a> <a class="btn mb-2 btn-fill-secondary" href="/contactus"> Button </a></div>`
    );
    expect(".o-website-builder_sidebar .fa-undo").toBeEnabled();
});

test("Drag & drop a 'Button' snippet over a dropzone should preview it correctly", async () => {
    const { getEditableContent } = await setupWebsiteBuilder(
        `<div><a href="http://test.com" class="btn btn-fill-secondary">ButtonStyled</a>
         <p style="padding-bottom: 50px;"><a href="http://test.com" class="btn btn-fill-secondary">ButtonStyled in a p</a></p></div>`
    );
    const contentEl = getEditableContent();
    expect(contentEl).toHaveInnerHTML(
        `<div><a href="http://test.com" class="btn btn-fill-secondary">ButtonStyled</a>
         <p style="padding-bottom: 50px;"><a href="http://test.com" class="btn btn-fill-secondary">ButtonStyled in a p</a></p></div>`
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
        `<div><a href="http://test.com" class="btn btn-fill-secondary"> ButtonStyled </a>
         <p style="padding-bottom: 50px;"><a href="http://test.com" class="btn btn-fill-secondary"> ButtonStyled in a p </a></p>
         <p><a class="btn btn-primary" href="/contactus"> Button </a></p></div>`
    );
    expect(".o-website-builder_sidebar .fa-undo").toBeEnabled();
});

test("Custom button is not wrapped in <p> when dropped near sibling button", async () => {
    const snippets = {
        snippet_content: [
            getInnerContent({
                name: "Button",
                content: `<a class="btn btn-primary o_default_snippet_text o_snippet_drop_in_only" data-snippet="s_button" href="#" data-bs-original-title="" title="">Button</a>`,
            }),
        ],
        snippet_custom: [
            `<div name="Custom Button" data-oe-type="snippet" data-oe-snippet-id="789" data-o-image-preview="" data-oe-thumbnail="" data-oe-keywords="">
                <a class="btn btn-primary o_default_snippet_text s_custom_snippet o_snippet_drop_in_only s_custom_button" data-snippet="s_button_9a57e5" href="#" data-bs-original-title="" title="">Custom Button</a>
            </div>`,
        ],
    };

    const { getEditableContent } = await setupWebsiteBuilder(
        `<section><a class="btn btn-primary" href="#">Button</a></section>`,
        { snippets }
    );
    expect(".o-snippets-menu #snippet_custom_content div[name='Custom Button']").toHaveCount(1);

    const { moveTo, drop } = await contains(
        ".o-snippets-menu div[name='Custom Button'] .o_snippet_thumbnail"
    ).drag();
    await moveTo(":iframe .oe_drop_zone");
    await drop(getDragHelper());
    await waitForEndOfOperation();
    expect(getEditableContent()).toHaveInnerHTML(
        `<section class="o_colored_level">
            <a class="btn btn-primary o_default_snippet_text s_custom_snippet mb-2" href="#" data-bs-original-title="" title="">Custom Button</a>
            <a class="btn btn-primary mb-2" href="#">Button</a>
        </section>`
    );
});
