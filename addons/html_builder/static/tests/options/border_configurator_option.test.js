import { expect, test } from "@odoo/hoot";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { xml } from "@odoo/owl";

defineWebsiteModels();

test("empty border input is treated as 0", async () => {
    patchWithCleanup(BorderConfigurator.prototype, {
        hasBorder(editingElement) {
            const styleActionValue = this.env.editor.shared.builderActions
                .getAction("styleAction")
                .getValue({
                    editingElement,
                    param: {
                        mainParam: this.getStyleActionParam("width"),
                    },
                });
            expect(styleActionValue).toBe("0px");
            const hasBorder = super.hasBorder(editingElement);
            expect.step("hasBorder");
            expect(hasBorder).toBe(false);
            return hasBorder;
        },
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<BorderConfigurator label="'Border'"/>`,
    });
    await setupWebsiteBuilder(`<section class="test-options-target">Bordered block</section>`);
    await contains(":iframe section").click();
    expect.verifySteps(["hasBorder"]);
    await contains(".options-container [data-label=Border] input").edit(" "); // .clear() doesn't trigger a rerender.
    expect.verifySteps(["hasBorder"]);
});
test("hasBorder is true when multiple-value border starts by 0", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BorderConfigurator label="'Border'"/>`,
    });
    await setupWebsiteBuilder(`<section class="test-options-target">Bordered block</section>`, {
        loadIframeBundles: true,
    });
    await contains(":iframe section").click();
    expect(".options-container [data-label=Border] input").toHaveValue("0");
    expect(".options-container [data-label=Border] .o_we_color_preview").not.toBeVisible();
    await contains(".options-container [data-label=Border] input").edit("0 3 4 4", {
        confirm: "enter",
    });
    expect(".options-container [data-label=Border] .o_we_color_preview").toBeVisible();
    expect(":iframe section").toHaveStyle({
        "border-top-width": "0px",
        "border-right-width": "3px",
        "border-bottom-width": "4px",
        "border-left-width": "4px",
    });
});
