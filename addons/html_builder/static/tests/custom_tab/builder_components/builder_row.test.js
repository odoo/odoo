import { addBuilderOption, setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { refreshSublevelRows } from "@html_builder/core/building_blocks/builder_row";
import { describe, expect, mockMatchMedia, test } from "@odoo/hoot";
import {
    advanceTime,
    animationFrame,
    hover,
    queryAll,
    queryAllTexts,
    queryOne,
    waitFor,
    waitUntil,
} from "@odoo/hoot-dom";
import { xml } from "@odoo/owl";
import { contains, defineStyle, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { OPEN_DELAY } from "@web/core/tooltip/tooltip_plugin";
import { config as transitionConfig } from "@web/core/transition";

function reapplyCollapseTransition() {
    defineStyle(/* css */ `
        hoot-fixture:not(.allow-transitions) * .o_hb_collapse_content {
            transition: height 0.35s ease !important;
        }
    `);
}

const ONE_ROW_HEIGHT = 32; // $o-hb-row-min-height (28px) + the row's 4px padding-top.

describe.current.tags("desktop");

test("show row title", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderRow label="'my label'">row text</BuilderRow>`,
    });
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".o_hb_options_container").toBeVisible();
    expect(".o_hb_row .text-nowrap").toHaveText("my label");
});
test("show row tooltip", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`<BuilderRow label="'my label'" tooltip="'my tooltip'">row text</BuilderRow>`,
    });
    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    expect(".o_hb_options_container").toBeVisible();
    expect(".o_hb_row .text-nowrap").toHaveText("my label");
    expect(".o-tooltip").not.toHaveCount();
    await hover(".o_hb_row .text-nowrap");
    await advanceTime(OPEN_DELAY);
    await waitFor(".o-tooltip");
    expect(".o-tooltip").toHaveText("my tooltip");
    await contains(":iframe .test-options-target").hover();
    expect(".o-tooltip").not.toHaveCount();
});
test("hide empty row and display row with content", async () => {
    addBuilderOption({
        selector: ".parent-target",
        template: xml`
            <BuilderRow label="'Row 1'">
                <BuilderButton applyTo="'.child-target'" classAction="'my-custom-class'"/>
            </BuilderRow>
        `,
    });
    addBuilderOption({
        selector: ".parent-target",
        template: xml`
            <BuilderRow label="'Row 2'">
                <BuilderButton applyTo="':not(.my-custom-class)'" classAction="'test'"/>
            </BuilderRow>
        `,
    });
    addBuilderOption({
        selector: ".parent-target",
        template: xml`
            <BuilderRow label="'Row 3'">
                <BuilderButton applyTo="'.my-custom-class'" classAction="'test'"/>
            </BuilderRow>
        `,
    });
    await setupHTMLBuilder(`<div class="parent-target"><div class="child-target">b</div></div>`);
    const selectorRowLabel = ".o_hb_options_container .o_hb_row:not(.d-none) .o_hb_row_label";
    await contains(":iframe .parent-target").click();
    expect(queryAllTexts(selectorRowLabel)).toEqual(["Row 1", "Row 2"]);

    await contains("[data-class-action='my-custom-class']").click();
    expect(queryAllTexts(selectorRowLabel)).toEqual(["Row 1", "Row 3"]);
});

test("reconnects lines across mixed levels", async () => {
    addBuilderOption({
        selector: ".test-options-target",
        template: xml`
            <div class="o_hb_options_container">
                <BuilderRow label="'root-1'">root-1</BuilderRow>
                <BuilderRow label="'level-1'" level="1">A</BuilderRow>
                <BuilderRow label="'level-2'" level="2">B</BuilderRow>
                <BuilderRow label="'level-1'" level="1">C</BuilderRow>
                <BuilderRow label="'root-2'">root-2</BuilderRow>
                <BuilderRow label="'level-1'" level="1">D</BuilderRow>
                <BuilderRow label="'level-2'" level="2">E</BuilderRow>
                <BuilderRow label="'level-2'" level="2">F</BuilderRow>
                <BuilderRow label="'level-3'" level="3">G</BuilderRow>
                <BuilderRow label="'level-3'" level="3">H</BuilderRow>
                <BuilderRow label="'level-2'" level="2">I</BuilderRow>
                <BuilderRow label="'level-1'" level="1">J</BuilderRow>
            </div>
        `,
    });

    await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
    await contains(":iframe .test-options-target").click();
    await waitFor(".o_hb_options_container .o_hb_row_label");
    await contains("[data-label='root-1'] .o_hb_collapse_toggler").click();
    await contains("[data-label='root-2'] .o_hb_collapse_toggler").click();

    const labelEls = queryAll(".o_hb_options_container .o_hb_row_label");
    const rowEls = queryAll(".o_hb_options_container .o_hb_row");
    const rects = [
        { top: 0, bottom: 40 },
        { top: 40, bottom: 80 },
        { top: 80, bottom: 120 },
        { top: 120, bottom: 160 },
        { top: 160, bottom: 200 },
        { top: 200, bottom: 240 },
        { top: 240, bottom: 280 },
        { top: 280, bottom: 320 },
        { top: 320, bottom: 360 },
        { top: 360, bottom: 400 },
        { top: 400, bottom: 440 },
        { top: 440, bottom: 480 },
    ];
    labelEls.forEach((labelEl, index) => {
        labelEl.getBoundingClientRect = () => rects[index];
    });
    refreshSublevelRows(rowEls[10]);
    await animationFrame();

    const offsets = labelEls.map((labelEl) =>
        labelEl.style.getPropertyValue("--o-hb-row-sublevel-top")
    );
    expect(offsets).toEqual(["", "", "", "-40px", "", "", "", "", "", "", "-80px", "-200px"]);
});

describe("BuilderRow sub-option groups", () => {
    test("groups span option components and preserve their levels and controls", async () => {
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`
                <BuilderRow label="'Media'">
                    <BuilderButton classAction="'media'">Media</BuilderButton>
                </BuilderRow>
            `,
        });
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`
                <BuilderRow label="'Transform'" level="1">
                    <BuilderButton classAction="'transform'">Transform</BuilderButton>
                </BuilderRow>
                <BuilderRow label="'Direction'" level="2">
                    <BuilderButton classAction="'direction'">Direction</BuilderButton>
                </BuilderRow>
                <BuilderRow label="'Shape'">
                    <BuilderButton classAction="'shape'">Shape</BuilderButton>
                </BuilderRow>
                <BuilderRow label="'Stretch'" level="1">
                    <BuilderButton classAction="'stretch'">Stretch</BuilderButton>
                </BuilderRow>
                <BuilderRow label="'Description'">
                    <BuilderTextInput attributeAction="'title'"/>
                </BuilderRow>
            `,
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        await animationFrame();

        const toggler = "[data-label='Media'] .o_hb_collapse_toggler";
        const transformEl = queryOne("[data-label='Transform']");
        const directionEl = queryOne("[data-label='Direction']");
        expect(".o_hb_row_group").toHaveCount(2);
        expect(toggler).toHaveAttribute("aria-expanded", "false");
        expect(toggler).toHaveAttribute("aria-controls", `${transformEl.id} ${directionEl.id}`);
        expect("[data-label='Shape']").toHaveClass("o_hb_row_group");
        expect("[data-label='Transform']").toHaveClass("o_hb_row_sublevel_1");
        expect("[data-label='Direction']").toHaveClass("o_hb_row_sublevel_2");
        expect("[data-label='Description'] .o_hb_collapse_toggler").toHaveCount(0);
        expect(transformEl).not.toBeVisible();
        expect(directionEl).not.toBeVisible();
        expect(transformEl.inert).toBe(true);
        expect("[data-label='Stretch']").not.toBeVisible();

        await contains("[data-class-action='media']").click();
        expect(":iframe .test-options-target").toHaveClass("media");
        expect(toggler).toHaveAttribute("aria-expanded", "false");
        await contains(toggler).click();
        expect(toggler).toHaveAttribute("aria-expanded", "true");
        await contains("[data-label='Shape'] .o_hb_collapse_toggler").click();
        await contains(toggler).click();
        expect(toggler).toHaveAttribute("aria-expanded", "false");
        expect(transformEl).not.toBeVisible();
        expect(directionEl).not.toBeVisible();
        expect(transformEl.inert).toBe(true);
        expect("[data-label='Stretch']").toBeVisible();
        expect("[data-label='Description']").toBeVisible();

        await contains("[data-label='Media'] .o_hb_row_label").click();
        expect(queryOne("[data-label='Transform']")).toBe(transformEl);
        expect(transformEl).toBeVisible();
        expect(directionEl).toBeVisible();
        expect(transformEl.inert).toBe(false);
        await contains("[data-class-action='transform']").click();
        expect(":iframe .test-options-target").toHaveClass("transform");
    });

    test("group toggles support keyboard activation", async () => {
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`
                <BuilderRow label="'Media'">Media</BuilderRow>
                <BuilderRow label="'Transform'" level="1">Transform</BuilderRow>
            `,
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        await animationFrame();

        const toggler = "[data-label='Media'] .o_hb_collapse_toggler";
        expect(toggler).toHaveAttribute("type", "button");
        expect(toggler).toHaveAttribute("aria-expanded", "false");
        await contains(toggler).press("Enter");
        expect(toggler).toBeFocused();
        expect(toggler).toHaveAttribute("aria-expanded", "true");
        expect("[data-label='Transform']").toBeVisible();
        await contains(toggler).press("Enter");
        expect(toggler).toBeFocused();
        expect(toggler).toHaveAttribute("aria-expanded", "false");
        expect("[data-label='Transform']").not.toBeVisible();
    });

    test("conditional sub-options expand the group when they appear again", async () => {
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`
                <BuilderRow label="'Media'">
                    <BuilderButton classAction="'enabled'" id="'enabled_opt'">Enable</BuilderButton>
                </BuilderRow>
                <BuilderRow label="'Transform'" level="1">
                    <BuilderButton t-if="this.isActiveItem('enabled_opt')" classAction="'transform'">
                        Transform
                    </BuilderButton>
                </BuilderRow>
            `,
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        await animationFrame();

        const toggler = "[data-label='Media'] .o_hb_collapse_toggler";
        expect(toggler).toHaveCount(0);
        await contains("[data-class-action='enabled']").click();
        await animationFrame();
        expect(toggler).toHaveAttribute("aria-expanded", "true");
        expect("[data-label='Transform']").toBeVisible();
        await contains(toggler).click();
        expect("[data-label='Transform']").not.toBeVisible();
        await contains("[data-class-action='enabled']").click();
        await animationFrame();
        expect(toggler).toHaveCount(0);
        await contains("[data-class-action='enabled']").click();
        await animationFrame();
        expect(toggler).toHaveAttribute("aria-expanded", "true");
        expect("[data-label='Transform']").toBeVisible();
    });

    test("new sub-options expand an existing collapsed group", async () => {
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`
                <BuilderRow label="'Media'">
                    <BuilderButton classAction="'enabled'" id="'enabled_opt'">Enable</BuilderButton>
                </BuilderRow>
                <BuilderRow label="'Transform'" level="1">Transform</BuilderRow>
                <BuilderRow label="'Filter'" level="1" t-if="this.isActiveItem('enabled_opt')">
                    Filter
                </BuilderRow>
            `,
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        await animationFrame();

        const toggler = "[data-label='Media'] .o_hb_collapse_toggler";
        expect(toggler).toHaveAttribute("aria-expanded", "false");
        expect("[data-label='Transform']").not.toBeVisible();
        expect("[data-label='Filter']").toHaveCount(0);
        await contains("[data-class-action='enabled']").click();
        await animationFrame();
        expect(toggler).toHaveAttribute("aria-expanded", "true");
        expect("[data-label='Transform']").toBeVisible();
        expect("[data-label='Filter']").toBeVisible();

        await contains(toggler).click();
        await contains("[data-class-action='enabled']").click();
        await animationFrame();
        expect(toggler).toHaveAttribute("aria-expanded", "false");
        expect("[data-label='Transform']").not.toBeVisible();
        expect("[data-label='Filter']").toHaveCount(0);
        await contains("[data-class-action='enabled']").click();
        await animationFrame();
        expect(toggler).toHaveAttribute("aria-expanded", "true");
        expect("[data-label='Filter']").toBeVisible();
    });

    test("option updates preserve the group's expanded or collapsed state", async () => {
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`
                <BuilderRow label="'Media'">
                    <BuilderButton classAction="'enabled'">Enable</BuilderButton>
                </BuilderRow>
                <BuilderRow label="'Transform'" level="1">
                    <BuilderButton classAction="'transform'">Transform</BuilderButton>
                </BuilderRow>
            `,
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        await animationFrame();

        const toggler = "[data-label='Media'] .o_hb_collapse_toggler";
        await contains(toggler).click();
        await contains("[data-class-action='enabled']").click();
        await animationFrame();
        expect(toggler).toHaveAttribute("aria-expanded", "true");
        expect("[data-label='Transform']").toBeVisible();
        await contains("[data-class-action='transform']").click();
        expect(toggler).toHaveAttribute("aria-expanded", "true");

        await contains(toggler).click();
        await contains("[data-class-action='enabled']").click();
        await animationFrame();
        expect(toggler).toHaveAttribute("aria-expanded", "false");
        expect("[data-label='Transform']").not.toBeVisible();
    });

    test("reopening an options container keeps its sub-option groups collapsed", async () => {
        addBuilderOption({
            selector: ".test-options-target",
            title: "Image",
            template: xml`
                <BuilderRow label="'Media'">Media</BuilderRow>
                <BuilderRow label="'Transform'" level="1">Transform</BuilderRow>
                <BuilderRow label="'Shape'">Shape</BuilderRow>
                <BuilderRow label="'Stretch'" level="1">Stretch</BuilderRow>
            `,
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        await animationFrame();

        const containerToggler =
            "[data-container-title='Image'] .o_hb_options_container_label_actionable";
        expect("[data-label='Media'] .o_hb_collapse_toggler").toHaveAttribute(
            "aria-expanded",
            "false"
        );
        expect("[data-label='Shape'] .o_hb_collapse_toggler").toHaveAttribute(
            "aria-expanded",
            "false"
        );
        await contains(containerToggler).click();
        expect(containerToggler).toHaveAttribute("aria-expanded", "false");
        await advanceTime(400);
        await animationFrame();
        expect("[data-container-title='Image'] .o_hb_row").toHaveCount(0);
        await contains(containerToggler).click();
        await animationFrame();
        expect(containerToggler).toHaveAttribute("aria-expanded", "true");
        expect("[data-label='Media'] .o_hb_collapse_toggler").toHaveAttribute(
            "aria-expanded",
            "false"
        );
        expect("[data-label='Shape'] .o_hb_collapse_toggler").toHaveAttribute(
            "aria-expanded",
            "false"
        );
        expect("[data-label='Transform']").not.toBeVisible();
        expect("[data-label='Stretch']").not.toBeVisible();
    });

    test("sub-option expansion animates its height and cancels when collapsed", async () => {
        patchWithCleanup(transitionConfig, { disabled: false });
        mockMatchMedia({ "prefers-reduced-motion": "no-preference" });
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`
                <BuilderRow label="'Media'">Media</BuilderRow>
                <BuilderRow label="'Transform'" level="1">Transform</BuilderRow>
            `,
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        await animationFrame();

        const toggler = "[data-label='Media'] .o_hb_collapse_toggler";
        const transformEl = queryOne("[data-label='Transform']");
        expect(transformEl.getAnimations()).toHaveLength(0);
        await contains(toggler).click();
        expect(transformEl.getAnimations()).toHaveLength(1);
        const animation = transformEl.getAnimations()[0];
        animation.pause();
        const expandedHeight = parseFloat(animation.effect.getKeyframes().at(-1).height);
        expect(expandedHeight).toBeGreaterThan(0);
        animation.currentTime = 0;
        expect(parseFloat(getComputedStyle(transformEl).height)).toBe(0);
        animation.currentTime = animation.effect.getTiming().duration / 2;
        expect(parseFloat(getComputedStyle(transformEl).height)).toBeGreaterThan(0);
        expect(parseFloat(getComputedStyle(transformEl).height)).toBeLessThan(expandedHeight);

        await contains(toggler).click();
        expect(animation.playState).toBe("idle");
        const closingAnimation = transformEl.getAnimations()[0];
        expect(closingAnimation.effect.getTiming().direction).toBe("reverse");
        expect(transformEl.inert).toBe(true);
        closingAnimation.finish();
        await animationFrame();
        expect(transformEl.getAnimations()).toHaveLength(0);
        expect(transformEl).not.toBeVisible();
        await contains(toggler).click();
        const nextAnimation = transformEl.getAnimations()[0];
        nextAnimation.finish();
        expect(transformEl).toBeVisible();
        expect(parseFloat(getComputedStyle(transformEl).height)).toBe(expandedHeight);
    });

    test("options container expansion measures only its visible rows", async () => {
        patchWithCleanup(transitionConfig, { disabled: false });
        mockMatchMedia({ "prefers-reduced-motion": "no-preference" });
        addBuilderOption({
            selector: ".test-options-target",
            title: "Image",
            template: xml`
                <BuilderRow label="'Media'">Media</BuilderRow>
                <BuilderRow label="'Transform'" level="1">Transform</BuilderRow>
                <BuilderRow label="'Shape'">Shape</BuilderRow>
                <BuilderRow label="'Stretch'" level="1">Stretch</BuilderRow>
            `,
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        await animationFrame();

        const contentSelector = "[data-container-title='Image'] .o_hb_options_container_content";
        const expandedHeight = parseFloat(getComputedStyle(queryOne(contentSelector)).height);
        const toggler = "[data-container-title='Image'] .o_hb_options_container_label_actionable";
        await contains(toggler).click();
        await contains(toggler).click();
        const contentEl = queryOne(contentSelector);
        await waitUntil(() => contentEl.getAnimations()[0]?.playState === "running");
        expect(contentEl.getAnimations()).toHaveLength(1);
        const animation = contentEl.getAnimations()[0];
        animation.pause();
        expect(parseFloat(animation.effect.getKeyframes().at(-1).height)).toBe(expandedHeight);
        animation.currentTime = 0;
        expect(parseFloat(getComputedStyle(contentEl).height)).toBe(0);
        animation.currentTime = animation.effect.getTiming().duration / 2;
        expect(parseFloat(getComputedStyle(contentEl).height)).toBeGreaterThan(0);
        expect(parseFloat(getComputedStyle(contentEl).height)).toBeLessThan(expandedHeight);
        expect("[data-label='Transform']").not.toBeVisible();
        expect("[data-label='Stretch']").not.toBeVisible();
        expect(queryOne("[data-label='Transform']").getAnimations()).toHaveLength(0);
        expect(queryOne("[data-label='Stretch']").getAnimations()).toHaveLength(0);
        animation.finish();
        expect(parseFloat(getComputedStyle(contentEl).height)).toBe(expandedHeight);
    });

    test("sub-option expansion respects disabled transitions and reduced motion", async () => {
        patchWithCleanup(transitionConfig, { disabled: true });
        mockMatchMedia({ "prefers-reduced-motion": "no-preference" });
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`
                <BuilderRow label="'Media'">Media</BuilderRow>
                <BuilderRow label="'Transform'" level="1">Transform</BuilderRow>
            `,
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        await animationFrame();

        const toggler = "[data-label='Media'] .o_hb_collapse_toggler";
        const transformEl = queryOne("[data-label='Transform']");
        await contains(toggler).click();
        expect(transformEl).toBeVisible();
        expect(transformEl.getAnimations()).toHaveLength(0);
        await contains(toggler).click();
        transitionConfig.disabled = false;
        mockMatchMedia({ "prefers-reduced-motion": "reduce" });
        await contains(toggler).click();
        expect(transformEl).toBeVisible();
        expect(transformEl.getAnimations()).toHaveLength(0);
    });

    test("groups register rows when their editing element becomes available", async () => {
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`
                <BuilderRow label="'Controls'">
                    <BuilderButton applyTo="'.child-target'" classAction="'enabled'">Enable</BuilderButton>
                </BuilderRow>
                <BuilderRow label="'Media'" applyTo="'.child-target.enabled'">Media</BuilderRow>
                <BuilderRow label="'Transform'" level="1" applyTo="'.child-target.enabled'">
                    Transform
                </BuilderRow>
            `,
        });
        await setupHTMLBuilder(`
            <div class="test-options-target"><div class="child-target">b</div></div>
        `);
        await contains(":iframe .test-options-target").click();
        await animationFrame();

        expect("[data-label='Media']").toHaveCount(0);
        await contains("[data-class-action='enabled']").click();
        await animationFrame();
        const toggler = "[data-label='Media'] .o_hb_collapse_toggler";
        expect(toggler).toHaveAttribute("aria-expanded", "true");
        await contains(toggler).click();
        expect("[data-label='Transform']").not.toBeVisible();
        await contains("[data-class-action='enabled']").click();
        await animationFrame();
        expect("[data-label='Media']").toHaveCount(0);
        await contains("[data-class-action='enabled']").click();
        await animationFrame();
        expect(toggler).toHaveAttribute("aria-expanded", "true");
        expect("[data-label='Transform']").toBeVisible();
    });

    test("removing a conditional row updates its nested section's group", async () => {
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`
                <BuilderOptionsSection title="'Nested section'">
                    <BuilderRow label="'Media'">
                        <BuilderButton classAction="'enabled'" id="'enabled_opt'">Enable</BuilderButton>
                    </BuilderRow>
                    <BuilderRow label="'Transform'" level="1" t-if="this.isActiveItem('enabled_opt')">
                        Transform
                    </BuilderRow>
                </BuilderOptionsSection>
            `,
        });
        await setupHTMLBuilder(`<div class="test-options-target enabled">b</div>`);
        await contains(":iframe .test-options-target").click();
        await animationFrame();

        const toggler = "[data-label='Media'] .o_hb_collapse_toggler";
        expect(toggler).toHaveAttribute("aria-expanded", "false");
        await contains("[data-class-action='enabled']").click();
        await animationFrame();
        expect("[data-label='Transform']").toHaveCount(0);
        expect(toggler).toHaveCount(0);
        await contains("[data-class-action='enabled']").click();
        await animationFrame();
        expect(toggler).toHaveAttribute("aria-expanded", "true");
        expect("[data-label='Transform']").toBeVisible();
    });

    test("explicit collapse slots and automatic groups toggle independently", async () => {
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`
                <BuilderRow label="'Visibility'" expand="true" observeCollapseContent="true">
                    Visibility
                    <t t-set-slot="collapse">
                        <BuilderRow label="'Condition'" level="1">Condition</BuilderRow>
                    </t>
                </BuilderRow>
                <BuilderRow label="'Animation'">Animation</BuilderRow>
                <BuilderRow label="'Effect'" level="1">Effect</BuilderRow>
            `,
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        await animationFrame();

        expect(".o_hb_collapse_toggler").toHaveCount(2);
        expect("[data-label='Effect']").not.toBeVisible();
        expect("[data-label='Condition']").toBeVisible();
        await contains("[data-label='Animation'] .o_hb_collapse_toggler").click();
        expect("[data-label='Effect']").toBeVisible();
        expect("[data-label='Condition']").toBeVisible();
        await contains("[data-label='Visibility'] .o_hb_collapse_toggler").click();
        await advanceTime(400);
        await animationFrame();
        expect("[data-label='Condition']").not.toBeVisible();
        await contains("[data-label='Animation'] .o_hb_collapse_toggler").click();
        expect("[data-label='Effect']").not.toBeVisible();
        expect("[data-label='Condition']").not.toBeVisible();
        await contains("[data-label='Visibility'] .o_hb_collapse_toggler").click();
        expect("[data-label='Condition']").toBeVisible();
    });

    test("groups stay within their options container", async () => {
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`
                <BuilderRow label="'Media'">Media</BuilderRow>
                <BuilderRow label="'Transform'" level="1">Transform</BuilderRow>
                <BuilderOptionsSection title="'Nested section'">
                    <BuilderRow label="'Animation'">Animation</BuilderRow>
                    <BuilderRow label="'Effect'" level="1">Effect</BuilderRow>
                </BuilderOptionsSection>
            `,
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        await animationFrame();

        const mediaToggler = "[data-label='Media'] .o_hb_collapse_toggler";
        expect(mediaToggler).toHaveAttribute(
            "aria-controls",
            queryOne("[data-label='Transform']").id
        );
        expect("[data-label='Transform']").not.toBeVisible();
        expect("[data-label='Animation']").toBeVisible();
        expect("[data-label='Effect']").not.toBeVisible();
        await contains("[data-label='Animation'] .o_hb_collapse_toggler").click();
        expect("[data-label='Effect']").toBeVisible();
        expect("[data-label='Transform']").not.toBeVisible();
        await contains(mediaToggler).click();
        expect("[data-label='Transform']").toBeVisible();
        expect("[data-label='Effect']").toBeVisible();
        await contains("[data-label='Animation'] .o_hb_collapse_toggler").click();
        expect("[data-label='Effect']").not.toBeVisible();
        expect("[data-label='Transform']").toBeVisible();
    });
});

/* ================= Collapse template ================= */
const collapseOptionTemplate = ({
    dependency = false,
    expand = false,
    observeCollapseContent = false,
} = {}) => xml`
        <BuilderRow label="'Test Collapse'" expand="${expand}" observeCollapseContent="${observeCollapseContent}">
            <BuilderButton classAction="'a'" ${
                dependency ? "id=\"'test_opt'\"" : ""
            }>A</BuilderButton>
            <t t-set-slot="collapse">
                <BuilderRow level="1" label="'B'" ${
                    dependency ? "t-if=\"this.isActiveItem('test_opt')\"" : ""
                }>
                    <BuilderButton classAction="'b'">B</BuilderButton>
                </BuilderRow>
            </t>
        </BuilderRow>`;

describe("BuilderRow with collapse content", () => {
    test("expand=false is collapsed by default", async () => {
        addBuilderOption({
            selector: ".test-options-target",
            template: collapseOptionTemplate(),
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".o_hb_options_container").toBeVisible();
        expect(".o_hb_collapse_toggler:not(.d-none)").not.toHaveClass("active");
    });

    test("expand=true is expanded by default", async () => {
        addBuilderOption({
            selector: ".test-options-target",
            template: collapseOptionTemplate({ dependency: false, expand: true }),
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".o_hb_options_container").toBeVisible();
        await animationFrame();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveClass("active");
    });

    test("Toggler button is not visible if no dependency is active", async () => {
        addBuilderOption({
            selector: ".test-options-target",
            template: collapseOptionTemplate({
                dependency: true,
                observeCollapseContent: true,
            }),
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".o_hb_options_container").toBeVisible();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveCount(0);
    });

    test("observed collapse content expands when a dependency becomes active", async () => {
        addBuilderOption({
            selector: ".test-options-target",
            template: collapseOptionTemplate({
                dependency: true,
                observeCollapseContent: true,
            }),
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveCount(0);

        await contains(".o_hb_options_container button[data-class-action='a']").click();
        await animationFrame();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveAttribute("aria-expanded", "true");
        expect(".o_hb_options_container button[data-class-action='b']").toBeVisible();
        await contains(".o_hb_options_container button[data-class-action='b']").click();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveAttribute("aria-expanded", "true");

        await contains(".o_hb_collapse_toggler:not(.d-none)").click();
        await advanceTime(400);
        await animationFrame();
        expect(".o_hb_options_container button[data-class-action='b']").not.toBeVisible();
        await contains(".o_hb_options_container button[data-class-action='a']").click();
        await animationFrame();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveCount(0);
        await contains(".o_hb_options_container button[data-class-action='a']").click();
        await animationFrame();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveAttribute("aria-expanded", "true");
        expect(".o_hb_options_container button[data-class-action='b']").toBeVisible();
    });

    test("expand=true works when a dependency becomes active", async () => {
        addBuilderOption({
            selector: ".test-options-target",
            template: collapseOptionTemplate({ dependency: true, expand: true }),
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".o_hb_options_container").toBeVisible();
        await contains(".o_hb_options_container button[data-class-action='a']").click();
        await animationFrame();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveCount(1);
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveClass("active");
        expect(".o_hb_options_container button[data-class-action='b']").toBeVisible();
    });

    test("Collapse works with several dependencies", async () => {
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`
                <BuilderRow label="'Test Collapse'" expand="true">
                    <BuilderSelect>
                        <BuilderSelectItem classAction="'a'" id="'test_opt'">A</BuilderSelectItem>
                        <BuilderSelectItem classAction="'c'" id="'random_opt'">C</BuilderSelectItem>
                    </BuilderSelect>
                    <t t-set-slot="collapse">
                        <BuilderRow level="1" t-if="this.isActiveItem('test_opt')" label="'B'">
                            <BuilderButton classAction="'b'">B</BuilderButton>
                        </BuilderRow>
                        <BuilderRow level="1" t-if="this.isActiveItem('random_opt')" label="'D'">
                            <BuilderButton classAction="'d'">D</BuilderButton>
                        </BuilderRow>
                    </t>
                </BuilderRow>
            `,
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".o_hb_options_container").toBeVisible();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveCount(0);
        await contains(".o_hb_options_container .dropdown-toggle").click();
        await contains(".dropdown-menu [data-class-action='a']").click();
        await animationFrame();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveCount(1);
        expect(".o_hb_options_container button[data-class-action='b']").toBeVisible();
        expect(".o_hb_options_container button[data-class-action='d']").not.toHaveCount();
        await contains(".o_hb_options_container .dropdown-toggle").click();
        await contains(".dropdown-menu [data-class-action='c']").click();
        await animationFrame();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveCount(1);
        expect(".o_hb_options_container button[data-class-action='b']").not.toHaveCount();
        expect(".o_hb_options_container button[data-class-action='d']").toBeVisible();
    });

    test("Click on toggler collapses / expands the BuilderRow", async () => {
        reapplyCollapseTransition();
        addBuilderOption({
            selector: ".test-options-target",
            template: collapseOptionTemplate(),
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".o_hb_options_container").toBeVisible();
        expect(".o_hb_collapse_toggler:not(.d-none)").not.toHaveClass("active");
        expect(".o_hb_options_container button[data-class-action='b']").toHaveCount(0);
        await contains(".o_hb_collapse_toggler:not(.d-none)").click();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveClass("active");
        expect(".o_hb_options_container button[data-class-action='b']").toBeVisible();
        const contentEl = queryOne(".o_hb_options_container .o_hb_collapse_content");
        expect(contentEl.style.height).toBe(`${ONE_ROW_HEIGHT}px`);
        expect(parseFloat(getComputedStyle(contentEl).height)).toBeLessThan(ONE_ROW_HEIGHT);
        await waitUntil(() => parseFloat(getComputedStyle(contentEl).height) >= ONE_ROW_HEIGHT - 1);
        // Collapsing pins the measured height, then targets 0 for the CSS transition.
        await contains(".o_hb_collapse_toggler:not(.d-none)").click();
        expect(contentEl.style.height).toBe("0px");
        expect(parseFloat(getComputedStyle(contentEl).height)).toBeGreaterThan(0);
        advanceTime(400); // wait for the collapse transition to be over
        await animationFrame();
        expect(".o_hb_collapse_toggler:not(.d-none)").not.toHaveClass("active");
        expect(".o_hb_options_container button[data-class-action='b']").toHaveCount(0);
        expect(parseFloat(getComputedStyle(contentEl).height)).toBe(NaN);
    });

    test("Click on toggler collapses / expands the BuilderRow (with observeCollapseContent)", async () => {
        reapplyCollapseTransition();
        addBuilderOption({
            selector: ".test-options-target",
            template: collapseOptionTemplate({ observeCollapseContent: true }),
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".o_hb_options_container").toBeVisible();
        expect(".o_hb_collapse_toggler:not(.d-none)").not.toHaveClass("active");
        expect(".o_hb_options_container button[data-class-action='b']").not.toBeVisible();
        // The content is never unmounted here, only hidden: it starts collapsed at 0.
        const contentEl = queryOne(".o_hb_options_container .o_hb_collapse_content");
        expect(contentEl.style.height).toBe("0px");
        await contains(".o_hb_collapse_toggler:not(.d-none)").click();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveClass("active");
        expect(".o_hb_options_container button[data-class-action='b']").toBeVisible();
        expect(contentEl.style.height).toBe(`${ONE_ROW_HEIGHT}px`);
        expect(parseFloat(getComputedStyle(contentEl).height)).toBeLessThan(ONE_ROW_HEIGHT);
        await contains(".o_hb_collapse_toggler:not(.d-none)").click();
        expect(".o_hb_collapse_toggler:not(.d-none)").not.toHaveClass("active");
        advanceTime(400); // wait for the collapse transition to be over
        await animationFrame();
        expect(".o_hb_options_container button[data-class-action='b']").not.toBeVisible();
    });

    test("Click header row's label collapses / expands the BuilderRow", async () => {
        reapplyCollapseTransition();
        addBuilderOption({
            selector: ".test-options-target",
            template: collapseOptionTemplate(),
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".o_hb_options_container").toBeVisible();
        expect(".o_hb_collapse_toggler:not(.d-none)").not.toHaveClass("active");
        expect(".o_hb_options_container button[data-class-action='b']").toHaveCount(0);
        await contains("[data-label='Test Collapse'] span:contains('Test Collapse')").click();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveClass("active");
        expect(".o_hb_options_container button[data-class-action='b']").toBeVisible();
        await contains("[data-label='Test Collapse'] span:contains('Test Collapse')").click();
        advanceTime(400); // wait for the collapse transition to be over
        await animationFrame();
        expect(".o_hb_collapse_toggler:not(.d-none)").not.toHaveClass("active");
        expect(".o_hb_options_container button[data-class-action='b']").toHaveCount(0);
    });

    test("Click header row's label collapses / expands the BuilderRow (with observeCollapseContent)", async () => {
        addBuilderOption({
            selector: ".test-options-target",
            template: collapseOptionTemplate({ observeCollapseContent: true }),
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".o_hb_options_container").toBeVisible();
        expect(".o_hb_collapse_toggler:not(.d-none)").not.toHaveClass("active");
        expect(".o_hb_options_container button[data-class-action='b']").not.toBeVisible();
        await contains("[data-label='Test Collapse'] span:contains('Test Collapse')").click();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveClass("active");
        expect(".o_hb_options_container button[data-class-action='b']").toBeVisible();
        await contains("[data-label='Test Collapse'] span:contains('Test Collapse')").click();
        expect(".o_hb_collapse_toggler:not(.d-none)").not.toHaveClass("active");
        advanceTime(400); // wait for the collapse transition to be over
        await animationFrame();
        expect(".o_hb_options_container button[data-class-action='b']").not.toBeVisible();
    });

    test("Two BuilderRows with collapse content on the same option are toggled independently", async () => {
        addBuilderOption({
            selector: ".test-options-target",
            template: collapseOptionTemplate({ dependency: true, expand: true }),
        });
        addBuilderOption({
            selector: ".test-options-target",
            template: collapseOptionTemplate(),
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        expect(".o_hb_options_container").toBeVisible();
        await animationFrame();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveCount(1);
        await contains(".o_hb_options_container [data-class-action='a']:first").click();
        await animationFrame();
        expect(".o_hb_collapse_toggler:not(.d-none)").toHaveCount(2);
        expect(".o_hb_collapse_toggler:not(.d-none):first").toHaveClass("active");
        expect(".o_hb_collapse_toggler:not(.d-none):not(.d-none):last").not.toHaveClass("active");
        await contains(".o_hb_options_container .o_hb_collapse_toggler:not(.d-none):last").click();
        expect(".o_hb_collapse_toggler:not(.d-none):first").toHaveClass("active");
        expect(".o_hb_collapse_toggler:not(.d-none):last").toHaveClass("active");
        await contains(".o_hb_options_container .o_hb_collapse_toggler:not(.d-none):first").click();
        expect(".o_hb_collapse_toggler:not(.d-none):first").not.toHaveClass("active");
        expect(".o_hb_collapse_toggler:not(.d-none):last").toHaveClass("active");
    });
});

describe.tags("desktop");
describe("HTML builder tests", () => {
    test("add tooltip when label is too long", async () => {
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`<BuilderRow label="'Supercalifragilisticexpalidocious'">Palais chatouille</BuilderRow>`,
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        const textEl = queryOne(
            "[data-label='Supercalifragilisticexpalidocious'] > .o_hb_row_label span"
        );
        await hover(textEl);
        await advanceTime(OPEN_DELAY);
        await waitFor(
            "[data-text-truncate-tooltip][data-text-truncate-tooltip-checked='true'][data-tooltip='Supercalifragilisticexpalidocious']"
        );
        expect(textEl.scrollWidth).toBeGreaterThan(textEl.clientWidth); // the text is longer than the available width.
    });
    test("show row label before tooltip when label is truncated and hovering on wrapper", async () => {
        addBuilderOption({
            selector: ".test-options-target",
            template: xml`<BuilderRow label="'Supercalifragilisticexpalidocious'" tooltip="'my tooltip'">Palais chatouille</BuilderRow>`,
        });
        await setupHTMLBuilder(`<div class="test-options-target">b</div>`);
        await contains(":iframe .test-options-target").click();
        const textEl = queryOne(
            "[data-label='Supercalifragilisticexpalidocious'] > .o_hb_row_label span"
        );
        await hover(textEl);
        await advanceTime(OPEN_DELAY);
        await waitFor(
            "[data-tooltip='Supercalifragilisticexpalidocious\\00a0: my tooltip'] > [data-text-truncate-tooltip][data-text-truncate-tooltip-checked='true']"
        );
        expect(textEl.scrollWidth).toBeGreaterThan(textEl.clientWidth); // the text is longer than the available width.
    });
});
