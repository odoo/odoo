import { after, before, expect, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import {
    addOption,
    defineWebsiteModels,
    mockGetSuggestedLinks,
    setupWebsiteBuilder,
} from "../../website_helpers";

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

before(() => {
    mockWindowOpen();
});
after(() => {
    unmockWindowOpen();
});

test("link button opens in new window if url not empty", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<WebsiteUrlPicker dataAttributeAction="'url'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    await contains(".we-bg-options-container button").click();

    await contains(".we-bg-options-container input").edit("/url");
    await contains(".we-bg-options-container button").click();
    expect.verifySteps(["callWindowOpen /url"]);

    await contains(".we-bg-options-container input").edit("");
    await contains(".we-bg-options-container button").click();
});

test("opens dropdown when typing /", async () => {
    mockGetSuggestedLinks(() => {
        expect.step("button_immediate_install");
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<WebsiteUrlPicker dataAttributeAction="'url'"/>`,
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
        template: xml`<WebsiteUrlPicker dataAttributeAction="'url'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    await contains(".we-bg-options-container input").edit("/");
    await contains(".we-bg-options-container input").click();
    await contains(document.querySelector(".o_website_ui_autocomplete > li:first-child a")).click();
    expect(document.querySelector(".o_website_ui_autocomplete")).toBe(null);
    expect(".we-bg-options-container input").toHaveValue("/page1");
    expect(":iframe .test-options-target").toHaveAttribute("data-url", "/page1");
});

test("collects anchors in current page and suggests them", async () => {
    mockGetSuggestedLinks();
    addOption({
        selector: ".test-options-target",
        template: xml`<WebsiteUrlPicker dataAttributeAction="'url'"/>`,
    });
    await setupWebsiteBuilder(`
        <div class="test-options-target">b</div>
        <div id="anchor1" data-anchor="true">anchor1</div>
        <div id="anchor2" data-anchor="true">anchor2</div>
    `);
    await contains(":iframe .test-options-target").click();
    await contains(".we-bg-options-container input").edit("#");
    await contains(".we-bg-options-container input").click();

    // Check autocomplete suggests both anchors
    const els = document.querySelectorAll(".o_website_ui_autocomplete > li a");
    expect(els).toHaveLength(4); // Our anchors, #top and #bottom
    expect(els[1].innerText).toBe("#anchor1");
    expect(els[2].innerText).toBe("#anchor2");

    // Check clicking on one of them properly applies
    await contains(els[1]).click();
    expect(".we-bg-options-container input").toHaveValue("#anchor1");
    await expect(":iframe .test-options-target").toHaveAttribute("data-url", "#anchor1");
});
