import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { testImg, testImgSrc } from "./image_test_helpers";

defineWebsiteModels();

test("the image should show its size", async () => {
    const { waitDomUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testImg}
        </div>
    `);
    await contains(":iframe .test-options-target img").click();
    await waitDomUpdated();
    const selector = `[data-container-title="Image"] [title="Size"]`;
    await waitFor(selector);
    expect(selector).toHaveInnerHTML("35.6 kB");
});

test("the background image should show its size", async () => {
    const { waitDomUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            <section style="background-image: url(${testImgSrc});">text</section>
        </div>
    `);
    await contains(":iframe .test-options-target section").click();
    await waitDomUpdated();
    const selector = `[data-label="Image"] [title="Size"]`;
    await waitFor(selector);
    expect(selector).toHaveInnerHTML("35.6 kB");
});
