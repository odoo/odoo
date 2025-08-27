import { expect, test } from "@odoo/hoot";
import { registry } from "@web/core/registry";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import {
    confirmAddSnippet,
    getDragHelper,
    waitForEndOfOperation,
} from "@html_builder/../tests/helpers";

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

    let iframeEl;
    await setupWebsiteBuilder("", {
        onIframeLoaded: (iframe) => (iframeEl = iframe),
    });
    const { moveTo, drop } = await contains(
        ".o-snippets-menu #snippet_groups .o_snippet_thumbnail"
    ).drag();
    await moveTo(iframeEl);
    await drop(getDragHelper());
    await confirmAddSnippet();
    await waitForEndOfOperation();
    expect(":iframe [data-snippet='s_banner']").toHaveClass("preprocessed");
});
