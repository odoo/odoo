import { expect, test } from "@odoo/hoot";
import { animationFrame, queryAllTexts } from "@odoo/hoot-dom";
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
        selector: ".a",
        template: xml`
        <WeRow label="'Row 2'">B</WeRow>`,
    });
    addOption({
        selector: ".main",
        template: xml`
        <WeRow label="'Row 3'">C</WeRow>`,
    });
    await setupWebsiteBuilder(`<div class="main"><p class="test-options-target a">b</p></div>`);
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

test("option that matches several elements", async () => {
    addOption({
        selector: ".a",
        template: xml`<WeRow label="'Row'">
            <WeButton classAction="'my-custom-class'">Test</WeButton>
        </WeRow>`,
    });

    await setupWebsiteBuilder(`<div class="a"><div class="a test-target">b</div></div>`);
    await contains(":iframe .test-target").click();
    expect(".options-container:not(.d-none)").toHaveCount(2);
    expect(queryAllTexts(".options-container:not(.d-none)")).toEqual(["Row\nTest", "Row\nTest"]);
});

test("Snippets options respect sequencing", async () => {
    addOption({
        selector: ".test-options-target",
        template: xml`
        <WeRow label="'Row 2'">
            Test
        </WeRow>`,
        sequence: 2,
    });
    addOption({
        selector: ".test-options-target",
        template: xml`
        <WeRow label="'Row 1'">
            Test
        </WeRow>`,
        sequence: 1,
    });
    addOption({
        selector: ".test-options-target",
        template: xml`
        <WeRow label="'Row 3'">
            Test
        </WeRow>`,
        sequence: 3,
    });
    await setupWebsiteBuilder(`<div class="test-options-target" data-name="Yop">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".options-container").toBeDisplayed();
    expect(queryAllTexts(".options-container .we-bg-options-container > div > div")).toEqual([
        "Row 1",
        "Test",
        "Row 2",
        "Test",
        "Row 3",
        "Test",
    ]);
});

test("hide empty OptionContainer and display OptionContainer with content", async () => {
    addOption({
        selector: ".parent-target",
        template: xml`<WeRow label="'Row 1'">
            <WeButton applyTo="'.child-target'" classAction="'my-custom-class'"/>
        </WeRow>`,
    });
    addOption({
        selector: ".parent-target > div",
        template: xml`<WeRow label="'Row 3'">
            <WeButton applyTo="'.my-custom-class'" classAction="'test'"/>
        </WeRow>`,
    });
    await setupWebsiteBuilder(
        `<div class="parent-target"><div><div class="child-target">b</div></div></div>`
    );

    await contains(":iframe .parent-target > div").click();
    expect(".options-container:not(.d-none)").toHaveCount(1);

    await contains("[data-class-action='my-custom-class']").click();
    expect(".options-container:not(.d-none)").toHaveCount(2);
});

test("hide empty OptionContainer and display OptionContainer with content (with WeButtonGroup)", async () => {
    addOption({
        selector: ".parent-target",
        template: xml`<WeRow label="'Row 1'">
            <WeButton applyTo="'.child-target'" classAction="'my-custom-class'"/>
        </WeRow>`,
    });

    addOption({
        selector: ".parent-target > div",
        template: xml`
            <WeRow label="'Row 2'">
                <WeButtonGroup>
                    <WeButton applyTo="'.my-custom-class'" classAction="'test'">Test</WeButton>
                </WeButtonGroup>
            </WeRow>`,
    });

    await setupWebsiteBuilder(
        `<div class="parent-target"><div><div class="child-target">b</div></div></div>`
    );
    await contains(":iframe .parent-target > div").click();
    expect(".options-container:not(.d-none)").toHaveCount(1);

    await contains("[data-class-action='my-custom-class']").click();
    expect(".options-container:not(.d-none)").toHaveCount(2);
    expect(".options-container:not(.d-none):nth-child(2)").toHaveText("Row 2\nTest");
});

test("hide empty OptionContainer and display OptionContainer with content (with WeButtonGroup) - 2", async () => {
    addOption({
        selector: ".parent-target",
        template: xml`<WeRow label="'Row 1'">
            <WeButton applyTo="'.child-target'" classAction="'my-custom-class'"/>
        </WeRow>`,
    });

    addOption({
        selector: ".parent-target > div",
        template: xml`
            <WeRow label="'Row 2'">
                <WeButtonGroup applyTo="'.my-custom-class'">
                    <WeButton  classAction="'test'">Test</WeButton>
                </WeButtonGroup>
            </WeRow>`,
    });

    await setupWebsiteBuilder(
        `<div class="parent-target"><div><div class="child-target">b</div></div></div>`
    );
    await contains(":iframe .parent-target > div").click();
    expect(".options-container:not(.d-none)").toHaveCount(1);

    await contains("[data-class-action='my-custom-class']").click();
    expect(".options-container:not(.d-none)").toHaveCount(2);
    expect(".options-container:not(.d-none):nth-child(2)").toHaveText("Row 2\nTest");
});

test("display empty message if any option match the selected element", async () => {
    await setupWebsiteBuilder(`<div class="parent-target"><div class="child-target">b</div></div>`);
    await contains(":iframe .parent-target > div").click();
    await animationFrame();
    expect(".o_customize_tab").toHaveText("Select a block on your page to style it.");
});

test("display empty message if any option container is visible", async () => {
    addOption({
        selector: ".parent-target",
        template: xml`<WeRow label="'Row 1'">
            <WeButton applyTo="'.invalid'" classAction="'my-custom-class'"/>
        </WeRow>`,
    });

    await setupWebsiteBuilder(`<div class="parent-target"><div class="child-target">b</div></div>`);
    await contains(":iframe .parent-target > div").click();
    await animationFrame();
    expect(".o_customize_tab").toHaveText("Select a block on your page to style it.");
});
