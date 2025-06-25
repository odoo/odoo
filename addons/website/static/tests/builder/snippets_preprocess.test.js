import { expect, test } from "@odoo/hoot";
import { registry } from "@web/core/registry";
import { contains } from "@web/../tests/web_test_helpers";
import {
    confirmAddSnippet,
    defineWebsiteModels,
    getDragHelper,
    setupWebsiteBuilder,
    waitForEndOfOperation,
} from "./website_helpers";

defineWebsiteModels();

test("preprocess modifies the snippet", async () => {
    registry
        .category("html_builder.snippetsPreprocessor")
        .add("test_snippets", function (namespace, snippets) {
            const bannerEls = snippets.querySelectorAll(".s_banner");
            for (const bannerEl of bannerEls) {
                bannerEl.classList.add("preprocessed");
            }
        });

    const { getIframeEl } = await setupWebsiteBuilder();
    const { moveTo, drop } = await contains(
        ".o-snippets-menu #snippet_groups .o_snippet_thumbnail"
    ).drag();
    await moveTo(getIframeEl());
    await drop(getDragHelper());
    await confirmAddSnippet();
    await waitForEndOfOperation();
    expect(":iframe [data-snippet='s_banner']").toHaveClass("preprocessed");
});
