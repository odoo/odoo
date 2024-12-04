import { expect, test } from "@odoo/hoot";
import { queryAllTexts } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "../helpers";
import { defaultOptionComponents } from "../../src/builder/components/defaultComponents";

defineWebsiteModels();

test("Open custom tab with template option", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`
        <WeRow label="'Row 1'">
            Test
        </WeRow>`,
    });
    await setupWebsiteBuilder(`<div class="test-options-target" data-name="Yop">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    expect(queryAllTexts(".options-container > div")).toEqual(["Yop", "Row 1\nTest"]);
});

test("Open custom tab with Component option", async () => {
    class TestOption extends Component {
        static template = xml`
            <WeRow label="'Row 1'">
                Test
            </WeRow>`;
        static components = { ...defaultOptionComponents };
        static props = {};
    }
    addOption({
        selector: ".test-options-target",
        Component: TestOption,
    });
    await setupWebsiteBuilder(`<div class="test-options-target" data-name="Yop">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    expect(queryAllTexts(".options-container > div")).toEqual(["Yop", "Row 1\nTest"]);
});

test("basic multi options containers", async () => {
    addOption({
        selector: ".test-options-target",
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
    await setupWebsiteBuilder(`<div><p class="test-options-target">b</p></div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toHaveCount(2);
    expect(queryAllTexts(".options-container:first .we-bg-options-container > div > div")).toEqual([
        "Row 3",
        "C",
    ]);
    expect(
        queryAllTexts(".options-container:nth-child(2) .we-bg-options-container > div > div")
    ).toEqual(["Row 1", "A", "Row 2", "B"]);
});
