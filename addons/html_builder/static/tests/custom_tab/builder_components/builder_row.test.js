import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, hover, queryAllTexts, waitFor } from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";
import { addOption, defineWebsiteModels, setupWebsiteBuilder } from "../../website_helpers";

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

/* ================= Collapse template ================= */
const collapseOptionTemplate = (dependency = false, expand = false) => xml`
    <BuilderRow label="'Test Collapse'" expand="${expand}">
        <BuilderButton classAction="'a'" ${dependency ? "id=\"'test_opt'\"" : ""}>A</BuilderButton>
        <t t-set-slot="collapse">
            <BuilderRow level="1" label="'B'" ${
                dependency ? "t-if=\"isActiveItem('test_opt')\"" : ""
            }>
                <BuilderButton classAction="'b'">B</BuilderButton>
            </BuilderRow>
        </t>
    </BuilderRow>`;

describe("BuilderRow with collapse content", () => {
    test("expand=false is collapsed by default", async () => {
        addOption({
            selector: ".test-options-target",
            template: collapseOptionTemplate(),
        });
        await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        expect(".o_we_collapse_toggler").not.toHaveClass("active");
    });

    test("expand=true is expanded by default", async () => {
        addOption({
            selector: ".test-options-target",
            template: collapseOptionTemplate(false, true),
        });
        await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        await animationFrame();
        expect(".o_we_collapse_toggler").toHaveClass("active");
    });

    test("Toggler button is not visible if no dependency is active", async () => {
        addOption({
            selector: ".test-options-target",
            template: collapseOptionTemplate(true),
        });
        await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        expect(".o_we_collapse_toggler").toHaveCount(0);
    });

    test("expand=true works when a dependency becomes active", async () => {
        addOption({
            selector: ".test-options-target",
            template: collapseOptionTemplate(true, true),
        });
        await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        await contains(".options-container button[data-class-action='a']").click();
        await animationFrame();
        expect(".o_we_collapse_toggler").toHaveCount(1);
        expect(".o_we_collapse_toggler").toHaveClass("active");
        expect(".options-container button[data-class-action='b']").toBeVisible();
    });

    test("Collapse works with several dependencies", async () => {
        addOption({
            selector: ".test-options-target",
            template: xml`
            <BuilderRow label="'Test Collapse'" expand="true">
                <BuilderSelect>
                    <BuilderSelectItem classAction="'a'" id="'test_opt'">A</BuilderSelectItem>
                    <BuilderSelectItem classAction="'c'" id="'random_opt'">C</BuilderSelectItem>
                </BuilderSelect>
                <t t-set-slot="collapse">
                    <BuilderRow level="1" t-if="isActiveItem('test_opt')" label="'B'">
                        <BuilderButton classAction="'b'">B</BuilderButton>
                    </BuilderRow>
                    <BuilderRow level="1" t-if="isActiveItem('random_opt')" label="'D'">
                        <BuilderButton classAction="'d'">D</BuilderButton>
                    </BuilderRow>
                </t>
            </BuilderRow>`,
        });
        await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        expect(".o_we_collapse_toggler").toHaveCount(0);
        await contains(".options-container .dropdown-toggle").click();
        await contains(".dropdown-menu [data-class-action='a']").click();
        await animationFrame();
        expect(".o_we_collapse_toggler").toHaveCount(1);
        expect(".options-container button[data-class-action='b']").toBeVisible();
        expect(".options-container button[data-class-action='d']").not.toBeVisible();
        await contains(".options-container .dropdown-toggle").click();
        await contains(".dropdown-menu [data-class-action='c']").click();
        await animationFrame();
        expect(".o_we_collapse_toggler").toHaveCount(1);
        expect(".options-container button[data-class-action='b']").not.toBeVisible();
        expect(".options-container button[data-class-action='d']").toBeVisible();
    });

    test("Click on toggler collapses / expands the BuilderRow", async () => {
        addOption({
            selector: ".test-options-target",
            template: collapseOptionTemplate(),
        });
        await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        expect(".o_we_collapse_toggler").not.toHaveClass("active");
        expect(".options-container button[data-class-action='b']").not.toBeVisible();
        await contains(".o_we_collapse_toggler").click();
        expect(".o_we_collapse_toggler").toHaveClass("active");
        expect(".options-container button[data-class-action='b']").toBeVisible();
        await contains(".o_we_collapse_toggler").click();
        expect(".o_we_collapse_toggler").not.toHaveClass("active");
        expect(".options-container button[data-class-action='b']").not.toBeVisible();
    });

    test("Click header row's label collapses / expands the BuilderRow", async () => {
        addOption({
            selector: ".test-options-target",
            template: collapseOptionTemplate(),
        });
        await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        expect(".o_we_collapse_toggler").not.toHaveClass("active");
        expect(".options-container button[data-class-action='b']").not.toBeVisible();
        await contains("[data-label='Test Collapse'] span:contains('Test Collapse')").click();
        expect(".o_we_collapse_toggler").toHaveClass("active");
        expect(".options-container button[data-class-action='b']").toBeVisible();
        await contains("[data-label='Test Collapse'] span:contains('Test Collapse')").click();
        expect(".o_we_collapse_toggler").not.toHaveClass("active");
        expect(".options-container button[data-class-action='b']").not.toBeVisible();
    });

    test("Two BuilderRows with collapse content on the same option are toggled independently", async () => {
        addOption({
            selector: ".test-options-target",
            template: collapseOptionTemplate(true, true),
        });
        addOption({
            selector: ".test-options-target",
            template: collapseOptionTemplate(),
        });
        await setupWebsiteBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".options-container").toBeDisplayed();
        await animationFrame();
        expect(".o_we_collapse_toggler").toHaveCount(1);
        await contains(".options-container [data-class-action='a']:first").click();
        await animationFrame();
        expect(".o_we_collapse_toggler").toHaveCount(2);
        expect(".o_we_collapse_toggler:first").toHaveClass("active");
        expect(".o_we_collapse_toggler:last").not.toHaveClass("active");
        await contains(".options-container .o_we_collapse_toggler:last").click();
        expect(".o_we_collapse_toggler:first").toHaveClass("active");
        expect(".o_we_collapse_toggler:last").toHaveClass("active");
        await contains(".options-container .o_we_collapse_toggler:first").click();
        expect(".o_we_collapse_toggler:first").not.toHaveClass("active");
        expect(".o_we_collapse_toggler:last").toHaveClass("active");
    });
});
