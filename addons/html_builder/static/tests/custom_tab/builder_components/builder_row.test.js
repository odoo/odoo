import { expect, test } from "@odoo/hoot";
import { hover, queryAllTexts, waitFor } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "../../helpers";

defineWebsiteModels();

test("show row title", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderRow label="'my label'">row text</BuilderRow>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    expect(".hb-row .text-nowrap").toHaveText("my label");
});
test("show row tooltip", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderRow label="'my label'" tooltip="'my tooltip'">row text</BuilderRow>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    expect(".hb-row .text-nowrap").toHaveText("my label");
    expect(".o-tooltip").not.toBeDisplayed();
    await hover(".hb-row .text-nowrap");
    await waitFor(".o-tooltip", { timeout: 1000 });
    expect(".o-tooltip").toHaveText("my tooltip");
    await contains(":iframe .test-options-target").hover();
    expect(".o-tooltip").not.toBeDisplayed();
});
test("hide empty row and display row with content", async () => {
    addOption({
        selector: ".parent-target",
        template: xml`<BuilderRow label="'Row 1'">
                <BuilderButton applyTo="'.child-target'" classAction="'my-custom-class'"/>
            </BuilderRow>`,
    });
    addOption({
        selector: ".parent-target",
        template: xml`<BuilderRow label="'Row 2'">
                <BuilderButton applyTo="':not(.my-custom-class)'" classAction="'test'"/>
            </BuilderRow>`,
    });
    addOption({
        selector: ".parent-target",
        template: xml`<BuilderRow label="'Row 3'">
                <BuilderButton applyTo="'.my-custom-class'" classAction="'test'"/>
            </BuilderRow>`,
    });
    await setupWebsiteBuilder(`<div class="parent-target"><div class="child-target">b</div></div>`);
    const selectorRowLabel = ".options-container .hb-row:not(.d-none) > div:nth-child(1)";
    await contains(":iframe .parent-target").click();
    expect(queryAllTexts(selectorRowLabel)).toEqual(["Row 1", "Row 2"]);

    await contains("[data-class-action='my-custom-class']").click();
    expect(queryAllTexts(selectorRowLabel)).toEqual(["Row 1", "Row 3"]);
});
test("extra classes on BuilderRow", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`<BuilderRow label="'my label'" extraClassName="'extra-class'">row text</BuilderRow>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    expect(".hb-row").toHaveClass("extra-class");
});
