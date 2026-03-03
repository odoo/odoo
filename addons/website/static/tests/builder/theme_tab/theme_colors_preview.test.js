import { expect, test } from "@odoo/hoot";
import { animationFrame, waitForNone } from "@odoo/hoot-dom";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { contains } from "@web/../tests/web_test_helpers";

defineWebsiteModels();

test("theme colors preview modal", async () => {
    await setupWebsiteBuilder("");

    await contains(".o-snippets-tabs button[data-name=theme]").click();
    await contains(".o-tab-content .o-hb-theme-color-slider-btn").click();
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

    await contains(".hb-sliding-panel-label button[aria-label='close']").click();
    await waitForNone(".o_theme_colors_preview_dialog");

    await contains(".o-tab-content .o-hb-theme-color-slider-btn").click();
    await contains(".o_theme_tab button[title='Colors preview']").click();
    await animationFrame();
    expect(".o_theme_colors_preview_dialog iframe").toHaveCount(1);

    await contains(".o-snippets-tabs button[data-name=blocks]").click();
    await waitForNone(".o_theme_colors_preview_dialog");
});
