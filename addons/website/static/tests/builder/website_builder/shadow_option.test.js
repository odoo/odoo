import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    mockThemeRpcs,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();
test("bootstrap shadow controls in the theme tab of website builder", async () => {
    mockThemeRpcs();
    await setupWebsiteBuilder("");

    await contains("#theme-tab").click();
    await contains("[data-action-param='box-shadow-offset-x'] input").fill("100");
    await expect.waitForSteps(['preview user_values.scss {"box-shadow-offset-x":"6.25rem"}']);

    await contains("div.o_hb_row_label:contains('Normal')").click();
    await contains("div[data-label='Color'] button.o_we_color_preview").click();
    await contains("div.o_popover button.o_color_button[data-color='#FF0000']").click();
    await expect.waitForSteps([
        'preview user_values.scss {"box-shadow-offset-x":"6.25rem","box-shadow-color":"#FF0000"}',
    ]);
});
