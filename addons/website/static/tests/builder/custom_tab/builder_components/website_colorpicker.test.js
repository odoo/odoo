import { expect, test } from "@odoo/hoot";
import { animationFrame, click } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import {
    addOption,
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

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
