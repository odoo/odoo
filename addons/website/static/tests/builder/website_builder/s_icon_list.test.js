import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("Icon List Snippet", async () => {
    await setupWebsiteBuilderWithSnippet("s_icon_list", { loadIframeBundles: true });
    await contains(":iframe .s_icon_list").click();

    await contains(".options-container div[data-label='Color'] button").click();
    await contains(".o_popover button[data-color='#FF0000']").click();
    expect(":iframe .s_icon_list").toHaveStyle("--icon-list-icon-color: #FF0000");

    await contains(".options-container div[data-label='Background Color'] button").click();
    await contains(".popover button.gradient-tab").click();
    await contains(".o_colorpicker_sections button").click();
    expect(":iframe .s_icon_list").toHaveStyle(
        "--icon-list-icon-bg-color: linear-gradient(135deg,rgb(255,204,51) 0%,rgb(226,51,255) 100%)"
    );

    await contains(".options-container button[data-action-id='replaceListIcon']").click();
    await contains(".modal-dialog .fa-remove").click();
    expect(":iframe .s_icon_list").toHaveStyle('--icon-list-icon-content: "\\f00d"');
});
