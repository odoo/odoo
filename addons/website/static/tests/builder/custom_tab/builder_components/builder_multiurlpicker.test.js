import { beforeEach, expect, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "../../website_helpers";

defineWebsiteModels();

const inputSelector = ".we-bg-options-container input.o-hb-input-base:not(:disabled)";
const selectedUrlsSelector = ".we-bg-options-container input.o-hb-input-base:disabled";
const testOptionsTargetSelector = ":iframe .test-options-target";

beforeEach(() => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderMultiUrlPicker dataAttributeAction="'urls'"/>`,
    });
});

test("adds URL by typing and pressing Enter", async () => {
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(testOptionsTargetSelector).click();

    await contains(inputSelector).edit("/page");
    await contains(inputSelector).press("Enter");
    expect(inputSelector).toHaveValue("");
    expect(selectedUrlsSelector).toHaveValue("/page");
    expect(testOptionsTargetSelector).toHaveAttribute("data-urls", '["/page"]');
});

test("adding multiple URLs", async () => {
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(testOptionsTargetSelector).click();

    // Add first URL
    await contains(inputSelector).edit("/page1");
    await contains(inputSelector).press("Enter");

    // Add second URL
    await contains(inputSelector).edit("/page2");
    await contains(inputSelector).press("Enter");

    // Verify disabled inputs contain the added URLs
    const selectedUrls = document.querySelectorAll(selectedUrlsSelector);
    expect(selectedUrls).toHaveLength(2);
    expect(selectedUrls[0].value).toBe("/page1");
    expect(selectedUrls[1].value).toBe("/page2");

    // Check data attribute is updated correctly
    await expect(testOptionsTargetSelector).toHaveAttribute(
        "data-urls",
        JSON.stringify(["/page1", "/page2"])
    );
});

test("does not add duplicate URLs", async () => {
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(testOptionsTargetSelector).click();

    // Add URL
    await contains(inputSelector).edit("/page1");
    await contains(inputSelector).press("Enter");
    let selectedUrls = document.querySelectorAll(selectedUrlsSelector);
    expect(selectedUrls[0].value).toBe("/page1");

    // Try to add duplicate
    await contains(inputSelector).edit("/page1");
    await contains(inputSelector).press("Enter");
    selectedUrls = document.querySelectorAll(selectedUrlsSelector);
    expect(selectedUrls).toHaveLength(1);
});

test("can remove a URL", async () => {
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(testOptionsTargetSelector).click();

    // Add URLs
    await contains(inputSelector).edit("/page1");
    await contains(inputSelector).press("Enter");

    await contains(inputSelector).edit("/page2");
    await contains(inputSelector).press("Enter");

    // Remove first URL
    await contains(".we-bg-options-container button.fa-minus:nth-child(1)").click();
    const selectedUrls = document.querySelectorAll(selectedUrlsSelector);
    expect(selectedUrls).toHaveLength(1);
    expect(selectedUrls[0].value).toBe("/page2");
    await expect(testOptionsTargetSelector).toHaveAttribute(
        "data-urls",
        JSON.stringify(["/page2"])
    );
});

test("previously selected URLs", async () => {
    await setupWebsiteBuilder(
        `<div class="test-options-target" data-urls='["/page1", "/page2"]'>b</div>`
    );
    await contains(testOptionsTargetSelector).click();

    const selectedUrls = document.querySelectorAll(selectedUrlsSelector);
    expect(selectedUrls).toHaveLength(2);
    expect(selectedUrls[0].value).toBe("/page1");
    expect(selectedUrls[1].value).toBe("/page2");
});
