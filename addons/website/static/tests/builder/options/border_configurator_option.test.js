import { addBuilderAction, addBuilderOption } from "@html_builder/../tests/helpers";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { advanceTime, expect, test } from "@odoo/hoot";
import { waitFor, waitForNone, click, queryOne } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("empty border input is treated as 0", async () => {
    let expectBorder = false;
    patch(BorderConfigurator.prototype, {
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
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BorderConfigurator label="'Border'"/>`,
    });
    await setupWebsiteBuilder(`<section class="test-options-target">Bordered block</section>`, {
        loadIframeBundles: true,
    });
    const borderOptionInputSelector = ".o_hb_options_container [data-label=Border] input";

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
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BorderConfigurator label="'Border'"/>`,
    });
    await setupWebsiteBuilder(`<section class="test-options-target">Bordered block</section>`, {
        loadIframeBundles: true,
    });
    await contains(":iframe section").click();
    await waitFor(".o_hb_options_container [data-label=Border]");
    expect(".o_hb_options_container [data-label=Border] input").toHaveValue("0");
    expect(".o_hb_options_container [data-label=Border] .o_we_color_preview").not.toHaveCount();
    await contains(".o_hb_options_container [data-label=Border] input").edit("0 3 4 4", {
        confirm: "enter",
    });
    expect(".o_hb_options_container [data-label=Border] .o_we_color_preview").toBeVisible();
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
    await waitFor(".o_hb_bg_options_container");

    // set color to white
    await click(queryOne("[data-label='Border'] .o_we_color_preview"));
    await waitFor(".o_popover");
    await click(queryOne("[data-color='#FFFFFF']"));
    await waitForNone(".o_popover");

    // set style to dotted
    await click(queryOne("[data-label='Border'] .o_hb_select_toggle"));
    await waitFor("[data-label='Border'] .o_hb_select_toggle.show", { timeout: 500 });
    await click(queryOne(".o_popover [data-action-value='dotted']"));

    // edit width and check that color and style have been kept
    await contains("[data-label='Border'] input").edit("10");
    expect(":iframe .s_hr hr").toHaveStyle({
        "border-top": "10px dotted rgb(255, 255, 255)",
    });
});
test("Up and down arrows update the radius when withRadiusPresets=false", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BorderConfigurator label="'Border'" withRoundCorner="true" withRadiusPresets="false"/>`,
    });
    await setupWebsiteBuilder(`<section class="test-options-target">Bordered block</section>`);
    await contains(":iframe section").click();
    await waitFor(".o_hb_options_container [data-label='Round Corners']");
    expect(".o_hb_options_container [data-label='Round Corners'] input").toHaveValue("0");
    function expectRadiusValue(value) {
        expect(".o_hb_options_container [data-label='Round Corners'] input").toHaveValue(value);
        expect(":iframe section").toHaveStyle({
            "--box-border-top-left-radius": `${value}px`,
            "--box-border-top-right-radius": `${value}px`,
            "--box-border-bottom-left-radius": `${value}px`,
            "--box-border-bottom-right-radius": `${value}px`,
        });
    }
    await contains(".o_hb_options_container [data-label='Round Corners'] input").press("ArrowUp");
    await advanceTime(750);
    expectRadiusValue("1");
    await contains(".o_hb_options_container [data-label='Round Corners'] input").press("ArrowDown");
    await advanceTime(750);
    expectRadiusValue("0");
});
test("Up and down arrows update the radius with a custom action", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BorderConfigurator label="'Border'" action="'customStyleAction'" withRoundCorner="true"/>`,
    });
    addBuilderAction({
        CustomStyleAction: class extends BuilderAction {
            static id = "customStyleAction";
            getValue({ editingElement }) {
                return editingElement.dataset.value;
            }
            apply({ editingElement, value }) {
                editingElement.dataset.value = value;
            }
        },
    });
    await setupWebsiteBuilder(`<section class="test-options-target">Bordered block</section>`);
    await contains(":iframe section").click();
    await waitFor(".o_hb_options_container [data-label='Round Corners']");
    expect(".o_hb_options_container [data-label='Round Corners'] input").toHaveValue("0");
    function expectRadiusValue(value) {
        expect(".o_hb_options_container [data-label='Round Corners'] input").toHaveValue(value);
        expect(":iframe section").toHaveAttribute("data-value", `${value}px`);
    }
    await contains(".o_hb_options_container [data-label='Round Corners'] input").press("ArrowUp");
    await advanceTime(750);
    expectRadiusValue("1");
    await contains(".o_hb_options_container [data-label='Round Corners'] input").press("ArrowDown");
    await advanceTime(750);
    expectRadiusValue("0");
});
