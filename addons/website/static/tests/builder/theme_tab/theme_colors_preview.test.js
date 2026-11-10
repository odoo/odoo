import { expect, test } from "@odoo/hoot";
import { animationFrame, queryAll, waitForNone, waitUntil } from "@odoo/hoot-dom";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { parseHTML } from "@html_editor/utils/html";

defineWebsiteModels();

test("theme colors preview modal", async () => {
    await setupWebsiteBuilder("");

    await contains(".o_hb_snippets_tabs button[data-name=theme]").click();
    await contains(".o_hb_tab_content .o_hb_theme_color_slider_btn").click();
    await contains(".o_theme_tab button[title='Colors preview']").click();
    await animationFrame();
    expect(".o_theme_colors_preview_dialog iframe").toHaveCount(1);
    expect(".o_theme_tab button[title='Colors preview']").toHaveAttribute(
        "data-icon",
        "visibility_off"
    );

    await contains(".o_theme_colors_preview_dialog .modal-header .btn-close").click();
    await waitForNone(".o_theme_colors_preview_dialog");
    expect(".o_theme_tab button[title='Colors preview']").toHaveAttribute(
        "data-icon",
        "visibility"
    );

    await contains(".o_theme_tab button[title='Colors preview']").click();
    await animationFrame();
    expect(".o_theme_colors_preview_dialog iframe").toHaveCount(1);

    await contains(".o_theme_tab button[title='Colors preview']").click();
    await waitForNone(".o_theme_colors_preview_dialog");
    expect(".o_theme_tab button[title='Colors preview']").toHaveAttribute(
        "data-icon",
        "visibility"
    );

    await contains(".o_theme_tab button[title='Colors preview']").click();
    await animationFrame();
    expect(".o_theme_colors_preview_dialog iframe").toHaveCount(1);

    await contains(".o_hb_sliding_panel_label button[aria-label='close']").click();
    await waitForNone(".o_theme_colors_preview_dialog");

    await contains(".o_hb_tab_content .o_hb_theme_color_slider_btn").click();
    await contains(".o_theme_tab button[title='Colors preview']").click();
    await animationFrame();
    expect(".o_theme_colors_preview_dialog iframe").toHaveCount(1);

    await contains(".o_hb_snippets_tabs button[data-name=blocks]").click();
    await waitForNone(".o_theme_colors_preview_dialog");
});

test("theme colors preview marks low contrast again once bundles are reloaded", async () => {
    onRpc("/website/theme_customize_bundle_reload", () => ({}));
    const builder = await setupWebsiteBuilder("");
    await contains(".o_hb_snippets_tabs button[data-name=theme]").click();
    await contains(".o_hb_tab_content .o_hb_theme_color_slider_btn").click();
    await contains(".o_theme_tab button[title='Colors preview']").click();
    // Set once the preview iframe is loaded.
    const previewDocument = await waitUntil(() => builder.getEditor().config.extraPreviewDocument);
    previewDocument.body.append(
        parseHTML(
            previewDocument,
            `<div class="o_test_faint" style="background-color: #ffffff;"><span class="o_website_theme_colors_preview_label">Test</span><p style="color: #eeeeee;">Faint</p></div>`
        )
    );
    // Only look at the added text: the preview page may have its own warnings.
    const queryWarnings = () =>
        queryAll(".o_test_faint .o_website_theme_colors_preview_contrast_warning", {
            root: previewDocument,
        });
    expect(queryWarnings()).toHaveLength(0);
    await builder.getEditor().shared.customizeWebsite.reloadBundles();
    expect(queryWarnings()).toHaveLength(1);
});
