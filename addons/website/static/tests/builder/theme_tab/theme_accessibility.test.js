import { expect, queryAllTexts, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("link check reports links told apart by color only", async () => {
    await setupWebsiteBuilder("", {
        styleContent: `
            :root {
                --link-underline: 'never';
                --o-cc1-bg: #ffffff;
                --o-cc1-text: #212529;
                --o-cc1-link: #333333;
                --o-cc2-bg: #ffffff;
                --o-cc2-text: #212529;
                --o-cc2-link: #0d6efd;
            }
        `,
    });

    await contains(".o_hb_snippets_tabs button[data-name=theme]").click();
    await contains(
        ".o_theme_tab [data-container-title='Link'] button[title='Check accessibility']"
    ).click();
    await animationFrame();
    expect(queryAllTexts(".o_theme_accessibility_dialog li strong")).toEqual([
        "Links are never underlined",
        "Color preset #1: links look like the text",
    ]);
});
