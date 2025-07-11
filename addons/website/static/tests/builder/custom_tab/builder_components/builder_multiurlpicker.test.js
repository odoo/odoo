import { after, before, expect, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "../../website_helpers";

defineWebsiteModels();

let originalWindowOpen;
function mockWindowOpen() {
    originalWindowOpen = window.open;
    window.open = (...args) => {
        expect.step(`callWindowOpen ${args[0]}`);
    };
}
function unmockWindowOpen() {
    window.open = originalWindowOpen;
}
function mockGetSuggestedLinks(callback = undefined) {
    onRpc("/website/get_suggested_links", () => {
        callback?.();
        return {
            matching_pages: [
                {
                    value: "/page1",
                    label: "/page1 (Page 1)",
                },
                {
                    value: "/page2",
                    label: "/page2 (Page 2)",
                },
            ],
            others: [
                {
                    title: "Last modified pages",
                    values: [
                        {
                            value: "/page3",
                            label: "/page3 (Page 3)",
                        },
                    ],
                },
                {
                    title: "Apps url",
                    values: [
                        {
                            value: "/app1",
                            label: "/app1 (App 1)",
                            icon: "app1_icon",
                        },
                    ],
                },
            ],
        };
    });
}

before(() => {
    mockWindowOpen();
});
after(() => {
    unmockWindowOpen();
});

test("opens dropdown when typing /", async () => {
    mockGetSuggestedLinks(() => {
        expect.step("button_immediate_install");
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<WebsiteMultiUrlPicker dataAttributeAction="'url'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    await contains(".we-bg-options-container input").edit("/");
    await contains(".we-bg-options-container input").click();
    expect.verifySteps(["button_immediate_install"]);
    expect(document.querySelector(".o_website_ui_autocomplete")).toBeVisible();
});

test("selects and commits value from dropdown", async () => {
    mockGetSuggestedLinks();
    addOption({
        selector: ".test-options-target",
        template: xml`<WebsiteMultiUrlPicker dataAttributeAction="'url'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    await contains(".we-bg-options-container input").edit("/");
    await contains(".we-bg-options-container input").click();
    await contains(document.querySelector(".o_website_ui_autocomplete > li:first-child a")).click();
    expect(document.querySelector(".o_website_ui_autocomplete")).toBe(null);
    expect(".we-bg-options-container .o-hb-input-base:disabled").toHaveValue("/page1");
    expect(":iframe .test-options-target").toHaveAttribute("data-url", '["/page1"]');
});

test("adding multiple URLs", async () => {
    mockGetSuggestedLinks();

    addOption({
        selector: ".test-options-target",
        template: xml`<WebsiteMultiUrlPicker dataAttributeAction="'urls'" />`,
    });

    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    const inputSelector = ".we-bg-options-container input.o-hb-input-base:not(:disabled)";
    const disabledInputSelector = ".we-bg-options-container input.o-hb-input-base:disabled";

    // Add first URL
    await contains(inputSelector).edit("/page1");
    await contains(inputSelector).click();
    await contains(
        document.querySelector(".o_website_ui_autocomplete > li:nth-child(1) a")
    ).click();

    // Add second URL
    await contains(inputSelector).edit("/page2");
    await contains(inputSelector).click();
    await contains(
        document.querySelector(".o_website_ui_autocomplete > li:nth-child(2) a")
    ).click();

    // Verify disabled inputs contain the added URLs
    const selectedInputs = document.querySelectorAll(disabledInputSelector);
    expect(selectedInputs).toHaveLength(2);
    expect(selectedInputs[0].value).toBe("/page1");
    expect(selectedInputs[1].value).toBe("/page2");

    // Check data attribute is updated correctly
    await expect(":iframe .test-options-target").toHaveAttribute(
        "data-urls",
        JSON.stringify(["/page1", "/page2"])
    );
});

test("does not add duplicate URLs", async () => {
    mockGetSuggestedLinks();
    addOption({
        selector: ".test-options-target",
        template: xml`<WebsiteMultiUrlPicker dataAttributeAction="'urls'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    const inputSelector = ".we-bg-options-container input.o-hb-input-base:not(:disabled)";
    const disabledInputSelector = ".we-bg-options-container input.o-hb-input-base:disabled";

    // Add URL
    await contains(inputSelector).edit("/page1");
    await contains(inputSelector).click();
    await contains(
        document.querySelector(".o_website_ui_autocomplete > li:nth-child(1) a")
    ).click();
    const selectedInputs = document.querySelectorAll(disabledInputSelector);
    expect(selectedInputs[0].value).toBe("/page1");

    // Try to add duplicate
    await contains(inputSelector).edit("/page1");
    await contains(inputSelector).click();
    await contains(
        document.querySelector(".o_website_ui_autocomplete > li:nth-child(1) a")
    ).click();
    expect(selectedInputs).toHaveLength(1);
});

test("can remove a URL", async () => {
    mockGetSuggestedLinks();
    addOption({
        selector: ".test-options-target",
        template: xml`<WebsiteMultiUrlPicker dataAttributeAction="'urls'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    const inputSelector = ".we-bg-options-container input.o-hb-input-base:not(:disabled)";
    const disabledInputSelector = ".we-bg-options-container input.o-hb-input-base:disabled";

    // Add URLs
    await contains(inputSelector).edit("/page1");
    await contains(inputSelector).click();
    await contains(
        document.querySelector(".o_website_ui_autocomplete > li:nth-child(1) a")
    ).click();
    await contains(inputSelector).edit("/page2");
    await contains(inputSelector).click();
    await contains(
        document.querySelector(".o_website_ui_autocomplete > li:nth-child(2) a")
    ).click();

    // Remove first URL
    await contains(".we-bg-options-container button.fa-minus:nth-child(1)").click();
    const selectedUrls = document.querySelectorAll(disabledInputSelector);
    expect(selectedUrls).toHaveLength(1);
    expect(selectedUrls[0].value).toBe("/page2");
    await expect(":iframe .test-options-target").toHaveAttribute(
        "data-urls",
        JSON.stringify(["/page2"])
    );
});

test("previously selected URLs", async () => {
    mockGetSuggestedLinks();
    addOption({
        selector: ".test-options-target",
        template: xml`<WebsiteMultiUrlPicker dataAttributeAction="'urls'"/>`,
    });
    await setupWebsiteBuilder(
        `<div class="test-options-target" data-urls='["/page1", "/page2"]'>b</div>`
    );
    await contains(":iframe .test-options-target").click();

    const disabledInputSelector = ".we-bg-options-container input.o-hb-input-base:disabled";
    const selectedInputs = document.querySelectorAll(disabledInputSelector);
    expect(selectedInputs).toHaveLength(2);
    expect(selectedInputs[0].value).toBe("/page1");
    expect(selectedInputs[1].value).toBe("/page2");
});
