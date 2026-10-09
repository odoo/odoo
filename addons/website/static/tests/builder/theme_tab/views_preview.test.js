import { expect, queryFirst, test } from "@odoo/hoot";
import { waitFor, waitForNone } from "@odoo/hoot-dom";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";
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
    // Committed once rendered.
    await waitFor("[data-label='Show Header'] input[type='checkbox']:not(:checked)");
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

test("a view of the page's content renders it again, keeping its unsaved edits", async () => {
    const page = (isOn) => `<main>
        <div class="test-options-target">
            <div class="o_savable" data-oe-model="ir.ui.view" data-oe-id="5" data-oe-field="arch">Text</div>
            ${isOn ? `<p class="test-view-on">View</p>` : ""}
        </div></main>`;
    onRpc("/blank", async (request) => {
        const views = JSON.parse(new URL(request.url).searchParams.get("theme_preview_views"));
        expect.step("render");
        return new Response(
            `<html><body><div id="wrapwrap"><header id="top">Header</header>${page(
                views.page_view
            )}</div></body></html>`
        );
    });
    onRpc("/website/theme_customize_data_get", () => []);
    addBuilderOption({
        selector: ".test-options-target",
        editableOnly: false,
        template: xml`
            <BuilderCheckbox action="'previewPageConfig'" actionParam="{views: ['page_view']}"/>
        `,
    });
    const { getEditor } = await setupWebsiteBuilder("", {
        headerContent: `<header id="top">Header</header>${page(false)}`,
    });
    const savableEl = queryFirst(":iframe main .o_savable");
    // An unsaved edit, a step of its own.
    savableEl.textContent = "Edited";
    savableEl.classList.add("o_dirty");
    getEditor().shared.history.commit();
    await contains(":iframe .test-options-target").click();
    await contains(".o_customize_tab input[type='checkbox']").click();
    await waitFor(":iframe main .test-view-on");
    await expect.waitForSteps(["render", "render"]);
    // The edited element itself, in the new content; the options on it.
    expect(queryFirst(":iframe main .o_savable")).toBe(savableEl);
    expect(":iframe main .o_savable").toHaveText("Edited");
    expect(".o_customize_tab input[type='checkbox']").toBeChecked();
    await contains(".o-snippets-top-actions button[data-icon='undo']").click();
    await waitForNone(":iframe main .test-view-on");
    expect(queryFirst(":iframe main .o_savable")).toBe(savableEl);
});

test("an edit in a part rendered for a views switch is recorded", async () => {
    onRpc("/website/theme_customize_data_get", () => []);
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderCheckbox action="'previewWebsiteConfig'" actionParam="{views: ['other_view']}"/>
        `,
    });
    onRpc("/blank", (request) => {
        const views = JSON.parse(new URL(request.url).searchParams.get("theme_preview_views"));
        const header = views.other_view ? `<p class="new">New</p>` : "Header";
        return new Response(
            `<html><body><div id="wrapwrap"><header id="top">${header}</header><main></main></div></body></html>`
        );
    });
    const { getEditor } = await setupWebsiteBuilder(`<div class="test-options-target">b</div>`, {
        headerContent: `<header id="top">Header</header><main></main>`,
    });
    await contains(":iframe .test-options-target").click();
    await contains(".o_customize_tab input[type='checkbox']").click();
    await waitFor(":iframe header#top .new");
    const newEl = queryFirst(":iframe header#top .new");
    newEl.classList.add("edited");
    getEditor().shared.history.commit();
    await contains(".o-snippets-top-actions button[data-icon='undo']").click();
    expect(newEl).not.toHaveClass("edited");
});

test("the options of a part rendered for a views switch are updated, not rebuilt", async () => {
    onRpc("/website/theme_customize_data_get", () => []);
    onRpc("/blank", (request) => {
        const views = JSON.parse(new URL(request.url).searchParams.get("theme_preview_views"));
        return new Response(
            `<html><body><div id="wrapwrap"><header id="top">${
                views.other_view ? "New" : "Header"
            }</header><main></main></div></body></html>`
        );
    });
    addBuilderOption({
        selector: "#wrapwrap > header",
        editableOnly: false,
        template: xml`
            <BuilderRow label="'Layout'">
                <BuilderCheckbox action="'previewWebsiteConfig'" actionParam="{views: ['other_view']}"/>
            </BuilderRow>
        `,
    });
    await setupWebsiteBuilder("", {
        headerContent: `<header id="top">Header</header><main></main>`,
    });
    await contains(":iframe header#top").click();
    const containerEl = queryFirst(
        ".o_customize_tab .options-container:has([data-label='Layout'])"
    );
    await contains("[data-label='Layout'] input[type='checkbox']").click();
    await waitFor(":iframe header#top:contains(New)");
    await waitFor("[data-label='Layout'] input[type='checkbox']:checked");
    await runAllTimers();
    await animationFrame();
    expect(queryFirst(".o_customize_tab .options-container:has([data-label='Layout'])")).toBe(
        containerEl
    );
});

test("after a layout switch, the options go to the same element, not the same position", async () => {
    onRpc("/website/theme_customize_data_get", () => []);
    onRpc("/blank", (request) => {
        const views = JSON.parse(new URL(request.url).searchParams.get("theme_preview_views"));
        const content = views.other_view
            ? `<div class="test-logo">Logo</div><div id="test-menu">Menu</div>`
            : `<div class="test-text">Text</div><div id="test-menu">Menu</div>`;
        return new Response(
            `<html><body><div id="wrapwrap"><header id="top">${content}</header><main></main></div></body></html>`
        );
    });
    // Switched from the element the switch takes out.
    addBuilderOption({
        selector: ".test-text",
        editableOnly: false,
        template: xml`
            <BuilderRow label="'Layout'">
                <BuilderCheckbox action="'previewWebsiteConfig'" actionParam="{views: ['other_view']}"/>
            </BuilderRow>
        `,
    });
    for (const name of ["logo", "text"]) {
        addBuilderOption({
            selector: `.test-${name}`,
            editableOnly: false,
            template: xml`<BuilderRow label="'${name}'"><BuilderButton classAction="'x'"/></BuilderRow>`,
        });
    }
    await setupWebsiteBuilder("", {
        headerContent: `<header id="top"><div class="test-text">Text</div><div id="test-menu">Menu</div></header><main></main>`,
    });
    // An element without a counterpart: the options go to the header.
    await contains(":iframe header#top .test-text").click();
    await contains("[data-label='Layout'] input[type='checkbox']").click();
    await waitFor(":iframe header#top .test-logo");
    await waitForNone("[data-label='Layout']");
    expect("[data-label='logo']").toHaveCount(0);
    expect("[data-label='text']").toHaveCount(0);
});

test("after a views switch, the options stay on an element known by its classes", async () => {
    onRpc("/website/theme_customize_data_get", () => []);
    onRpc("/blank", (request) => {
        const views = JSON.parse(new URL(request.url).searchParams.get("theme_preview_views"));
        return new Response(
            `<html><body><div id="wrapwrap"><main></main><footer id="bottom"><div class="test-bar">${
                views.other_view ? "New" : "Bar"
            }</div></footer></div></body></html>`
        );
    });
    addBuilderOption({
        selector: ".test-bar",
        editableOnly: false,
        template: xml`
            <BuilderRow label="'Bar'">
                <BuilderCheckbox action="'previewWebsiteConfig'" actionParam="{views: ['other_view']}"/>
            </BuilderRow>
        `,
    });
    await setupWebsiteBuilder("", {
        headerContent: `<main></main>`,
        footerContent: `<footer id="bottom"><div class="test-bar">Bar</div></footer>`,
    });
    await contains(":iframe footer#bottom .test-bar").click();
    await contains("[data-label='Bar'] input[type='checkbox']").click();
    await waitFor(":iframe footer#bottom .test-bar:contains(New)");
    await runAllTimers();
    await animationFrame();
    expect("[data-label='Bar'] input[type='checkbox']").toBeChecked();
});
