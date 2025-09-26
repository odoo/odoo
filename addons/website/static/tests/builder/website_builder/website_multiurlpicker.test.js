import { beforeEach, expect, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import {
    addOption,
    defineWebsiteModels,
    mockGetSuggestedLinks,
    setupWebsiteBuilder,
} from "../website_helpers";

defineWebsiteModels();

const inputSelector = ".we-bg-options-container input.o-hb-input-base:not(:disabled)";
const selectedUrlsSelector = ".we-bg-options-container input.o-hb-input-base:disabled";
const testOptionsTargetSelector = ":iframe .test-options-target";

beforeEach(async () => {
    mockGetSuggestedLinks();
    addOption({
        selector: ".test-options-target",
        template: xml`<WebsiteMultiUrlPicker dataAttributeAction="'urls'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(testOptionsTargetSelector).click();
});

test("opens dropdown when typing /", async () => {
    await contains(inputSelector).edit("/");
    await contains(inputSelector).click();
    expect(document.querySelector(".o_website_ui_autocomplete")).toBeVisible();
});

test("selects URL from dropdown by clicking", async () => {
    await contains(inputSelector).edit("/");
    await contains(inputSelector).click();
    await contains(document.querySelector(".o_website_ui_autocomplete > li:first-child a")).click();
    expect(inputSelector).toHaveValue("");
    expect(document.querySelector(".o_website_ui_autocomplete")).toBe(null);
    expect(selectedUrlsSelector).toHaveValue("/page1");
    expect(testOptionsTargetSelector).toHaveAttribute("data-urls", '["/page1"]');
});

test("selects URL from dropdown by pressing Enter", async () => {
    await contains(inputSelector).edit("/");
    await contains(inputSelector).click();
    await contains(document.querySelector(".o_website_ui_autocomplete > li:first-child a")).press(
        "Enter"
    );
    expect(inputSelector).toHaveValue("");
    expect(document.querySelector(".o_website_ui_autocomplete")).toBe(null);
    expect(selectedUrlsSelector).toHaveValue("/page1");
    expect(testOptionsTargetSelector).toHaveAttribute("data-urls", '["/page1"]');
});
