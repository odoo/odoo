import { animationFrame, expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    addPlugin,
    defineWebsiteModels,
    insertCategorySnippet,
    setupWebsiteBuilder,
} from "./website_helpers";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";

defineWebsiteModels();

test("dropping a floating snippet moves it to the end of the container", async () => {
    class TestPlugin extends Plugin {
        static id = "a";
        resources = {
            floating_snippets_selectors: ".s_banner",
        };
    }
    addPlugin(TestPlugin);
    await setupWebsiteBuilder("<section class='first-snippet'>First snippet</section>", {
        loadAssetsFrontendJS: true,
    });
    await insertCategorySnippet({ group: "intro", snippet: "s_banner" });
    await animationFrame();
    expect(":iframe #wrap.o_savable > .s_banner:last-child").toHaveCount(1);
});

test("can move a snippet to a provided custom scope", async () => {
    class TestPlugin extends Plugin {
        static id = "a";
        resources = {
            floating_snippet_scope_providers: [
                withSequence(10, {
                    value: "customContainer",
                    label: "Custom",
                    containerSelector: ".custom-container",
                }),
            ],
        };
    }
    addPlugin(TestPlugin);
    const { waitSidebarUpdated } = await setupWebsiteBuilder("<section class='custom-container'", {
        loadIframeBundles: true,
        loadAssetsFrontendJS: true,
    });
    await insertCategorySnippet({ group: "content", snippet: "s_popup" });
    await waitSidebarUpdated();
    expect(":iframe .custom-container > *").toHaveCount(0);
    expect(":iframe .s_popup .modal").toBeVisible();
    await contains(":iframe .s_popup .modal").click();
    await contains(".hb-row[data-label='Show on'] .dropdown-toggle").click();
    await contains(".dropdown-item[data-action-value='customContainer']").click();
    await waitSidebarUpdated();
    expect(":iframe .custom-container > *").toHaveCount(1);
    expect(":iframe .custom-container > .s_popup").toHaveCount(1);
    expect(":iframe .s_popup").toHaveAttribute("data-show-on", "customContainer");
});
