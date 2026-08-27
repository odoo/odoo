import { getSnippetStructure } from "@html_builder/../tests/helpers";
import { expect, test, waitForNone } from "@odoo/hoot";
import { isDarkColorPalette } from "@website/components/dialog/dark_palette_utils";
import {
    contains,
    defineModels,
    defineStyle,
    getService,
    models,
    onRpc,
} from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    getStructureSnippet,
    setupWebsiteBuilder,
    waitForSnippetDialog,
} from "./website_helpers";

defineWebsiteModels();

test("snippet dialog uses dark palette content adaptations", async () => {
    class WebsiteAssets extends models.Model {
        _name = "website.assets";

        make_scss_customization() {}
    }
    defineModels([WebsiteAssets]);

    let pageDocument;
    const reloadPromise = Promise.withResolvers();
    onRpc("/website/theme_customize_bundle_reload", () => {
        pageDocument.documentElement.style.setProperty("--color-palettes-name", "'default-dark-1'");
        reloadPromise.resolve();
        return {};
    });

    const coverEl = await getStructureSnippet("s_cover");
    await setupWebsiteBuilder("", {
        snippets: {
            snippet_groups: [
                `<div name="Intro" data-oe-snippet-id="123" data-o-snippet-group="intro">
                    <section data-snippet="s_snippet_group"></section>
                </div>`,
            ],
            snippet_structure: [
                getSnippetStructure({
                    name: "Cover",
                    groupName: "intro",
                    content: coverEl.outerHTML,
                }),
            ],
        },
        styleContent: `:root { --color-palettes-name: 'default-light-1'; }`,
        onIframeLoaded: (iframeEl) => {
            pageDocument = iframeEl.contentDocument;
        },
    });
    getService("website").pageDocument = pageDocument;
    defineStyle(`:root { --o-palette-default-dark-1-is-dark: true; }`);

    // With a light palette, the dialog must show the original Cover snippet.
    // Its `o_cc5` preset must remain unchanged despite its black filter.
    await contains("[data-snippet-group='intro'] .o_snippet_thumbnail_area").click();
    await waitForSnippetDialog();
    expect(".o_add_snippet_dialog :iframe .s_cover").toHaveClass("o_cc5");
    expect(".o_add_snippet_dialog :iframe .s_cover").not.toHaveClass("o_cc1");
    expect(".o_add_snippet_dialog :iframe .s_cover > .o_we_bg_filter.bg-black-50").toHaveCount(1);
    await contains(".modal .btn-close").click();
    await waitForNone(".o_add_snippet_dialog");

    // Switch the website from a light palette to a dark palette.
    await contains("#theme-tab").click();
    await contains(".o-tab-content .o-hb-theme-color-slider-btn").click();
    await contains(
        ".o_theme_tab [data-src='/website/static/src/img/snippets_options/palette.svg']"
    ).click();
    await contains(`[data-action-value="'default-dark-1'"] .o-color-palette-card span`).click();
    await reloadPromise.promise;
    expect(isDarkColorPalette(pageDocument)).toBe(true);

    // Reopening the dialog creates a viewer for the new dark palette. The
    // black filter must make the dark-palette clone replace `o_cc5` with
    // `o_cc1`, which keeps its text readable over that dark filter.
    await contains("#blocks-tab").click();
    await contains("[data-snippet-group='intro'] .o_snippet_thumbnail_area").click();
    await waitForSnippetDialog();
    expect(".o_add_snippet_dialog :iframe .s_cover").toHaveClass("o_cc1");
    expect(".o_add_snippet_dialog :iframe .s_cover").not.toHaveClass("o_cc5");
});
