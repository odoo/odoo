import { expect, test } from "@odoo/hoot";
import { animationFrame, click, queryFirst } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("List Group Snippet", async () => {
    await setupWebsiteBuilderWithSnippet("s_list_group", { loadIframeBundles: true });
    await contains(":iframe .s_list_group").click();
    await click(".options-container div[data-label='Icon Color'] button");
    await animationFrame();
    await click(".o_popover button[data-color='#FF0000']");
    await animationFrame();
    const el = queryFirst(":iframe .s_list_group li");
    expect(el).toHaveStyle("--s_list_group-icon-color: #FF0000");
    await click(".options-container div[data-label='Icon Background Color'] button");
    await animationFrame();
    await click(".popover button.gradient-tab");
    await animationFrame();
    await click(".o_colorpicker_sections button");
    await animationFrame();
    expect(el).toHaveStyle(
        "--s_list_group-icon-bg: linear-gradient(135deg,rgb(255,204,51) 0%,rgb(226,51,255) 100%)"
    );
    await click(".options-container button[data-action-id='replaceListIcon']");
    await animationFrame();
    await click(".modal-dialog .fa-remove");
    await animationFrame();
    const iconContent = getComputedStyle(el).getPropertyValue("--s_list_group-icon-content").trim();
    expect(iconContent).toMatch(/^["']\uf00d["']$/);
});
