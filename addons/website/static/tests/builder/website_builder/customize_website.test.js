import { expect, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";

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
    expect.verifySteps(["websiteSave", "theme_customize_data"]);
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
