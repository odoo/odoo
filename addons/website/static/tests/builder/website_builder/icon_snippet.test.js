import { expect, test } from "@odoo/hoot";
import { press, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { getDragHelper } from "@html_builder/../tests/helpers";

defineWebsiteModels();

async function dragIcon() {
    const { moveTo, drop } = await contains(
        ".o_website_builder_sidebar [name='Icon'] .o_snippet_thumbnail"
    ).drag();
    expect(":iframe .oe_drop_zone:nth-child(1)").toHaveCount(1);
    expect(":iframe .oe_drop_zone:nth-child(3)").toHaveCount(1);
    await moveTo(":iframe .oe_drop_zone");
    expect(":iframe .oe_drop_zone.invisible:nth-child(1)").toHaveCount(1);
    expect(".o_website_builder_sidebar [data-icon='undo']").not.toBeEnabled();
    await drop(getDragHelper());
    await waitFor(".o-IconPicker");
    expect(".o_select_media_dialog").toHaveCount(0);
}

test("Drag & drop an 'Icon' snippet opens the icon picker to select an icon", async () => {
    const { getEditableContent } = await setupWebsiteBuilder(`<div><p>Icon</p></div>`);
    const contentEl = getEditableContent();
    expect(contentEl).toHaveInnerHTML(`<div><p>Icon</p></div>`);
    expect(".o_website_builder_sidebar [data-icon='undo']").not.toBeEnabled();
    await dragIcon();
    expect(".o_website_builder_sidebar [data-icon='undo']").not.toBeEnabled();
    // Discard first attempt
    await press("Escape");
    await animationFrame();
    expect(".o-IconPicker").toHaveCount(0);
    expect(":iframe .s_icon").toHaveCount(0);
    expect(":iframe p span[data-icon='favorite']").toHaveCount(0);
    // Drag again and select heart
    await dragIcon();
    await contains(".o-IconPicker-icon[data-icon='favorite']:not(.oi-filled)").click();
    expect(".o-IconPicker").toHaveCount(0);
    expect(":iframe p").toHaveCount(2); // new `p` for the icon
    expect(":iframe p span[data-icon='favorite']").toHaveCount(1);
    expect(".o_website_builder_sidebar [data-icon='undo']").toBeEnabled();
});

test("Drag & drop an 'Icon' snippet in inline does not add <p>", async () => {
    await setupWebsiteBuilder(`<div><p>Text<a class="btn">button</a>Text</p></div>`);
    const { drop } = await contains(
        ".o_website_builder_sidebar [name='Icon'] .o_snippet_thumbnail"
    ).drag();
    await drop(":iframe p a + .oe_drop_zone");
    await contains(".o-IconPicker-icon.oi-filled[data-icon='favorite']").click();
    expect(".o-IconPicker").toHaveCount(0);
    expect(":iframe p").toHaveCount(1); // no new `p` for the icon
    expect(":iframe p span.oi-filled[data-icon='favorite']").toHaveCount(1);
});
