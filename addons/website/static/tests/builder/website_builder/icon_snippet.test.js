import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { getDragHelper } from "@html_builder/../tests/helpers";

defineWebsiteModels();

async function dragIcon() {
    const { moveTo, drop } = await contains(
        ".o-website-builder_sidebar [name='Icon'] .o_snippet_thumbnail"
    ).drag();
    expect(":iframe .oe_drop_zone:nth-child(1)").toHaveCount(1);
    expect(":iframe .oe_drop_zone:nth-child(3)").toHaveCount(1);
    await moveTo(":iframe .oe_drop_zone");
    expect(":iframe .oe_drop_zone.invisible:nth-child(1)").toHaveCount(1);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();
    await drop(getDragHelper());
    expect(".o_select_media_dialog").toHaveCount(1);
}

test("Drag & drop an 'Icon' snippet opens the dialog to select an icon", async () => {
    const { getEditableContent } = await setupWebsiteBuilder(`<div><p>Icon</p></div>`);
    const contentEl = getEditableContent();
    expect(contentEl).toHaveInnerHTML(`<div><p>Icon</p></div>`);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();
    await dragIcon();
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();
    // Discard first attempt
    await contains(".o_select_media_dialog button:contains('Discard')").click();
    expect(":iframe p span.fa-heart").toHaveCount(0);
    // Drag again and select heart
    await dragIcon();
    await contains(".o_select_media_dialog .font-icons-icons span.fa-heart").click();
    expect(".o_select_media_dialog").toHaveCount(0);
    expect(":iframe p").toHaveCount(2); // new `p` for the icon
    expect(":iframe p span.fa-heart").toHaveCount(1);
    expect(".o-website-builder_sidebar .fa-undo").toBeEnabled();
});

test("Drag & drop an 'Icon' snippet in inline does not add <p>", async () => {
    await setupWebsiteBuilder(`<div><p>Text<a class="btn">button</a>Text</p></div>`);
    const { drop } = await contains(
        ".o-website-builder_sidebar [name='Icon'] .o_snippet_thumbnail"
    ).drag();
    await drop(":iframe p a + .oe_drop_zone");
    await contains(".o_select_media_dialog .font-icons-icons span.fa-heart").click();
    expect(".o_select_media_dialog").toHaveCount(0);
    expect(":iframe p").toHaveCount(1); // no new `p` for the icon
    expect(":iframe p span.fa-heart").toHaveCount(1);
});
