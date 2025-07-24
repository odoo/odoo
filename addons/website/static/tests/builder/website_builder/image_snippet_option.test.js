import { expect, test } from "@odoo/hoot";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    getDragHelper,
    setupWebsiteBuilder,
    waitForEndOfOperation,
} from "../website_helpers";

defineWebsiteModels();

test("Drag & drop an 'Image' snippet opens the dialog to select an image", async () => {
    onRpc("ir.attachment", "search_read", () => [
        {
            id: 1,
            name: "logo",
            mimetype: "image/png",
            image_src: "/web/static/img/logo2.png",
            access_token: false,
            public: true,
        },
    ]);

    const { getEditableContent } = await setupWebsiteBuilder(`<div><p>Text</p></div>`);
    const contentEl = getEditableContent();
    expect(contentEl).toHaveInnerHTML(`<div><p>Text</p></div>`);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    const { moveTo, drop } = await contains(
        ".o-website-builder_sidebar [name='Image'] .o_snippet_thumbnail"
    ).drag();
    expect(":iframe .oe_drop_zone:nth-child(1)").toHaveCount(1);
    expect(":iframe .oe_drop_zone:nth-child(3)").toHaveCount(1);

    await moveTo(":iframe .oe_drop_zone");
    expect(":iframe .oe_drop_zone.invisible:nth-child(1)").toHaveCount(1);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    await drop(getDragHelper());
    await new Promise((resolve) => setTimeout(resolve, 600));
    expect(".o_select_media_dialog").toHaveCount(1);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    await contains(".o_select_media_dialog .o_button_area[aria-label='logo']").click();
    await waitForEndOfOperation();
    expect(".o_select_media_dialog").toHaveCount(0);

    expect(":iframe div img[src^='data:image/webp;base64,']").toHaveCount(1);
    expect(":iframe img").toHaveCount(1);
    expect(".o-website-builder_sidebar .fa-undo").toBeEnabled();
});

test("Drag & drop an 'Image' snippet does not add a step in the history if we cancel the dialog", async () => {
    const { getEditableContent } = await setupWebsiteBuilder(`<div><p>Text</p></div>`);
    const contentEl = getEditableContent();
    expect(contentEl).toHaveInnerHTML(`<div><p>Text</p></div>`);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    const { moveTo, drop } = await contains(
        ".o-website-builder_sidebar [name='Image'] .o_snippet_thumbnail"
    ).drag();
    expect(":iframe .oe_drop_zone:nth-child(1)").toHaveCount(1);
    expect(":iframe .oe_drop_zone:nth-child(3)").toHaveCount(1);

    await moveTo(":iframe .oe_drop_zone");
    expect(":iframe .oe_drop_zone.invisible:nth-child(1)").toHaveCount(1);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    await drop(getDragHelper());
    await new Promise((resolve) => setTimeout(resolve, 600));
    expect(".o_select_media_dialog").toHaveCount(1);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    await contains(".o_select_media_dialog button.btn-close").click();
    expect(".o_select_media_dialog").toHaveCount(0);
    await waitForEndOfOperation();

    expect(contentEl).toHaveInnerHTML(`<div><p>Text</p></div>`);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();
});
