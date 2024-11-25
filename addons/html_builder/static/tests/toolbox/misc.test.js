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
    expect(".element-toolbox").toBeDisplayed();
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
    expect(".element-toolbox").toHaveCount(2);
    expect(queryAllTexts(".element-toolbox:first .we-bg-toolbox > div > div")).toEqual([
        "Row 3",
        "C",
    ]);
    expect(queryAllTexts(".element-toolbox:nth-child(2) .we-bg-toolbox > div > div")).toEqual([
        "Row 1",
        "A",
        "Row 2",
        "B",
    ]);
});
