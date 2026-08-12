import { after, before, expect, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { addBuilderOption } from "@html_builder/../tests/helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { advanceTime, queryAllTexts } from "@odoo/hoot-dom";
import { browser } from "@web/core/browser/browser";

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

test("link button opens in new window if url not empty", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderUrlPicker dataAttributeAction="'url'"/>`,
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
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderUrlPicker dataAttributeAction="'url'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    await contains(".we-bg-options-container input").edit("/", { confirm: false });
    await advanceTime(250);
    expect.verifySteps(["button_immediate_install"]);
    expect(document.querySelector(".o_website_ui_autocomplete")).toBeVisible();
});

test("selects and commits value from dropdown", async () => {
    mockGetSuggestedLinks();
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderUrlPicker dataAttributeAction="'url'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    await contains(".we-bg-options-container input").edit("/", { confirm: false });
    await advanceTime(250);
    await contains(document.querySelector(".o_website_ui_autocomplete > li:first-child a")).click();
    expect(document.querySelector(".o_website_ui_autocomplete")).toBe(null);
    // The last modified page is now the first suggestion.
    expect(".we-bg-options-container input").toHaveValue("/page3");
    expect(":iframe .test-options-target").toHaveAttribute("data-url", "/page3");
});

test("suggests the recently used URL on top when nothing was typed yet", async () => {
    mockGetSuggestedLinks();
    browser.localStorage.setItem("website.recently_used_url", "/app1");
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderUrlPicker dataAttributeAction="'url'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    await contains(".we-bg-options-container input").edit("/", { confirm: false });
    await advanceTime(250);

    expect(queryAllTexts(".o_website_ui_autocomplete > li a")).toEqual([
        "/app1 (App 1)",
        "/page3 (Page 3)",
        "/page1 (Page 1)",
        "/page2 (Page 2)",
    ]);
});

test("the recently used URL matching what is typed comes first", async () => {
    mockGetSuggestedLinks();
    browser.localStorage.setItem("website.recently_used_url", "/page1");
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderUrlPicker dataAttributeAction="'url'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    await contains(".we-bg-options-container input").edit("/page", { confirm: false });
    await advanceTime(250);

    expect(queryAllTexts(".o_website_ui_autocomplete > li a")).toEqual([
        "/page1 (Page 1)",
        "/page3 (Page 3)",
        "/page2 (Page 2)",
        "/app1 (App 1)",
    ]);
});

test("the recently used URL is not suggested when it does not match", async () => {
    mockGetSuggestedLinks();
    browser.localStorage.setItem("website.recently_used_url", "/contactus");
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderUrlPicker dataAttributeAction="'url'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();

    await contains(".we-bg-options-container input").edit("/page", { confirm: false });
    await advanceTime(250);

    expect(queryAllTexts(".o_website_ui_autocomplete > li a")).toEqual([
        "/page3 (Page 3)",
        "/page1 (Page 1)",
        "/page2 (Page 2)",
        "/app1 (App 1)",
    ]);
});

test("collects anchors in current page and suggests them", async () => {
    mockGetSuggestedLinks();
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderUrlPicker dataAttributeAction="'url'"/>`,
    });
    await setupWebsiteBuilder(`
        <div class="test-options-target">b</div>
        <div id="anchor1" data-anchor="true">anchor1</div>
        <div id="anchor2" data-anchor="true">anchor2</div>
    `);
    await contains(":iframe .test-options-target").click();
    await contains(".we-bg-options-container input").edit("#", { confirm: false });
    await advanceTime(250);

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
