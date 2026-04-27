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

    await contains("button[data-action='mobile']").click();
    expect(".o_website_preview.o_is_mobile").toHaveCount(1);

    await contains(".o-snippets-tabs button[data-name=theme]").click();
    await contains(".o-tab-content .o-hb-theme-color-slider-btn").click();
    await contains(".o_theme_tab button[title='Colors preview']").click();
    await animationFrame();

    expect(".o_theme_colors_preview_dialog iframe").toHaveCount(1);
    expect("button[data-action='mobile']").toHaveAttribute("disabled");
    expect(".o_website_preview.o_is_mobile").toHaveCount(0);
    expect(".o_theme_tab button[title='Colors preview']").toHaveClass("fa-eye-slash");

    await contains(".o_theme_tab button[title='Colors preview']").click();
    await waitForNone(".o_theme_colors_preview_dialog");

    expect("button[data-action='mobile']").not.toHaveAttribute("disabled");
    expect(".o_website_preview.o_is_mobile").toHaveCount(1);
    expect(".o_theme_tab button[title='Colors preview']").toHaveClass("fa-eye");

    await contains(".o_theme_tab button[title='Colors preview']").click();
    await animationFrame();

    expect(".o_theme_colors_preview_dialog iframe").toHaveCount(1);
    expect("button[data-action='mobile']").toHaveAttribute("disabled");
    expect(".o_website_preview.o_is_mobile").toHaveCount(0);

    await contains(".o-snippets-tabs button[data-name=blocks]").click();
    await waitForNone(".o_theme_colors_preview_dialog");

    expect("button[data-action='mobile']").not.toHaveAttribute("disabled");
    expect(".o_website_preview.o_is_mobile").toHaveCount(1);
});
