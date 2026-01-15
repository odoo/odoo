import { before, expect, test, waitFor } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains, onRpc, models, defineModels } from "@web/../tests/web_test_helpers";
import {
    addOption,
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { waitForEndOfOperation } from "@html_builder/../tests/helpers";

defineWebsiteModels();

before(async () => {
    class WebEditorAssets extends models.Model {
        _name = "website.assets";
        make_scss_customization(location, changes) {
            expect.step("make_scss_customization");
        }
    }
    defineModels([WebEditorAssets]);

    onRpc("/website/theme_customize_data", async () => {
        expect.step("theme_customize_data");
    });

    onRpc("/website/theme_customize_bundle_reload", async () => {
        expect.step("bundle_reload");
        return { success: true };
    });

    addOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderButton action="'websiteConfig'" actionParam="{views: ['test_view']}">view_option</BuilderButton>`,
    });
    addOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderButton action="'websiteConfig'" actionParam="{assets: ['test_asset']}">asset_option</BuilderButton>`,
    });
});

test("customize website actions are properly reverted on discard", async () => {
    onRpc("/website/rollback", async (request) => {
        expect.step("rollback");
        const { params } = await request.json();
        expect(params.theme).toEqual({
            views: {
                enable: [],
                disable: ["test_view"],
            },
            assets: {
                enable: [],
                disable: ["test_asset"],
            },
        });

        expect(params.scss).toEqual({
            "/website/static/src/scss/options/user_values.scss": {
                layout: "null",
            },
        });
    });

    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);

    // Click on the test options to simulate a theme_customize_data RPC call
    await contains(":iframe .test-options-target").click();
    await contains("[data-action-id=websiteConfig]:contains('view_option')").click();
    await expect.waitForSteps(["theme_customize_data"]);

    await contains(":iframe .test-options-target").click();
    await contains("[data-action-id=websiteConfig]:contains('asset_option')").click();
    await expect.waitForSteps(["theme_customize_data"]);

    // Edit a theme value to simulate a make_scss_customization ORM call
    await contains("#theme-tab").click();
    await contains("[data-label='Page Layout'] button").click();
    await contains("[data-action-value='boxed']").click();
    await expect.waitForSteps(["make_scss_customization", "bundle_reload"]);

    // Check that when pressing discard a rollback RPC call is sent containing
    // the original values
    await contains(".o-snippets-top-actions [data-action='cancel']").click();
    await contains(".modal-content footer .btn-primary").click();
    await expect.waitForSteps(["rollback"]);
});

test("rollback data should not be kept from from one editing session to the other", async () => {
    onRpc("/website/rollback", async () => {
        expect.step("rollback");
    });

    const { openBuilderSidebar } = await setupWebsiteBuilder("");

    // Edit a theme value to simulate a make_scss_customization ORM call
    await contains("#theme-tab").click();
    await contains("[data-label='Page Layout'] button").click();
    await contains("[data-action-value='boxed']").click();
    await expect.waitForSteps(["make_scss_customization", "bundle_reload"]);

    // Save
    await contains(".o-snippets-top-actions [data-action='save']").click();
    await waitFor(".o-website-builder_sidebar:not(.o_builder_sidebar_open)");
    expect.verifySteps([], {
        message: "Rollback is not called on save",
    });

    // Cancel without changing anything
    await openBuilderSidebar();
    await contains(".o-snippets-top-actions [data-action='cancel']").click();
    await waitFor(".o-website-builder_sidebar:not(.o_builder_sidebar_open)");
    expect.verifySteps([], {
        message: "Rollback is not called since nothing was modified in this editing session",
    });
});

test("header rollback", async () => {
    let enabled = ["website.template_header_default"];
    onRpc("/website/theme_customize_data_get", async () => enabled);
    onRpc("/website/theme_customize_data", async (request) => {
        const { params } = await request.json();
        expect.step(JSON.stringify(params.enable));
        enabled = params.enable;
    });

    onRpc("/website/rollback", async (request) => {
        const { params } = await request.json();
        expect(params.theme).toEqual({
            views: {
                enable: ["website.template_header_default"],
                disable: [
                    "website.template_header_hamburger",
                    "website.no_autohide_menu",
                    "website.template_header_boxed",
                    "website.template_header_stretch",
                    "website.template_header_vertical",
                    "website.template_header_search",
                    "website.template_header_sales_one",
                    "website.template_header_sales_two",
                    "website.template_header_sales_three",
                    "website.template_header_sales_four",
                    "website.template_header_sidebar",
                ],
            },
        });
        expect.step("rollback");
    });

    await setupWebsiteBuilder("", {
        beforeWrapwrapContent: `<input type="hidden" class="o_page_option_data" autocomplete="off" name="header_visible">`,
        headerContent: `
            <header id="top" data-anchor="true" data-name="Header">
                    Header
            </header>`,
    });

    await contains(":iframe header").click();

    // Change the header template a couple times
    await contains("[data-label=Template] button").click();
    await contains("[data-action-param*='website.template_header_hamburger']").click();
    await waitForEndOfOperation();
    expect.verifySteps([
        '["website.template_header_hamburger","website.no_autohide_menu"]',
        "theme_customize_data",
        "make_scss_customization",
        "bundle_reload",
    ]);

    await contains("[data-label=Template] button").click();
    await contains("[data-action-param*='website.template_header_boxed']").click();
    await waitForEndOfOperation();
    expect.verifySteps([
        '["website.template_header_boxed"]',
        "theme_customize_data",
        "make_scss_customization",
        "bundle_reload",
    ]);
    await waitForEndOfOperation();

    // Discard
    await contains(".o-snippets-top-actions [data-action='cancel']").click();
    await contains(".modal-content footer .btn-primary").click();
    await expect.waitForSteps(["rollback"]);
});
