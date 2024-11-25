import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "../helpers";

defineWebsiteModels();

test("Open toolbox", async () => {
    addOption({
        selector: ".test-toolbox-target",
        template: xml`
        <WeRow label="'Row 1'">
            Test
        </WeRow>`,
    });
    await setupWebsiteBuilder(`<div class="test-toolbox-target">b</div>`);
    await contains(":iframe .test-toolbox-target").click();
    expect(".options-container").toBeDisplayed();
});

test("basic multi toolboxes", async () => {
    addOption({
        selector: ".test-toolbox-target",
        template: xml`
        <WeRow label="'Row 1'">A</WeRow>`,
    });
    addOption({
        selector: "p",
        template: xml`
        <WeRow label="'Row 2'">B</WeRow>`,
    });
    addOption({
        selector: "div",
        template: xml`
        <WeRow label="'Row 3'">C</WeRow>`,
    });
    await setupWebsiteBuilder(`<div><p class="test-toolbox-target">b</p></div>`);
    await contains(":iframe .test-toolbox-target").click();
    expect(".options-container").toHaveCount(2);
    expect(queryAllTexts(".options-container:first .we-bg-options-container > div > div")).toEqual([
        "Row 3",
        "C",
    ]);
    expect(
        queryAllTexts(".options-container:nth-child(2) .we-bg-options-container > div > div")
    ).toEqual(["Row 1", "A", "Row 2", "B"]);
});
