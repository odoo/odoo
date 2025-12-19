import { expect, test } from "@odoo/hoot";
import { queryOne, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("Size option should be present when scroll down button is enabled", async () => {
    const sizeOptionSelector = ".hb-row-sublevel-1[data-label='Size']";
    await setupWebsiteBuilderWithSnippet("s_banner", { loadIframeBundles: true });
    await contains(":iframe img").click();
    await contains("[data-label='Height'] [data-action-param='o_full_screen_height']").click();
    await contains("[data-label='Scroll Down Button'] input").click();
    await waitFor(sizeOptionSelector);
    expect(`${sizeOptionSelector} .o-hb-button-group button`).toHaveCount(5);
    await contains(`[data-class-action='fa-2x']`).click();
    const scrollDownButtonEl = queryOne(":iframe .o_scroll_button");
    const angleDownIconEl = scrollDownButtonEl.querySelector(".fa-angle-down");
    const computedStyle = getComputedStyle(scrollDownButtonEl);
    const iconFontSize = getComputedStyle(angleDownIconEl).fontSize;
    expect(computedStyle.width).toBe(iconFontSize);
    expect(computedStyle.height).toBe(iconFontSize);
});
