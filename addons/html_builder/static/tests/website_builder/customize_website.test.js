import { expect, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";
import { animationFrame, Deferred } from "@odoo/hoot-dom";

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
    onRpc("ir.ui.view", "save", async () => {
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
    onRpc("ir.ui.view", "save", async () => {
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
