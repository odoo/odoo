import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { expect, test } from "@odoo/hoot";
import { waitFor, waitForNone, click, queryOne } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    addOption,
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("empty border input is treated as 0", async () => {
    let expectBorder = false;
    patchWithCleanup(BorderConfigurator.prototype, {
        hasBorder(editingElement) {
            const styleActionValue = this.env.editor.shared.builderActions
                .getAction("styleAction")
                .getValue({
                    editingElement,
                    params: {
                        mainParam: this.getStyleActionParam("width"),
                    },
                });
            expect(styleActionValue).toBe(expectBorder ? expectBorder : "0px");
            const hasBorder = super.hasBorder(editingElement);
            expect.step("hasBorder");
            expect(hasBorder).toBe(!!expectBorder);
            return hasBorder;
        },
    });
    addOption({
        selector: ".test-options-target",
        template: xml`<BorderConfigurator label="'Border'"/>`,
    });
    await setupWebsiteBuilder(`<section class="test-options-target">Bordered block</section>`, {
        loadIframeBundles: true,
    });
    const borderOptionInputSelector = ".options-container [data-label=Border] input";

    expectBorder = false;
    await contains(":iframe section").click();
    expect.verifySteps(["hasBorder"]);

    expectBorder = "1px";
    await contains(borderOptionInputSelector).edit("1");
    expect.verifySteps(["hasBorder"]);

    expectBorder = false;
    await contains(borderOptionInputSelector).edit("    ");
    expect.verifySteps(["hasBorder"]);

    expectBorder = "2px";
    await contains(borderOptionInputSelector).edit("2");
    expect.verifySteps(["hasBorder"]);

    expectBorder = false;
    await contains(borderOptionInputSelector).clear();
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
    await waitFor(".options-container [data-label=Border]");
    expect(".options-container [data-label=Border] input").toHaveValue("0");
    expect(".options-container [data-label=Border] .o_we_color_preview").not.toHaveCount();
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
test("Elements with withBSClass = false don't reset their style when width is changed", async () => {
    await setupWebsiteBuilder(
        `
        <section>
            <div>
                <p>Text</p>
                <p>
                    <div class="s_hr pt32 pb32 o_colored_level o_draggable" data-snippet="s_hr" data-name="Separator">
                        <hr class="w-100 mx-auto">
                    </div>
                </p>
                <p>More Text</p>
            </div>
        </section>`,
        {
            openEditor: true,
        }
    );

    // click on separator
    await click(queryOne(":iframe .s_hr"));
    await waitFor(".we-bg-options-container");

    // set color to white
    await click(queryOne("[data-label='Border'] .o_we_color_preview"));
    await waitFor(".o_popover");
    await click(queryOne("[data-color='#FFFFFF']"));
    await waitForNone(".o_popover");

    // set style to dotted
    await click(queryOne("[data-label='Border'] .o-hb-select-toggle"));
    await waitFor("[data-label='Border'] .o-hb-select-toggle.show", { timeout: 500 });
    await click(queryOne(".o_popover [data-action-value='dotted']"));

    // edit width and check that color and style have been kept
    await contains("[data-label='Border'] input").edit("10");
    expect(":iframe .s_hr hr").toHaveStyle({
        "border-top": "10px dotted rgb(255, 255, 255)",
    });
});
