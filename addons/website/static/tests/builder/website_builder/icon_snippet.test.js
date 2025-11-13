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
    expect(":iframe p span.fa-heart").toHaveCount(1);
    expect(".o-website-builder_sidebar .fa-undo").toBeEnabled();
});
