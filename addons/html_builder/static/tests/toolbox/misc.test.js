import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { addToolbox, defineWebsiteModels, setupWebsiteBuilder } from "../helpers";

defineWebsiteModels();

test("Open toolbox", async () => {
    addToolbox({
        selector: ".test-toolbox-target",
        template: xml`
        <ToolboxRow label="'Row 1'">
            Test
        </ToolboxRow>`,
    });
    await setupWebsiteBuilder(`<div class="test-toolbox-target">b</div>`);
    await contains(":iframe .test-toolbox-target").click();
    expect(".element-toolbox").toBeDisplayed();
});

test("basic multi toolboxes", async () => {
    addToolbox({
        selector: ".test-toolbox-target",
        template: xml`
        <ToolboxRow label="'Row 1'">A</ToolboxRow>`,
    });
    addToolbox({
        selector: "p",
        template: xml`
        <ToolboxRow label="'Row 2'">B</ToolboxRow>`,
    });
    addToolbox({
        selector: "div",
        template: xml`
        <ToolboxRow label="'Row 3'">C</ToolboxRow>`,
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
