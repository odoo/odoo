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

test("link button opens in new window if url not empty", async () => {
    addOption({
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
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderUrlPicker dataAttributeAction="'url'"/>`,
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
        template: xml`<BuilderUrlPicker dataAttributeAction="'url'"/>`,
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
