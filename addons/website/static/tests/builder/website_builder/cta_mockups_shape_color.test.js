import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("verify that shape color is present in 's_cta_mockups' snippet", async () => {
    const { waitSidebarUpdated, getEditableContent } = await setupWebsiteBuilder("", {
        loadIframeBundles: true,
    });
    const editableContent = getEditableContent();
    await contains("[data-snippet-group='content'] button").click();
    await contains(":iframe [data-snippet-id='s_cta_mockups']").click();
    const imgEls = editableContent.querySelectorAll("img");
    imgEls.forEach(async (imgEl) => {
        click(imgEl);
        await waitSidebarUpdated();
        expect("[data-container-title='Image'] [data-label='Colors']").toBeVisible();
    });
});
