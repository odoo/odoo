import { expect, test } from "@odoo/hoot";
import { animationFrame, queryOne } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { addBuilderOption, dummyBase64Img } from "@html_builder/../tests/helpers";
import {
    contains,
    onRpc,
    models,
    defineModels,
    registerTemplate,
} from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { redo, undo } from "@html_editor/../tests/_helpers/user_actions";
import { ToggleBodyBgImageAction } from "@website/builder/plugins/customize_website_plugin";
import { patchDragImage } from "../image_test_helpers";

defineWebsiteModels();

test("BuilderButton with action “websiteConfig” are correctly displayed", async () => {
    const def = Promise.withResolvers();
    onRpc("/website/theme_customize_data_get", async (request) => {
        const { params } = await request.json();
        expect.step("theme_customize_data_get");
        expect(params.keys).toEqual(["test_template_1", "test_template_2"]);
        await def.promise;
        return ["test_template_2"];
    });
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderButton action="'websiteConfig'" actionParam="{views: ['test_template_1']}">1</BuilderButton>
            <BuilderButton action="'websiteConfig'" actionParam="{views: ['test_template_2']}">2</BuilderButton>
        `,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".o_hb_tab_content > .o_customize_tab").toHaveCount(0);

    def.resolve();
    await animationFrame();
    expect(".o_hb_tab_content > .o_customize_tab").toHaveCount(1);
    expect("[data-action-param*='test_template_1']").not.toHaveClass("active");
    expect("[data-action-param*='test_template_2']").toHaveClass("active");
    expect.verifySteps(["theme_customize_data_get"]);
});

test("click on BuilderButton with action “websiteConfig”", async () => {
    onRpc("/website/theme_customize_data_get", async (request) => {
        const { params } = await request.json();
        expect.step("theme_customize_data_get");
        expect(params.keys).toEqual(["test_template_1", "test_template_2"]);
        return ["test_template_2"];
    });
    onRpc("/website/theme_customize_data", async (request) => {
        const { params } = await request.json();
        expect.step("theme_customize_data");
        expect(params.enable).toEqual(["test_template_1"]);
        expect(params.disable).toEqual([]);
    });
    onRpc("ir.ui.view", "save", () => {
        expect.step("websiteSave");
        return true;
    });

    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderButton action="'websiteConfig'" actionParam="{views: ['test_template_1']}">1</BuilderButton>
            <BuilderButton action="'websiteConfig'" actionParam="{views: ['test_template_2']}">2</BuilderButton>
            <BuilderButton classAction="'a'">a</BuilderButton>
        `,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect.verifySteps(["theme_customize_data_get"]);
    await contains("[data-class-action='a']").click();

    await contains("[data-action-param*='test_template_1']").click();
    expect.verifySteps(["theme_customize_data", "websiteSave"]);
});

test("click on BuilderSelectItem with action “websiteConfig”", async () => {
    onRpc("/website/theme_customize_data_get", async (request) => {
        const { params } = await request.json();
        expect.step("theme_customize_data_get");
        expect(params.keys).toEqual(["test_template_1", "test_template_2"]);
        return ["test_template_2"];
    });
    onRpc("/website/theme_customize_data", async (request) => {
        const { params } = await request.json();
        expect.step("theme_customize_data");
        expect(params.enable).toEqual(["test_template_1"]);
        expect(params.disable).toEqual(["test_template_2"]);
    });
    onRpc("ir.ui.view", "save", () => {
        expect.step("websiteSave");
        return true;
    });

    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderSelect action="'websiteConfig'">
                <BuilderSelectItem actionParam="{views: ['test_template_1']}">1</BuilderSelectItem>
                <BuilderSelectItem actionParam="{views: ['test_template_2']}">2</BuilderSelectItem>
            </BuilderSelect>
        `,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect.verifySteps(["theme_customize_data_get"]);

    await contains(".o_hb_options_container .dropdown-toggle").click();
    await contains("[data-action-param*='test_template_1']").click();
    expect.verifySteps(["theme_customize_data"]);
});

test("use isActiveItem base on BuilderButton with 'websiteConfig'", async () => {
    const def = Promise.withResolvers();
    onRpc("/website/theme_customize_data_get", async (request) => {
        const { params } = await request.json();
        expect.step("theme_customize_data_get");
        expect(params.keys).toEqual(["test_template_1"]);
        await def.promise;
        return ["test_template_1"];
    });
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderButton id="'a'" action="'websiteConfig'" actionParam="{views: ['test_template_1']}">1</BuilderButton>
            <div t-if="this.isActiveItem('a')" class="test">a</div>
        `,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".o_hb_tab_content > .o_customize_tab").toHaveCount(0);

    def.resolve();
    await animationFrame();
    expect(".o_hb_tab_content > .o_customize_tab").toHaveCount(1);
    expect("[data-action-param*='test_template_1']").toHaveClass("active");
    expect(".test").toHaveCount(1);
    expect.verifySteps(["theme_customize_data_get"]);
});

test("use isActiveItem base on BuilderCheckbox with 'websiteConfig'", async () => {
    const def = Promise.withResolvers();
    onRpc("/website/theme_customize_data_get", async (request) => {
        const { params } = await request.json();
        expect.step("theme_customize_data_get");
        expect(params.keys).toEqual(["test_template_1"]);
        await def.promise;
        return ["test_template_1"];
    });
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderCheckbox id="'a'" action="'websiteConfig'" actionParam="{views: ['test_template_1']}"/>
            <div t-if="this.isActiveItem('a')" class="test">a</div>
        `,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".o_hb_tab_content > .o_customize_tab").toHaveCount(0);

    def.resolve();
    await animationFrame();
    expect(".o_hb_tab_content > .o_customize_tab").toHaveCount(1);
    expect("[data-action-param*='test_template_1'] .form-check-input:checked").toHaveCount(1);
    expect(".test").toHaveCount(1);
    expect.verifySteps(["theme_customize_data_get"]);
});

test("click on BuilderCheckbox with action “websiteConfig”", async () => {
    onRpc("/website/theme_customize_data_get", async (request) => {
        const { params } = await request.json();
        expect.step("theme_customize_data_get");
        expect(params.keys).toEqual(["test_template_1", "test_template_2"]);
        return ["test_template_2"];
    });
    onRpc("/website/theme_customize_data", async (request) => {
        const { params } = await request.json();
        expect.step("theme_customize_data");
        expect(params.enable).toEqual(["test_template_1"]);
        expect(params.disable).toEqual(["test_template_2"]);
    });

    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderCheckbox action="'websiteConfig'" actionParam="{views: ['!test_template_1', 'test_template_2']}"/>
        `,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect.verifySteps(["theme_customize_data_get"]);

    await contains("input[type='checkbox']:checked").click();
    expect.verifySteps(["theme_customize_data"]);
});

test("use isActiveItem base on BuilderSelectItem with websiteConfig", async () => {
    onRpc("/website/theme_customize_data_get", async (request) => {
        const { params } = await request.json();
        expect.step("theme_customize_data_get");
        expect(params.keys).toEqual(["test_template_1"]);
        return [];
    });

    onRpc("/website/theme_customize_data", async (request) => {
        const { params } = await request.json();
        expect.step("theme_customize_data");
        expect(params.enable).toEqual(["test_template_1"]);
        expect(params.disable).toEqual([]);
    });

    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderRow label.translate="Test">
                <BuilderSelect action="'websiteConfig'">
                    <BuilderSelectItem actionParam="{views: ['test_template_1']}">a</BuilderSelectItem>
                    <BuilderSelectItem id="'test'" actionParam="{views: []}">b</BuilderSelectItem>
                </BuilderSelect>
                <div class="my-test" t-if="this.isActiveItem('test')">test</div>
            </BuilderRow>
        `,
    });

    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    await animationFrame();
    expect(".o_hb_tab_content > .o_customize_tab").toHaveCount(1);
    expect(".my-test").toHaveCount(1);
    expect("[data-label='Test'] .dropdown-toggle").toHaveText("b");
    expect(".o-dropdown-item:visible").toHaveCount(0);

    await contains("[data-label='Test'] .dropdown-toggle").click();
    expect(".o-dropdown-item:visible").toHaveCount(2);

    await contains("[data-action-param*='test_template_1']").click();
    expect.verifySteps(["theme_customize_data_get", "theme_customize_data"]);
});

test("isApplied with action “websiteConfig” depends on views, assets and vars", async () => {
    onRpc("/website/theme_customize_data_get", async (request) => {
        const { params } = await request.json();
        if (params.is_view_data) {
            expect.step("theme_customize_data_get view");
            expect(params.keys).toEqual(["test_template_1", "test_template_2"]);
        } else {
            expect.step("theme_customize_data_get asset");
            expect(params.keys).toEqual(["test_asset_1", "test_asset_2"]);
        }
        return params.is_view_data ? ["test_template_1"] : ["test_asset_1"];
    });
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderCheckbox action="'websiteConfig'"
                actionParam="{
                    views: ['test_template_1'], assets: ['test_asset_1'], vars: { foo: 'bar', cat: 'cat' }
                }"/>
            <BuilderCheckbox action="'websiteConfig'"
                actionParam="{
                    views: ['test_template_1'], assets: ['test_asset_1'], vars: { bar: 'foo' }
                }"/>
            <BuilderCheckbox action="'websiteConfig'"
                actionParam="{
                    views: ['test_template_2'], assets: ['test_asset_1'], vars: { foo: 'bar' }
                }"/>
            <BuilderCheckbox action="'websiteConfig'"
                actionParam="{
                    views: ['test_template_1'], assets: ['test_asset_2'], vars: { foo: 'bar' }
                }"/>
        `,
    });
    const { getEditableContent } = await setupWebsiteBuilder(
        `<div class="test-options-target">b</div>`
    );
    // fake initial values
    const iframeDocument = getEditableContent().ownerDocument.documentElement;
    iframeDocument.style.setProperty("--foo", "bar");
    iframeDocument.style.setProperty("--cat", "cat");
    await contains(":iframe .test-options-target").click();
    await animationFrame();
    expect.verifySteps(["theme_customize_data_get view", "theme_customize_data_get asset"]);
    expect(".o_hb_options_container input[type='checkbox']:eq(0)").toBeChecked();
    expect(".o_hb_options_container input[type='checkbox']:eq(1)").not.toBeChecked();
    expect(".o_hb_options_container input[type='checkbox']:eq(2)").not.toBeChecked();
    expect(".o_hb_options_container input[type='checkbox']:eq(3)").not.toBeChecked();
});

test("BuilderButton with action “previewableWebsiteConfig”", async () => {
    onRpc("/website/theme_customize_data", async (request) => {
        const { params } = await request.json();
        expect.step("theme_customize_data");
        expect(params.enable).toEqual(["test_template_2"]);
        expect(params.disable).toEqual(["test_template_1", "test_template_negation"]);
    });
    onRpc("ir.ui.view", "save", () => {
        expect.step("websiteSave");
        return true;
    });
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderButtonGroup action="'previewableWebsiteConfig'">
                <BuilderButton actionParam="{views: ['test_template_1'], previewClass: 'test_class_1'}">1</BuilderButton>
                <BuilderButton actionParam="{views: ['test_template_2', '!test_template_negation'], previewClass: 'test_class_2'}">2</BuilderButton>
                <BuilderButton actionParam="{views: [], previewClass: ''}">3</BuilderButton>
            </BuilderButtonGroup>
        `,
    });

    await setupWebsiteBuilder(`<div class="test-options-target test_class_1">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect("[data-action-param*='test_template_1']").toHaveClass("active");

    await contains("[data-action-param*='[]']").hover();
    expect(":iframe .test-options-target").not.toHaveClass("test_class_1");
    expect(":iframe .test-options-target").not.toHaveClass("test_class_2");

    await contains("[data-action-param*='[]']").click();
    expect("[data-action-param*='[]']").toHaveClass("active");
    expect(":iframe .test-options-target").not.toHaveClass("test_class_1");
    expect(":iframe .test-options-target").not.toHaveClass("test_class_2");

    await contains("[data-action-param*='test_template_1']").hover();
    expect(":iframe .test-options-target").toHaveClass("test_class_1");
    expect(":iframe .test-options-target").not.toHaveClass("test_class_2");

    await contains("[data-action-param*='test_template_1']").click();
    expect("[data-action-param*='test_template_1']").toHaveClass("active");
    expect(":iframe .test-options-target").toHaveClass("test_class_1");
    expect(":iframe .test-options-target").not.toHaveClass("test_class_2");

    await contains("[data-action-param*='test_template_2']").hover();
    expect(":iframe .test-options-target").not.toHaveClass("test_class_1");
    expect(":iframe .test-options-target").toHaveClass("test_class_2");

    await contains("[data-action-param*='test_template_2']").click();
    expect("[data-action-param*='test_template_2']").toHaveClass("active");
    expect(":iframe .test-options-target").not.toHaveClass("test_class_1");
    expect(":iframe .test-options-target").toHaveClass("test_class_2");

    await contains(".o_hb_snippets_top_actions [data-action='save']").click();
    expect.verifySteps(["websiteSave", "theme_customize_data"]);
});

test("Undo and redo “previewableWebsiteConfig” action", async () => {
    onRpc("/website/theme_customize_data", async (request) => {
        const { params } = await request.json();
        expect.step("theme_customize_data");
        expect(params.enable).toEqual(["test_template_1"]);
        expect(params.disable).toEqual([]);
    });
    onRpc("ir.ui.view", "save", () => {
        expect.step("websiteSave");
        return true;
    });
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderButtonGroup action="'previewableWebsiteConfig'">
                <BuilderButton actionParam="{views: ['test_template_1'], previewClass: 'test_class_1'}">1</BuilderButton>
                <BuilderButton actionParam="{views: ['test_template_2'], previewClass: 'test_class_2'}">2</BuilderButton>
                <BuilderButton actionParam="{views: [], previewClass: ''}">3</BuilderButton>
            </BuilderButtonGroup>
        `,
    });
    const { getEditor } = await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    const editor = getEditor();

    await contains(":iframe .test-options-target").click();
    await contains("[data-action-param*='test_template_1']").click();
    expect("[data-action-param*='test_template_1']").toHaveClass("active");
    expect(":iframe .test-options-target").toHaveClass("test_class_1");
    expect(":iframe .test-options-target").not.toHaveClass("test_class_2");

    await contains("[data-action-param*='test_template_2']").click();
    expect("[data-action-param*='test_template_2']").toHaveClass("active");
    expect(":iframe .test-options-target").not.toHaveClass("test_class_1");
    expect(":iframe .test-options-target").toHaveClass("test_class_2");

    undo(editor);
    await animationFrame();
    expect("[data-action-param*='test_template_1']").toHaveClass("active");
    expect(":iframe .test-options-target").toHaveClass("test_class_1");
    expect(":iframe .test-options-target").not.toHaveClass("test_class_2");

    redo(editor);
    await animationFrame();
    expect("[data-action-param*='test_template_2']").toHaveClass("active");
    expect(":iframe .test-options-target").not.toHaveClass("test_class_1");
    expect(":iframe .test-options-target").toHaveClass("test_class_2");

    undo(editor);
    await animationFrame();
    expect("[data-action-param*='test_template_1']").toHaveClass("active");
    expect(":iframe .test-options-target").toHaveClass("test_class_1");
    expect(":iframe .test-options-target").not.toHaveClass("test_class_2");

    await contains(".o_hb_snippets_top_actions [data-action='save']").click();
    expect.verifySteps(["websiteSave", "theme_customize_data"]);
});

test("No rpc call if “previewableWebsiteConfig” action is undone", async () => {
    onRpc("/website/theme_customize_data", async () => {
        expect.step("theme_customize_data");
    });
    onRpc("ir.ui.view", "save", () => {
        expect.step("websiteSave");
        return true;
    });
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderButtonGroup action="'previewableWebsiteConfig'">
                <BuilderButton actionParam="{views: [], previewClass: ''}">1</BuilderButton>
                <BuilderButton actionParam="{views: ['test_template'], previewClass: 'test_class'}">2</BuilderButton>
            </BuilderButtonGroup>
        `,
    });
    const { getEditor } = await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    const editor = getEditor();

    await contains(":iframe .test-options-target").click();
    await contains("[data-action-param*='test_template']").click();
    undo(editor);
    await contains(".o_hb_snippets_top_actions [data-action='save']").click();
    expect.verifySteps([]); // No call to `theme_customize_data` nor to `save`
});

test("theme background image is properly set", async () => {
    const base64Image =
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYIIA" +
        "A".repeat(1000);

    patch(ToggleBodyBgImageAction.prototype, {
        async apply(params) {
            const { type: currentType, image: currentImage } = this.getCurrentConfig();
            const oldConfig = { type: currentType, image: currentImage };
            const newConfig = { type: "image", image: base64Image };
            await this.applyConfig(oldConfig, newConfig);
        },
    });

    class WebsiteAssets extends models.Model {
        _name = "website.assets";
        make_scss_customization(location, changes) {
            expect(
                changes["body-image"].includes(base64Image) &&
                    changes["body-image-type"].includes("image")
            ).toBe(true);
            expect.step("scss_customization");
        }
    }
    defineModels([WebsiteAssets]);

    onRpc("/website/theme_customize_bundle_reload", async (request) => {
        expect.step("bundle_reload");
        return { success: true };
    });

    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`, {
        loadIframeBundles: true,
    });

    await contains("[data-name='theme']").click();
    await animationFrame();
    expect(".o_theme_tab button[data-action-id='toggleBodyBgImage']").toHaveCount(1);
    await contains(".o_theme_tab button[data-action-id='toggleBodyBgImage']").click();
    await animationFrame();
    await expect.verifySteps(["scss_customization", "bundle_reload"]);
});

test("undo/redo website theme variables", async () => {
    const variable = "test-size";
    class WebsiteAssets extends models.Model {
        _name = "website.assets";
        make_scss_customization(location, changes) {
            const value = changes[variable];
            // Simulate the CSS variable change.
            queryOne(":iframe").documentElement.style.setProperty(`--${variable}`, value);
            expect.step(value);
        }
    }
    defineModels([WebsiteAssets]);

    onRpc("/website/theme_customize_bundle_reload", () => {
        expect.step("bundle_reload");
        return { success: true };
    });
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderButton action="'customizeWebsiteVariable'"
                           actionParam="'${variable}'" actionValue="'20px'"
                           preview="false">Medium</BuilderButton>
        `,
    });

    const initialSize = "10px";
    const { getEditor } = await setupWebsiteBuilder(
        `<section class="test-options-target">Text</section>`,
        {
            styleContent: `
                :root { --${variable}: ${initialSize}; }
                .test-options-target { font-size: var(--${variable}); }`,
        }
    );
    const editor = getEditor();

    // Select the target.
    const target = queryOne(`:iframe .test-options-target`);
    await contains(target).click();
    expect(target).toHaveStyle({ fontSize: initialSize });

    // Change font size to 20px.
    const changedSize = "20px";
    await contains(`[data-action-value="${changedSize}"]`).click();
    await expect.waitForSteps([changedSize, "bundle_reload"]);
    await animationFrame(); // Wait for action completion so there is a commit to undo.
    expect(target).toHaveStyle({ fontSize: changedSize });

    // Undo -> back to 10px.
    undo(editor);
    await expect.waitForSteps([initialSize, "bundle_reload"]);
    expect(target).toHaveStyle({ fontSize: initialSize });

    // Redo -> back to 20px.
    redo(editor);
    await expect.waitForSteps([changedSize, "bundle_reload"]);
    expect(target).toHaveStyle({ fontSize: changedSize });
});

test("undo/redo body background image removal", async () => {
    const variable = "body-image";
    const typeVariable = "body-image-type";
    class WebsiteAssets extends models.Model {
        _name = "website.assets";
        make_scss_customization(location, changes) {
            // Simulate the CSS variable change.
            const style = queryOne(":iframe").documentElement.style;
            for (const [key, value] of Object.entries(changes)) {
                // The server treats "null" as an SCSS reset. Model the
                // resulting empty CSS string explicitly.
                style.setProperty(`--${key}`, value === "null" ? "''" : value);
            }
            expect(changes[typeVariable]).toBe("'image'");
            expect.step(changes[variable]);
        }
    }
    defineModels([WebsiteAssets]);

    onRpc("/website/theme_customize_bundle_reload", () => {
        expect.step("bundle_reload");
        return { success: true };
    });
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderButton action="'removeBodyBgImage'" preview="false">Remove image</BuilderButton>`,
    });
    const { getEditor } = await setupWebsiteBuilder(
        `<section class="test-options-target">Text</section>`,
        {
            styleContent: `
                :root {
                    --${variable}: "${dummyBase64Img}";
                    --${typeVariable}: "image";
                }`,
        }
    );
    const editor = getEditor();
    const getImage = () => editor.shared.customizeWebsite.getWebsiteVariableValue(variable);

    // Select the target.
    await contains(":iframe .test-options-target").click();

    // We start with a body background image.
    expect(getImage()).toBe(dummyBase64Img);

    // Remove the body background image.
    await contains("button[data-action-id='removeBodyBgImage']").click();
    await expect.waitForSteps(["null", "bundle_reload"]);
    await animationFrame(); // Wait for action completion so there is a commit to undo.
    expect(getImage()).toBe("");

    // Undo -> restore the body background image.
    undo(editor);
    await expect.waitForSteps([`'${dummyBase64Img}'`, "bundle_reload"]);
    expect(getImage()).toBe(dummyBase64Img);

    // Redo -> remove the body background image again.
    redo(editor);
    await expect.waitForSteps(["null", "bundle_reload"]);
    expect(getImage()).toBe("");
});

test("preview/undo/redo body background position", async () => {
    const variable = "body-image-background-position";
    class WebsiteAssets extends models.Model {
        _name = "website.assets";
        make_scss_customization(location, changes) {
            const value = changes[variable];
            // Simulate the CSS variable change.
            queryOne(":iframe").documentElement.style.setProperty(`--${variable}`, value);
            expect.step(value);
        }
    }
    defineModels([WebsiteAssets]);

    onRpc("/website/theme_customize_bundle_reload", () => {
        expect.step("bundle_reload");
        return { success: true };
    });
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderButton action="'bodyBgPositionOverlay'">Position image</BuilderButton>`,
    });
    const initialValue = "10% 20%";
    const { getEditor } = await setupWebsiteBuilder(
        `<section class="test-options-target"
                  style="background-image: url('/web/image/123/transparent.png'); width: 500px; height: 300px"
         >Text</section>`,
        {
            styleContent: `
                :root { --${variable}: ${initialValue}; }
                .test-options-target { background-position: var(--${variable}); }
            `,
        }
    );
    const editor = getEditor();
    patch(editor.shared.backgroundPositionOption, { getDelta: () => ({ x: 100, y: 100 }) });

    // Select the target.
    const target = queryOne(":iframe .test-options-target");
    await contains(target).click();
    // The theme stylesheet provides the initial position: (10%, 20%).
    expect(target.style.backgroundPosition).toBe("");
    expect(target).toHaveStyle({ backgroundPosition: initialValue });

    // Move body background image by (30%, 40%): (10%, 20%) -> (40%, 60%).
    const { startDrag, endDrag } = patchDragImage(
        ".o_we_overlay_dragger",
        { x: 100, y: 100 },
        { x: 130, y: 140 }
    );
    await contains("button[data-action-id='bodyBgPositionOverlay']").click();
    await endDrag(await startDrag());
    // Dragging adds an inline style preview.
    const changedValue = "40% 60%";
    expect(target.style.backgroundPosition).toBe(changedValue);
    expect(target).toHaveStyle({ backgroundPosition: changedValue });

    // Discard the change -> back to (10%, 20%).
    await contains(".o_we_image_position_overlay .o_btn_discard").click();
    // The inline style preview is removed when the change is discarded.
    expect(target.style.backgroundPosition).toBe("");
    expect(target).toHaveStyle({ backgroundPosition: initialValue });

    // Move body background image by (30%, 40%): (10%, 20%) -> (40%, 60%).
    await contains("button[data-action-id='bodyBgPositionOverlay']").click();
    await endDrag(await startDrag());
    // Dragging adds an inline style preview.
    expect(target.style.backgroundPosition).toBe(changedValue);
    expect(target).toHaveStyle({ backgroundPosition: changedValue });

    // Apply the change: (40%, 60%).
    await contains(".o_we_image_position_overlay .o_btn_apply").click();
    await expect.waitForSteps([changedValue, "bundle_reload"]);
    await animationFrame(); // Wait for action completion so there is a commit to undo.
    // The inline style preview is removed when the change is applied.
    expect(target.style.backgroundPosition).toBe("");
    expect(target).toHaveStyle({ backgroundPosition: changedValue });

    // Undo -> back to (10%, 20%).
    undo(editor);
    await expect.waitForSteps([initialValue, "bundle_reload"]);
    expect(target.style.backgroundPosition).toBe("");
    expect(target).toHaveStyle({ backgroundPosition: initialValue });

    // Redo -> restore the applied position: (40%, 60%).
    redo(editor);
    await expect.waitForSteps([changedValue, "bundle_reload"]);
    expect(target.style.backgroundPosition).toBe("");
    expect(target).toHaveStyle({ backgroundPosition: changedValue });
});

test("BuilderButton with action “templatePreviewableWebsiteConfig”", async () => {
    registerTemplate("test.template.1", `<div class="template1"></div>`);
    registerTemplate("test.template.2", `<div class="template2"></div>`);
    registerTemplate("test.template.3", `<div class="template3"></div>`);
    onRpc("/website/theme_customize_data", async (request) => {
        const { params } = await request.json();
        expect.step("theme_customize_data");
        expect(params.enable).toEqual(["test_template_2"]);
        expect(params.disable).toEqual(["test_template_1", "test_template_3"]);
    });
    onRpc("ir.ui.view", "save", () => {
        expect.step("websiteSave");
        return true;
    });
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderButtonGroup>
                <BuilderButton
                        action="'websiteConfig'"
                        actionParam="{views: []}"
                >Item1</BuilderButton>
                <BuilderButton
                        action="'templatePreviewableWebsiteConfig'"
                        actionParam="{
                            views: ['test_template_1'],
                            previewClass: 'preview_class_1',
                            templateId: 'test.template.1',
                            placeBefore: '.target1',
                        }"
                >Item2</BuilderButton>
                <BuilderButton
                        action="'templatePreviewableWebsiteConfig'"
                        actionParam="{
                            views: ['test_template_2'],
                            previewClass: 'preview_class_2',
                            templateId: 'test.template.2',
                            placeAfter: '.target1',
                            placeExcludeRootClosest: '#o_wsale_container.o_wsale_has_sidebar',
                        }"
                >Item3</BuilderButton>
                <BuilderButton
                        action="'templatePreviewableWebsiteConfig'"
                        actionParam="{
                            views: ['test_template_3'],
                            previewClass: 'preview_class_3',
                            templateId: 'test.template.3',
                            placeAfter: '.target2',
                            placeExcludeRootClosest: '.excluded-class',
                        }"
                >Item4</BuilderButton>
            </BuilderButtonGroup>
        `,
    });

    await setupWebsiteBuilder(
        `<div class="test-options-target excluded-class">
            <div class="target1">a</div>
            <div class="target2">b</div>
        </div>`
    );
    await contains(":iframe .test-options-target").click();
    await contains("[data-action-param*='test_template_1']").hover();
    expect(":iframe .test-options-target").toHaveClass("preview_class_1");
    expect(":iframe .test-options-target").not.toHaveClass("preview_class_2");
    expect(":iframe .test-options-target").not.toHaveClass("preview_class_3");
    expect(":iframe .template1 + .target1 + .target2").toHaveCount(1);
    expect(":iframe .template2").toHaveCount(0);
    expect(":iframe .template3").toHaveCount(0);

    await contains("[data-action-param*='test_template_2']").hover();
    expect(":iframe .test-options-target").toHaveClass("preview_class_2");
    expect(":iframe .test-options-target").not.toHaveClass("preview_class_1");
    expect(":iframe .test-options-target").not.toHaveClass("preview_class_3");
    expect(":iframe .target1 + .template2 + .target2").toHaveCount(1);
    expect(":iframe .template1").toHaveCount(0);
    expect(":iframe .template3").toHaveCount(0);

    await contains("[data-action-param*='test_template_3']").hover();
    expect(":iframe .test-options-target").toHaveClass("preview_class_3");
    expect(":iframe .test-options-target").not.toHaveClass("preview_class_1");
    expect(":iframe .test-options-target").not.toHaveClass("preview_class_2");
    expect(":iframe .template1").toHaveCount(0);
    expect(":iframe .template2").toHaveCount(0);
    expect(":iframe .template3").toHaveCount(0);

    await contains(":iframe .test-options-target").hover();
    expect(":iframe .test-options-target").not.toHaveClass("preview_class_1");
    expect(":iframe .test-options-target").not.toHaveClass("preview_class_2");
    expect(":iframe .test-options-target").not.toHaveClass("preview_class_3");

    await contains("[data-action-param*='test_template_2']").click();
    expect.verifySteps(["theme_customize_data"]);
});
