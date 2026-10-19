import {
    confirmAddSnippet,
    getDragHelper,
    waitForEndOfOperation,
} from "@html_builder/../tests/helpers";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    addPlugin,
    defineWebsiteModels,
    insertCategorySnippet,
    setupWebsiteBuilder,
} from "./website_helpers";

defineWebsiteModels();

test("dropping a floating snippet moves it to the end of the container", async () => {
    class TestPlugin extends Plugin {
        static id = "a";
        resources = {
            floating_snippets_selectors: ".s_banner",
        };
    }
    addPlugin(TestPlugin);
    await setupWebsiteBuilder("<section class='first-snippet'>First snippet</section>");

    const { moveTo, drop } = await contains(
        ".o-website-builder_sidebar [data-snippet-group='intro'] .o_snippet_thumbnail"
    ).drag();
    // Drop the snippet in the first dropzone.
    await moveTo(":iframe .oe_drop_zone:first");
    await drop(getDragHelper());
    await confirmAddSnippet("s_banner");
    await waitForEndOfOperation();

    expect(":iframe #wrap.o_savable > .s_banner:last-child").toHaveCount(1);
});

test("can move a snippet to a provided custom scope", async () => {
    class TestPlugin extends Plugin {
        static id = "a";
        resources = {
            floating_snippet_scope_providers: [
                withSequence(10, {
                    label: "Custom",
                    containerSelector: ".custom-container",
                }),
            ],
        };
    }
    addPlugin(TestPlugin);
    const { waitSidebarUpdated } = await setupWebsiteBuilder(
        "<section class='custom-container' />",
        {
            loadIframeBundles: true,
            loadAssetsFrontendJS: true,
        }
    );
    await insertCategorySnippet({ group: "content", snippet: "s_popup" });
    await waitSidebarUpdated();
    expect(":iframe .custom-container > *").toHaveCount(0);
    expect(":iframe .s_popup .modal").toBeVisible();
    await contains(":iframe .s_popup .modal").click();
    await contains(".hb-row[data-label='Show on'] .dropdown-toggle").click();
    await contains(".dropdown-item:contains('Custom')").click();
    await waitSidebarUpdated();
    expect(":iframe .custom-container > *").toHaveCount(1);
    expect(":iframe .custom-container > .s_popup").toHaveCount(1);
});

test("inserted snippet should be inserted in 'This page' container by default", async () => {
    class TestPlugin extends Plugin {
        static id = "a";
        resources = {
            floating_snippets_selectors: ".s_banner",
            floating_snippet_scope_providers: [
                withSequence(10, {
                    label: "This page",
                    containerSelector: ".custom-container",
                    isThisPage: true,
                }),
            ],
        };
    }
    addPlugin(TestPlugin);
    const { waitSidebarUpdated } = await setupWebsiteBuilder("<section class='custom-container'/>");
    await insertCategorySnippet({ group: "intro", snippet: "s_banner" });
    await waitSidebarUpdated();
    expect(":iframe .custom-container > .s_banner").toHaveCount(1);
});
