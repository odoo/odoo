import { expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import {
    contains,
    onRpc,
    models,
    defineModels,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import {
    addOption,
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { redo, undo } from "@html_editor/../tests/_helpers/user_actions";
import { CustomizeBodyBgTypeAction } from "@website/builder/plugins/customize_website_plugin";
import { renderToString } from "@web/core/utils/render";

defineWebsiteModels();

test("BuilderButton with action “websiteConfig” are correctly displayed", async () => {
    const def = new Deferred();
    onRpc("/website/theme_customize_data_get", async (request) => {
        const { params } = await request.json();
        expect.step("theme_customize_data_get");
        expect(params.keys).toEqual(["test_template_1", "test_template_2"]);
        await def;
        return ["test_template_2"];
    });
    addOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderButton action="'websiteConfig'" actionParam="{views: ['test_template_1']}">1</BuilderButton>
            <BuilderButton action="'websiteConfig'" actionParam="{views: ['test_template_2']}">2</BuilderButton>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".o-tab-content > .o_customize_tab").toHaveCount(0);

    def.resolve();
    await animationFrame();
    expect(".o-tab-content > .o_customize_tab").toHaveCount(1);
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

    addOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderButton action="'websiteConfig'" actionParam="{views: ['test_template_1']}">1</BuilderButton>
            <BuilderButton action="'websiteConfig'" actionParam="{views: ['test_template_2']}">2</BuilderButton>
            <BuilderButton classAction="'a'">a</BuilderButton>`,
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

    addOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderSelect action="'websiteConfig'">
                <BuilderSelectItem actionParam="{views: ['test_template_1']}">1</BuilderSelectItem>
                <BuilderSelectItem actionParam="{views: ['test_template_2']}">2</BuilderSelectItem>
            </BuilderSelect>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect.verifySteps(["theme_customize_data_get"]);

    await contains(".options-container .dropdown-toggle").click();
    await contains("[data-action-param*='test_template_1']").click();
    expect.verifySteps(["theme_customize_data"]);
});

test("use isActiveItem base on BuilderButton with 'websiteConfig'", async () => {
    const def = new Deferred();
    onRpc("/website/theme_customize_data_get", async (request) => {
        const { params } = await request.json();
        expect.step("theme_customize_data_get");
        expect(params.keys).toEqual(["test_template_1"]);
        await def;
        return ["test_template_1"];
    });
    addOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderButton id="'a'" action="'websiteConfig'" actionParam="{views: ['test_template_1']}">1</BuilderButton>
            <div t-if="isActiveItem('a')" class="test">a</div>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".o-tab-content > .o_customize_tab").toHaveCount(0);

    def.resolve();
    await animationFrame();
    expect(".o-tab-content > .o_customize_tab").toHaveCount(1);
    expect("[data-action-param*='test_template_1']").toHaveClass("active");
    expect(".test").toHaveCount(1);
    expect.verifySteps(["theme_customize_data_get"]);
});

test("use isActiveItem base on BuilderCheckbox with 'websiteConfig'", async () => {
    const def = new Deferred();
    onRpc("/website/theme_customize_data_get", async (request) => {
        const { params } = await request.json();
        expect.step("theme_customize_data_get");
        expect(params.keys).toEqual(["test_template_1"]);
        await def;
        return ["test_template_1"];
    });
    addOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderCheckbox id="'a'" action="'websiteConfig'" actionParam="{views: ['test_template_1']}"/>
            <div t-if="isActiveItem('a')" class="test">a</div>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".o-tab-content > .o_customize_tab").toHaveCount(0);

    def.resolve();
    await animationFrame();
    expect(".o-tab-content > .o_customize_tab").toHaveCount(1);
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

    addOption({
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

    addOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderRow label.translate="Test">
                <BuilderSelect action="'websiteConfig'">
                    <BuilderSelectItem actionParam="{views: ['test_template_1']}">a</BuilderSelectItem>
                    <BuilderSelectItem id="'test'" actionParam="{views: []}">b</BuilderSelectItem>
                </BuilderSelect>
                <div class="my-test" t-if="this.isActiveItem('test')">test</div>
            </BuilderRow>`,
    });

    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    await animationFrame();
    expect(".o-tab-content > .o_customize_tab").toHaveCount(1);
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
    addOption({
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
    expect(".options-container input[type='checkbox']:eq(0)").toBeChecked();
    expect(".options-container input[type='checkbox']:eq(1)").not.toBeChecked();
    expect(".options-container input[type='checkbox']:eq(2)").not.toBeChecked();
    expect(".options-container input[type='checkbox']:eq(3)").not.toBeChecked();
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
    addOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderButtonGroup action="'previewableWebsiteConfig'">
                <BuilderButton actionParam="{views: ['test_template_1'], previewClass: 'test_class_1'}">1</BuilderButton>
                <BuilderButton actionParam="{views: ['test_template_2', '!test_template_negation'], previewClass: 'test_class_2'}">2</BuilderButton>
                <BuilderButton actionParam="{views: [], previewClass: ''}">3</BuilderButton>
            </BuilderButtonGroup>`,
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

    await contains(".o-snippets-top-actions [data-action='save']").click();
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
    addOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderButtonGroup action="'previewableWebsiteConfig'">
                <BuilderButton actionParam="{views: ['test_template_1'], previewClass: 'test_class_1'}">1</BuilderButton>
                <BuilderButton actionParam="{views: ['test_template_2'], previewClass: 'test_class_2'}">2</BuilderButton>
                <BuilderButton actionParam="{views: [], previewClass: ''}">3</BuilderButton>
            </BuilderButtonGroup>`,
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

    await contains(".o-snippets-top-actions [data-action='save']").click();
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
    addOption({
        selector: ".test-options-target",
        template: xml`
            <BuilderButtonGroup action="'previewableWebsiteConfig'">
                <BuilderButton actionParam="{views: [], previewClass: ''}">1</BuilderButton>
                <BuilderButton actionParam="{views: ['test_template'], previewClass: 'test_class'}">2</BuilderButton>
            </BuilderButtonGroup>`,
    });
    const { getEditor } = await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    const editor = getEditor();

    await contains(":iframe .test-options-target").click();
    await contains("[data-action-param*='test_template']").click();
    undo(editor);
    await contains(".o-snippets-top-actions [data-action='save']").click();
    expect.verifySteps([]); // No call to `theme_customize_data` nor to `save`
});

test("theme background image is properly set", async () => {
    const base64Image =
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYIIA" +
        "A".repeat(1000);

    // Using historyImageSrc to avoid mocking the gallery dialog
    patchWithCleanup(CustomizeBodyBgTypeAction.prototype, {
        async load(editingElement) {
            editingElement.historyImageSrc = { src: base64Image };
            super.load(editingElement);
        },
        apply(params) {
            params.loadResult = {
                imageSrc: base64Image,
                oldImageSrc: "",
                oldValue: "'image'",
            };
            super.apply(params);
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
    expect(
        ".o_theme_tab button[data-action-id='customizeBodyBgType'][data-action-value='image']"
    ).toHaveCount(1);
    await contains(
        ".o_theme_tab button[data-action-id='customizeBodyBgType'][data-action-value='image']"
    ).click();
    await animationFrame();
    await expect.verifySteps(["scss_customization", "bundle_reload"]);
});

test("BuilderButton with action “templatePreviewableWebsiteConfig”", async () => {
    renderToString.app.addTemplate("test.template.1", `<div class="template1"></div>`);
    renderToString.app.addTemplate("test.template.2", `<div class="template2"></div>`);
    renderToString.app.addTemplate("test.template.3", `<div class="template3"></div>`);
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
    addOption({
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
