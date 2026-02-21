import { expect, queryFirst, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();
const snippetHTML = `
    <section class="s_banner o_half_screen_height" data-snippet="s_banner" data-name="Banner" contenteditable="false">
        <div contenteditable="true" class="container">
        </div>
    </section>`;

test("Can change the height of a snippet when it has o_half_screen_height class", async () => {
    await setupWebsiteBuilder(snippetHTML, {
        loadIframeBundles: true,
    });
    expect(":iframe .s_banner").toHaveClass("o_half_screen_height");
    const snippetEl = queryFirst(":iframe .s_banner");
    const initialHeight = getComputedStyle(snippetEl).height;
    await contains(":iframe .s_banner").click();
    expect("[data-action-param='o_three_quarter_height']").not.toHaveClass("active");
    await contains("[data-action-param='o_three_quarter_height']").click();

    expect(":iframe .s_banner").not.toHaveClass("o_half_screen_height");
    expect(":iframe .s_banner").not.toHaveStyle({ height: initialHeight });
});
