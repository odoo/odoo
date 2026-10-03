import { expect, test } from "@odoo/hoot";
import { click, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { setupEditor } from "@html_editor/../tests/_helpers/editor";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expandToolbar, openToolbarMenu } from "@html_editor/../tests/_helpers/toolbar";
import { openEffectsSection } from "@html_builder/../tests/helpers";
import { EffectsPanelPlugin } from "@html_builder/plugins/effects/effects_plugin";
import { HighlightPlugin } from "@website/builder/plugins/highlight/highlight_plugin";
import { contains } from "@web/../tests/web_test_helpers";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { Plugin } from "@html_editor/plugin";
import { highlightIdToName } from "@website/builder/plugins/highlight/highlight_configurator";
import { textHighlightFactory } from "@website/js/highlight_utils";
import { unformat } from "@html_editor/../tests/_helpers/format";

defineMailModels();

class FakeEditInteractionPlugin extends Plugin {
    static id = "edit_interaction";
    static shared = ["stopInteraction"];
    stopInteraction() {}
}

function checkHighlightColor(highlightStyle, expectedColor = "var(--hb-cp-o-color-1)") {
    const color = document.documentElement
        .querySelector(`span.${highlightStyle}`)
        .style.getPropertyValue("--text-highlight-color");
    expect(color).toBe(expectedColor);
}

test("Can highlight a selected text", async () => {
    await setupEditor("<p>This is [highlighted]</p>", {
        config: { includePlugins: [HighlightPlugin, EffectsPanelPlugin, FakeEditInteractionPlugin] },
    });

    await expandToolbar();
    expect(".o-select-effects").toHaveCount(1);
    await openEffectsSection("highlight");
    expect("#highlightPicker").toHaveText("None");
    await contains("#highlightPicker").click();
    await waitFor(".o_popover .o_text_highlight_underline");

    expect("p>.o_text_highlight_underline").toHaveCount(0);
    checkHighlightColor("o_text_highlight_underline");

    await click(".o_popover .o_text_highlight_underline");
    expect("p>.o_text_highlight_underline").toHaveCount(1);
    // The shapes are then drawn in the color of the highlight.
    await contains("#highlightPicker").click();
    checkHighlightColor("o_text_highlight_freehand_2", "#714B67");
});

test("Check no highlight color is displayed in colorpicker when text with multiple highlight color is selected", async () => {
    await setupEditor(
        `<p>
            [This is <span class="o_text_highlight o_text_highlight_underline" style="--text-highlight-color: #FFFF00;">first</span> and <span class="o_text_highlight o_text_highlight_freehand_2">second</span>]
        </p>`,
        { config: { includePlugins: [HighlightPlugin, EffectsPanelPlugin, FakeEditInteractionPlugin] } }
    );

    // Open highlight toolbar
    await expandToolbar();
    expect(".o-select-effects").toHaveCount(1);
    await openEffectsSection("highlight");
    expect("#colorButton").not.toHaveAttribute("style");
});

test("Can set a color to a highlight", async () => {
    await setupEditor(
        `
        <p>
            <span class="o_text_highlight o_text_highlight_freehand_2">[highlight 3]</span>
        </p>`,
        { config: { includePlugins: [HighlightPlugin, EffectsPanelPlugin, FakeEditInteractionPlugin] } }
    );
    await expandToolbar();
    expect(".o-select-effects").toHaveCount(1);
    await openEffectsSection("highlight");
    await animationFrame();
    await click("#colorButton");
    await animationFrame();
    await click("button[style*='background-color: var(--hb-cp-o-color-2)']");
    await animationFrame();
    const color = getComputedStyle(document.documentElement).getPropertyValue("--o-color-2");
    expect("span.o_text_highlight_freehand_2").toHaveStyle({
        "--text-highlight-color": color,
    });
});

test("Changing highlight keep the color and the width", async () => {
    await setupEditor(
        `<p>
            <span class="o_text_highlight o_text_highlight_freehand_2" style="--text-highlight-color: #E79C9C; --text-highlight-width: 2px;">[highlight 3]</span>
        </p>`,
        { config: { includePlugins: [HighlightPlugin, EffectsPanelPlugin, FakeEditInteractionPlugin] } }
    );
    await expandToolbar();
    expect(".o-select-effects").toHaveCount(1);
    await openEffectsSection("highlight");
    await contains("#highlightPicker").click();

    expect("p>.o_text_highlight_underline").toHaveCount(0);
    await contains(".o_popover .o_text_highlight_underline").click();
    expect("p>.o_text_highlight_underline").toHaveCount(1);
    expect("p>span.o_text_highlight_underline").toHaveStyle({
        "--text-highlight-color": "#E79C9C",
        "--text-highlight-width": "2px",
    });
});

test("Selecting partially a highlight select all the highlight", async () => {
    const { editor } = await setupEditor(
        ` 
        <p>
            <span class="o_text_highlight o_text_highlight_freehand_2" style="--text-highlight-color: #E79C9C; --text-highlight-width: 2px;">h[i]ghlight</span>
        </p>`,
        { config: { includePlugins: [HighlightPlugin, EffectsPanelPlugin, FakeEditInteractionPlugin] } }
    );
    await expandToolbar();
    expect(".o-select-effects").toHaveCount(1);
    let selectionData = editor.shared.selection.getEditableSelection();
    expect(selectionData.anchorOffset).toBe(1);
    expect(selectionData.focusOffset).toBe(2);
    await openEffectsSection("highlight");
    selectionData = editor.shared.selection.getEditableSelection();
    expect(selectionData.anchorOffset).toBe(0);
    expect(selectionData.focusOffset).toBe(9);
});

test("Can remove an highlight with the None shape", async () => {
    await setupEditor(
        ` 
        <p>
            <span class="o_text_highlight o_text_highlight_freehand_2" style="--text-highlight-color: #E79C9C; --text-highlight-width: 2px;">h[i]ghlight</span>
        </p>`,
        { config: { includePlugins: [HighlightPlugin, EffectsPanelPlugin, FakeEditInteractionPlugin] } }
    );
    await expandToolbar();
    expect(".o-select-effects").toHaveCount(1);
    expect(".o-select-effects").toHaveClass("active");
    expect("p .o_text_highlight").toHaveCount(1);
    await openEffectsSection("highlight");
    expect(".o-we-effects-section[data-section='highlight']").toHaveClass(
        "o-we-effects-section-active"
    );
    await click(".o-we-effects-section[data-section='highlight'] .o-we-panel-select");
    await animationFrame();
    await click(".o_highlight_picker .o_highlight_none");
    await animationFrame();
    expect("p .o_text_highlight").toHaveCount(0);
    expect(".o-we-effects-section[data-section='highlight']").not.toHaveClass(
        "o-we-effects-section-active"
    );
});

test("Similar adjacent highlights are merged", async () => {
    await setupEditor(
        `<p>
            <span class="o_text_highlight o_text_highlight_freehand_2" style="--text-highlight-width: 1px;">highlight</span><span class="o_text_highlight o_text_highlight_freehand_1">[highlight2]</span>
        </p>`,
        { config: { includePlugins: [HighlightPlugin, EffectsPanelPlugin, FakeEditInteractionPlugin] } }
    );
    await expandToolbar();
    expect(".o-select-effects").toHaveCount(1);
    await openEffectsSection("highlight");

    expect("p>.o_text_highlight_freehand_2").toHaveCount(1);
    expect("p>.o_text_highlight_freehand_1").toHaveCount(1);
    await contains("#highlightPicker").click();
    await contains(".o_popover .o_text_highlight_freehand_2").click();
    expect("p>.o_text_highlight_freehand_2").toHaveCount(1);
    expect("p>.o_text_highlight_freehand_1").toHaveCount(0);
});

test("Remove format on highlight does not create an empty node", async () => {
    const { editor } = await setupEditor(
        `<p>
            <span class="o_text_highlight o_text_highlight_freehand_2" style="--text-highlight-color: #E79C9C; --text-highlight-width: 2px;">highligh[t]</span>
        </p>`,
        { config: { includePlugins: [HighlightPlugin, EffectsPanelPlugin, FakeEditInteractionPlugin] } }
    );
    await expandToolbar();
    const selectedHighlights = (editor) =>
        editor.shared.selection
            .getTargetedNodes()
            .map((n) => closestElement(n, ".o_text_highlight"))
            .filter(Boolean);
    expect("p>.o_text_highlight_freehand_2").toHaveCount(1);
    expect(selectedHighlights(editor)).toHaveLength(1);
    await openToolbarMenu("more_formatting");
    await contains("[name='remove_format']").click();
    expect("p>.o_text_highlight_freehand_2").toHaveCount(1);
    expect(selectedHighlights(editor)).toHaveLength(0);
});

test("Can modify multiple highlights", async () => {
    await setupEditor(
        `<p> [
            <span class="o_text_highlight o_text_highlight_freehand_2" style="--text-highlight-color: #E79C9C; --text-highlight-width: 3px;">highlight1</span>
            <span class="o_text_highlight o_text_highlight_freehand_2" style="--text-highlight-color: #E79C9C; --text-highlight-width: 3px;">highlight</span>
            ]
        </p>`,
        { config: { includePlugins: [HighlightPlugin, EffectsPanelPlugin, FakeEditInteractionPlugin] } }
    );
    await expandToolbar();
    expect(".o-select-effects").toHaveCount(1);
    expect("p .o_text_highlight").toHaveCount(2);
    await openEffectsSection("highlight");
    expect("#highlightPicker").toHaveText("Multiple");
    expect("#colorButton").toHaveStyle({
        "background-color": "rgb(231, 156, 156)",
    });
    expect("#thicknessInput").toHaveValue(3);
    await contains("#highlightPicker").click();
    await contains(".o_popover .o_text_highlight_underline").click();
    expect("p>.o_text_highlight_underline").toHaveCount(1);
    expect("p .o_text_highlight").toHaveCount(1);
});

test("each highlight has a name", () => {
    const highlightWithAName = Object.keys(highlightIdToName);
    const highlightWithAPath = Object.keys(textHighlightFactory);
    highlightWithAName.sort();
    highlightWithAPath.sort();
    expect(highlightWithAPath).toEqual(highlightWithAName);
});

test("Should override existing highlight", async () => {
    const { el } = await setupEditor(
        unformat(
            `<p>
                [a
                <span class="o_text_highlight o_text_highlight_freehand_1" style="--text-highlight-width: 4px;">
                    <span class="o_animated_text o_animate o_anim_fade_in o_visible o_animated" style="visibility: visible; animation-play-state: running;">b</span>
                </span>
                c]
            </p>`
        ),
        { config: { includePlugins: [HighlightPlugin, EffectsPanelPlugin, FakeEditInteractionPlugin] } }
    );
    await expandToolbar();
    await openEffectsSection("highlight");
    await contains("#highlightPicker").click();
    await contains(".o_popover .o_text_highlight_underline").click();
    expect(el.innerHTML).toBe(
        unformat(
            `<p>
                <span class="o_text_highlight o_text_highlight_underline" style="--text-highlight-width: 4px;">
                    a
                    <span class="o_animated_text o_animate o_anim_fade_in o_visible o_animated" style="visibility: visible; animation-play-state: running;"><span>b</span></span>
                    c
                </span>
            </p>`
        )
    );
});
