import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { testImg, testImgSrc, testGifImg, testGifImgSrc } from "./image_test_helpers";

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
    const size = parseFloat(document.querySelector(selector).innerHTML);
    expectAround(size, 35.6);
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
    const size = parseFloat(document.querySelector(selector).innerHTML);
    expectAround(size, 35.6);
});

function expectAround(value, expected, delta = 0.2) {
    expect(value).toBeGreaterThan(expected - delta);
    expect(value).toBeLessThan(expected + delta);
}

test("the GIF image should NOT show its size", async () => {
    const { waitDomUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            ${testGifImg}
        </div>
    `);
    await contains(":iframe .test-options-target img").click();
    await waitDomUpdated();
    expect(`[data-label="Image"] [title="Size"]`).toHaveCount(0);
});

test("the GIF background image should NOT show its size", async () => {
    const { waitDomUpdated } = await setupWebsiteBuilder(`
        <div class="test-options-target">
            <section style="background-image: url(${testGifImgSrc});">text</section>
        </div>
    `);
    await contains(":iframe .test-options-target section").click();
    await waitDomUpdated();
    expect(`[data-label="Image"] [title="Size"]`).toHaveCount(0);
});
