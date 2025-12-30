import { expect, test } from "@odoo/hoot";
import { animationFrame, click } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import {
    addOption,
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";
import { waitForEndOfOperation } from "@html_builder/../tests/helpers";

defineWebsiteModels();

test("should apply o_cc color", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderColorPicker styleAction="'background-color'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    await contains(".we-bg-options-container .o_we_color_preview").click();
    await click(".o-overlay-item [data-color='o_cc3']");
    await animationFrame();
    expect(":iframe .test-options-target").toHaveClass("test-options-target o_cc o_cc3");
});

test("should remove o_cc color on reset", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderColorPicker styleAction="'background-color'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target o_cc o_cc3">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    await contains(".we-bg-options-container .o_we_color_preview").click();
    await click(".o-overlay-item .fa-trash");
    await animationFrame();
    expect(":iframe .test-options-target").toHaveClass("test-options-target");
    expect(":iframe .test-options-target").not.toHaveClass("o_cc o_cc3");
});

test("should have the theme tab", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderColorPicker enabledTabs="['custom', 'theme']" styleAction="'background-color'"/>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    await contains(".we-bg-options-container .o_we_color_preview").click();
    expect("button.theme-tab").toHaveCount(1);
    await contains("button.theme-tab").click();
    await contains(".color-combination-button[data-color='o_cc1']").click();
    await contains(".we-bg-options-container .o_we_color_preview").click();
    await contains("button.theme-tab").click();
    expect(".color-combination-button[data-color='o_cc1']").toHaveClass("selected");
});

test("should work with color transition", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderColorPicker styleAction="'color'" enabledTabs="['custom']" />`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`, {
        // The CSS for the class "o_we_force_no_transition" is needed
        loadIframeBundles: true,
        styleContent:
            ".test-options-target { color: #FF0000; transition: color 0.15s ease-in-out; }",
        enableIframeTransitions: true,
    });

    await contains(":iframe .test-options-target").click();
    await contains(".we-bg-options-container .o_we_color_preview").click();
    await contains(".o_colorpicker_widget .o_hex_input").edit("#0000FF");
    await waitForEndOfOperation();
    expect(":iframe .test-options-target").toHaveStyle("color: rgb(0, 0, 255)");
    await contains(".we-bg-options-container .o_we_color_preview").click();
    await waitForEndOfOperation();
    expect(":iframe .test-options-target").toHaveStyle("color: rgb(0, 0, 255)");
});
