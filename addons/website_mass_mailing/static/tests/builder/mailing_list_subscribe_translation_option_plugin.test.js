import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    getStructureSnippet,
    setupSidebarBuilderForTranslation,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("'Display Thanks message' option should be visible in the translate mode", async () => {
    const snippet = await getStructureSnippet("s_newsletter_block");
    await setupSidebarBuilderForTranslation({
        websiteContent: snippet.outerHTML,
    });

    await contains(".modal .btn:contains(Ok, never show me this again)").click();
    await contains(":iframe .s_newsletter_block").click();

    expect(".hb-row [data-action-id='toggleThanksMessage']").toHaveCount(1);
    // thanks message shouldn't be displayed
    expect(":iframe .js_subscribed_wrap").not.toHaveClass("o_enable_preview");
    expect(":iframe .js_subscribe_wrap").not.toHaveClass("o_disable_preview");

    await contains("[data-action-id='toggleThanksMessage'] input[type='checkbox']").click();
    // thanks message should be displayed
    expect(":iframe .js_subscribed_wrap").toHaveClass("o_enable_preview");
    expect(":iframe .js_subscribe_wrap").toHaveClass("o_disable_preview");
});
