import { expect, queryFirst, test } from "@odoo/hoot";
import { waitFor, waitForNone } from "@odoo/hoot-dom";
import { runAllTimers } from "@odoo/hoot-mock";
import { xml } from "@odoo/owl";
import { addBuilderOption } from "@html_builder/../tests/helpers";
import { contains, defineModels, models, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

const HIDE_HEADER = "website.option_layout_hide_header";

// The page as the server renders it with the previewed views (the test's
// iframe is at "blank").
function mockPageRenders() {
    onRpc("/blank", async (request) => {
        const views = new URL(request.url).searchParams.get("theme_preview_views");
        expect.step(`render ${views}`);
        const header = JSON.parse(views)[HIDE_HEADER] ? "" : `<header id="top">Header</header>`;
        return new Response(
            `<html><body><div id="wrapwrap">${header}<main></main></div></body></html>`
        );
    });
}

test("a views switch is previewed without a reload, undone, and written on save", async () => {
    mockPageRenders();
    onRpc("/website/theme_customize_data_get", () => []);
    onRpc("/website/theme_customize_data", async (request) => {
        const { params } = await request.json();
        expect.step(`write ${JSON.stringify(params)}`);
    });
    await setupWebsiteBuilder("", {
        headerContent: `<header id="top">Header</header><main></main>`,
    });
    const liveHeaderEl = queryFirst(":iframe header#top");
    await contains("#theme-tab").click();
    await contains("[data-label='Show Header'] input[type='checkbox']").click();
    await waitForNone(":iframe header#top");
    expect.verifySteps([`render {}`, `render {"${HIDE_HEADER}":true}`]);

    await contains(".o-snippets-top-actions button[data-icon='undo']").click();
    await waitFor(":iframe header#top");
    // The same element, with its state.
    expect(queryFirst(":iframe header#top")).toBe(liveHeaderEl);
    expect("[data-label='Show Header'] input[type='checkbox']").toBeChecked();

    await contains(".o-snippets-top-actions button[data-icon='redo']").click();
    await waitForNone(":iframe header#top");
    expect.verifySteps([]);

    await contains(".o-snippets-top-actions [data-action='save']").click();
    await waitForNone(".o-snippets-top-actions");
    expect.verifySteps([
        `write {"is_view_data":true,"enable":["${HIDE_HEADER}"],"disable":[],"reset_view_arch":false}`,
    ]);
});

test("a views switch that resets its view is written with the reset on save", async () => {
    mockPageRenders();
    onRpc("/website/theme_customize_data_get", () => ["test_view"]);
    onRpc("/website/theme_customize_data", async (request) => {
        const { params } = await request.json();
        expect.step(`write ${JSON.stringify(params)}`);
    });
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderCheckbox action="'previewWebsiteConfig'" actionParam="{views: ['test_view'], resetViewArch: true}"/>
        `,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`, {
        headerContent: `<header id="top">Header</header><main></main>`,
    });
    await contains(":iframe .test-options-target").click();
    await contains(".o_customize_tab input[type='checkbox']").click();
    expect(".o_customize_tab input[type='checkbox']").not.toBeChecked();
    await expect.waitForSteps([`render {}`, `render {"test_view":false}`]);
    await contains(".o-snippets-top-actions [data-action='save']").click();
    await waitForNone(".o-snippets-top-actions");
    expect.verifySteps([
        `write {"is_view_data":true,"disable":["test_view"],"reset_view_arch":true}`,
    ]);
});

test("a footer template is previewed, written on save with its copyright width", async () => {
    onRpc("/blank", async (request) => {
        const views = JSON.parse(new URL(request.url).searchParams.get("theme_preview_views"));
        const footer = views["website.template_footer_descriptive"] ? "Descriptive" : "Footer";
        return new Response(
            `<html><body><div id="wrapwrap"><main></main><footer id="bottom">${footer}</footer></div></body></html>`
        );
    });
    onRpc("/website/theme_customize_data", async (request) => {
        const { params } = await request.json();
        expect.step(`write ${params.enable.join(",")}`);
    });
    onRpc("/website/update_footer_template", async (request) => {
        const { params } = await request.json();
        expect.step(`footer ${params.template_key}`);
    });
    class WebsiteAssets extends models.Model {
        _name = "website.assets";
        make_scss_customization(location, changes) {
            expect.step(`scss ${JSON.stringify(changes)}`);
        }
    }
    defineModels([WebsiteAssets]);
    await setupWebsiteBuilder("", {
        headerContent: `<main></main>`,
        footerContent: `<footer id="bottom" class="o_footer">Footer</footer>`,
    });
    await contains(":iframe footer#bottom").click();
    await contains("[data-label='Template'] .dropdown-toggle").click();
    await contains(".o_popover [title='Descriptive']").click();
    await waitFor(":iframe footer#bottom:contains(Descriptive)");
    expect.verifySteps([]);
    await contains(".o-snippets-top-actions [data-action='save']").click();
    await waitForNone(".o-snippets-top-actions");
    expect.verifySteps([
        "write website.template_footer_descriptive",
        "footer website.template_footer_descriptive",
        `scss {"footer-template":"descriptive"}`,
    ]);
});

test("the click effect's assets are written on save, without a reload", async () => {
    onRpc("/website/theme_customize_data_get", () => []);
    onRpc("/website/theme_customize_data", async (request) => {
        const { params } = await request.json();
        expect.step(`write ${JSON.stringify(params)}`);
    });
    class WebsiteAssets extends models.Model {
        _name = "website.assets";
        make_scss_customization(location, changes) {
            expect.step(`scss ${JSON.stringify(changes)}`);
        }
    }
    defineModels([WebsiteAssets]);
    await setupWebsiteBuilder("");
    await contains("#theme-tab").click();
    await contains("[data-label='On Click Effect'] .dropdown-toggle").click();
    await contains(".o_popover .dropdown-item:contains('Ripple')").click();
    expect.verifySteps([]);
    await contains(".o-snippets-top-actions button[data-icon='undo']").click();
    await contains(".o-snippets-top-actions button[data-icon='redo']").click();
    await contains(".o-snippets-top-actions [data-action='save']").click();
    await waitForNone(".o-snippets-top-actions");
    expect.verifySteps([
        `write {"is_view_data":false,"enable":["website.ripple_effect_scss","website.ripple_effect_js"],"disable":[]}`,
        `scss {"btn-ripple":"true"}`,
    ]);
});

test("a views switch isn't previewed on hover, and the page shows it's loading", async () => {
    const render = Promise.withResolvers();
    onRpc("/blank", async (request) => {
        const views = new URL(request.url).searchParams.get("theme_preview_views");
        expect.step(`render ${views}`);
        const isSwitched = JSON.parse(views).test_view;
        if (isSwitched) {
            await render.promise;
        }
        return new Response(
            `<html><body><div id="wrapwrap"><header id="top">${
                isSwitched ? "New" : "Header"
            }</header><main></main></div></body></html>`
        );
    });
    onRpc("/website/theme_customize_data_get", () => []);
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderCheckbox action="'previewWebsiteConfig'" actionParam="{views: ['test_view']}"/>
        `,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`, {
        headerContent: `<header id="top">Header</header><main></main>`,
    });
    await contains(":iframe .test-options-target").click();
    await contains(".o_customize_tab input[type='checkbox']").hover();
    await runAllTimers();
    expect.verifySteps([]);
    await contains(".o_customize_tab input[type='checkbox']").click();
    await expect.waitForSteps([`render {}`, `render {"test_view":true}`]);
    expect(":iframe header#top").toHaveClass("o_we_chrome_loading");
    render.resolve();
    await waitFor(":iframe header#top:contains(New)");
    expect(":iframe header#top").not.toHaveClass("o_we_chrome_loading");
});

test("a views switch shown by a class needs no render, and later renders show it", async () => {
    onRpc("/blank", async (request) => {
        expect.step(`render ${new URL(request.url).searchParams.get("theme_preview_views")}`);
        return new Response(
            `<html><body><div id="wrapwrap"><header id="top">Header</header><main></main></div></body></html>`
        );
    });
    onRpc("/website/theme_customize_data_get", () => []);
    onRpc("/website/theme_customize_data", async (request) => {
        const { params } = await request.json();
        expect.step(`write ${params.enable.join(",")}`);
    });
    // The class is an edit of the page.
    onRpc("ir.ui.view", "save", () => true);
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderRow label="'Shown'">
                <BuilderCheckbox action="'previewableWebsiteConfig'" actionParam="{views: ['shown_view'], previewClass: 'o_shown'}"/>
            </BuilderRow>
            <BuilderRow label="'Rendered'">
                <BuilderCheckbox action="'previewWebsiteConfig'" actionParam="{views: ['rendered_view']}"/>
            </BuilderRow>
        `,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`, {
        headerContent: `<header id="top">Header</header><main></main>`,
    });
    await contains(":iframe .test-options-target").click();
    await contains("[data-label='Shown'] input[type='checkbox']").click();
    expect(":iframe .test-options-target").toHaveClass("o_shown");
    await runAllTimers();
    expect.verifySteps([]);
    await contains("[data-label='Rendered'] input[type='checkbox']").click();
    await expect.waitForSteps([
        `render {"shown_view":true}`,
        `render {"rendered_view":true,"shown_view":true}`,
    ]);
    await contains(".o-snippets-top-actions [data-action='save']").click();
    await waitForNone(".o-snippets-top-actions");
    expect.verifySteps(["write shown_view,rendered_view"]);
});
