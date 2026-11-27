import { expect, test } from "@odoo/hoot";
import { click, press, queryOne, waitFor, waitForNone } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { setupEditor } from "@html_editor/../tests/_helpers/editor";
import { setSelection } from "@html_editor/../tests/_helpers/selection";
import {
    expandToolbar,
    expectAccessibleLabels,
    expectConsistentAriaStates,
} from "@html_editor/../tests/_helpers/toolbar";
import { HighlightPlugin } from "@website/builder/plugins/highlight/highlight_plugin";
import { contains } from "@web/../tests/web_test_helpers";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { Plugin } from "@html_editor/plugin";
import { highlightIdToName } from "@website/builder/plugins/highlight/highlight_configurator";
import { textHighlightFactory } from "@website/js/highlight_utils";
import { unformat } from "@html_editor/../tests/_helpers/format";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

class FakeEditInteractionPlugin extends Plugin {
    static id = "edit_interaction";
    static shared = ["stopInteraction"];
    stopInteraction() {}
}

function checkHighlightColor(highlightStyle) {
    const color = document.documentElement
        .querySelector(`span.${highlightStyle}`)
        .style.getPropertyValue("--text-highlight-color");
    expect(color).toBe("var(--hb-cp-o-color-1)");
}

test("Can highlight a selected text", async () => {
    await setupEditor("<p>This is [highlighted]</p>", {
        config: { includePlugins: [HighlightPlugin, FakeEditInteractionPlugin] },
    });

    await expandToolbar();
    expect(".o_hb_select_highlight").toHaveCount(1);
    await click(".o-we-toolbar .o_hb_select_highlight");
    await waitFor(".o_popover .o_text_highlight_underline");

    expect("p>.o_text_highlight_underline").toHaveCount(0);
    checkHighlightColor("o_text_highlight_underline");

    await click(".o_popover .o_text_highlight_underline");
    expect("p>.o_text_highlight_underline").toHaveCount(1);
    checkHighlightColor("o_text_highlight_freehand_2");
});

test("highlight button aria-expanded should match whether its popover is open", async () => {
    const { editor } = await setupEditor("<p>This is [highlighted]</p>", {
        config: { includePlugins: [HighlightPlugin, FakeEditInteractionPlugin] },
    });
    // The `active` class of these buttons means that a text effect is applied,
    // so the popup state is read from `aria-expanded`, checked here
    const isPopupOpen = (el) => el.getAttribute("aria-expanded") === "true";
    const expectAccessibleToolbar = () => {
        expectConsistentAriaStates(editor, { isPopupOpen });
        expectAccessibleLabels();
    };

    await expandToolbar();
    expect(".o_hb_select_highlight").toHaveAttribute("aria-haspopup", "dialog");
    expect(".o_hb_select_highlight").toHaveAttribute("aria-expanded", "false");
    expectAccessibleToolbar();
    await click(".o-we-toolbar .o_hb_select_highlight");
    await waitFor(".o_popover .o_text_highlight_underline");
    expect(".o_hb_select_highlight").toHaveAttribute("aria-expanded", "true");
    expectAccessibleToolbar();

    await press("Escape");
    await waitForNone(".o_popover .o_text_highlight_underline");
    expect(".o_hb_select_highlight").toHaveAttribute("aria-expanded", "false");
    expectAccessibleToolbar();
});

test("Check no highlight color is displayed in colorpicker when text with multiple highlight color is selected", async () => {
    await setupEditor(
        `<p>
            [This is <span class="o_text_highlight o_text_highlight_underline" style="--text-highlight-color: #FFFF00;">first</span> and <span class="o_text_highlight o_text_highlight_freehand_2">second</span>]
        </p>`,
        { config: { includePlugins: [HighlightPlugin, FakeEditInteractionPlugin] } }
    );

    // Open highlight toolbar
    await expandToolbar();
    expect(".o_hb_select_highlight").toHaveCount(1);
    await contains(".o-we-toolbar .o_hb_select_highlight").click();
    expect("#colorButton").not.toHaveAttribute("style");
});

test("Can set a color to a highlight", async () => {
    await setupEditor(
        `
        <p>
            <span class="o_text_highlight o_text_highlight_freehand_2">[highlight 3]</span>
        </p>`,
        { config: { includePlugins: [HighlightPlugin, FakeEditInteractionPlugin] } }
    );
    await expandToolbar();
    expect(".o_hb_select_highlight").toHaveCount(1);
    await click(".o-we-toolbar .o_hb_select_highlight");
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
        { config: { includePlugins: [HighlightPlugin, FakeEditInteractionPlugin] } }
    );
    await expandToolbar();
    expect(".o_hb_select_highlight").toHaveCount(1);
    await contains(".o-we-toolbar .o_hb_select_highlight").click();
    await contains("#highlightPicker").click();

    expect("p>.o_text_highlight_underline").toHaveCount(0);
    await contains(".o_popover .o_text_highlight_underline").click();
    expect("p>.o_text_highlight_underline").toHaveCount(1);
    expect("p>span.o_text_highlight_underline").toHaveStyle({
        "--text-highlight-color": "#E79C9C",
        "--text-highlight-width": "2px",
    });
});

test("should show the current highlight as active when opening the picker", async () => {
    await setupEditor(
        `<p>
            <span class="o_text_highlight o_text_highlight_freehand_2" style="--text-highlight-color: #E79C9C; --text-highlight-width: 2px;">[highlight 3]</span>
        </p>`,
        { config: { includePlugins: [HighlightPlugin, FakeEditInteractionPlugin] } }
    );
    await expandToolbar();
    await contains(".o-we-toolbar .o_hb_select_highlight").click();
    await contains("#highlightPicker").click();
    expect(".o_popover .border-primary .o_text_highlight").toHaveCount(1);
    expect(".o_popover .border-primary .o_text_highlight").toHaveClass(
        "o_text_highlight_freehand_2"
    );
});

test("Selecting partially a highlight select all the highlight", async () => {
    const { editor } = await setupEditor(
        ` 
        <p>
            <span class="o_text_highlight o_text_highlight_freehand_2" style="--text-highlight-color: #E79C9C; --text-highlight-width: 2px;">h[i]ghlight</span>
        </p>`,
        { config: { includePlugins: [HighlightPlugin, FakeEditInteractionPlugin] } }
    );
    await expandToolbar();
    expect(".o_hb_select_highlight").toHaveCount(1);
    let selectionData = editor.shared.selection.getEditableSelection();
    expect(selectionData.anchorOffset).toBe(1);
    expect(selectionData.focusOffset).toBe(2);
    await click(".o-we-toolbar .o_hb_select_highlight");
    selectionData = editor.shared.selection.getEditableSelection();
    expect(selectionData.anchorOffset).toBe(0);
    expect(selectionData.focusOffset).toBe(9);
});

test("Can remove an highlight with the trash button", async () => {
    await setupEditor(
        ` 
        <p>
            <span class="o_text_highlight o_text_highlight_freehand_2" style="--text-highlight-color: #E79C9C; --text-highlight-width: 2px;">h[i]ghlight</span>
        </p>`,
        { config: { includePlugins: [HighlightPlugin, FakeEditInteractionPlugin] } }
    );
    await expandToolbar();
    expect(".o_hb_select_highlight").toHaveCount(1);
    expect(".o_hb_select_highlight").toHaveClass("active");
    expect(".o_text_highlight").toHaveCount(1);
    await click(".o-we-toolbar .o_hb_select_highlight");
    await waitFor("button[title='Reset']");
    await click("button[title='Reset']");
    expect(".o_text_highlight").toHaveCount(0);
});

test("Similar adjacent highlights are merged", async () => {
    await setupEditor(
        `<p>
            <span class="o_text_highlight o_text_highlight_freehand_2" style="--text-highlight-width: 1px;">highlight</span><span class="o_text_highlight o_text_highlight_freehand_1">[highlight2]</span>
        </p>`,
        { config: { includePlugins: [HighlightPlugin, FakeEditInteractionPlugin] } }
    );
    await expandToolbar();
    expect(".o_hb_select_highlight").toHaveCount(1);
    await contains(".o-we-toolbar .o_hb_select_highlight").click();

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
        { config: { includePlugins: [HighlightPlugin, FakeEditInteractionPlugin] } }
    );
    await expandToolbar();
    const selectedHighlights = (editor) =>
        editor.shared.selection
            .getTargetedNodes()
            .map((n) => closestElement(n, ".o_text_highlight"))
            .filter(Boolean);
    expect("p>.o_text_highlight_freehand_2").toHaveCount(1);
    expect(selectedHighlights(editor)).toHaveLength(1);
    await contains(".o-we-toolbar [data-icon='ink_eraser']").click();
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
        { config: { includePlugins: [HighlightPlugin, FakeEditInteractionPlugin] } }
    );
    await expandToolbar();
    expect(".o_hb_select_highlight").toHaveCount(1);
    expect(".o_text_highlight").toHaveCount(2);
    await contains(".o-we-toolbar .o_hb_select_highlight").click();
    expect("#highlightPicker").toHaveText("");
    expect("#colorButton").toHaveStyle({
        "background-color": "rgb(231, 156, 156)",
    });
    expect("#thicknessInput").toHaveValue(3);
    await contains("#highlightPicker").click();
    await contains(".o_popover .o_text_highlight_underline").click();
    expect("p>.o_text_highlight_underline").toHaveCount(1);
    expect(".o_text_highlight").toHaveCount(1);
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
        { config: { includePlugins: [HighlightPlugin, FakeEditInteractionPlugin] } }
    );
    await expandToolbar();
    await contains(".o-we-toolbar .o_hb_select_highlight").click();
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

test("Highlight wraps each line of a multi-line text", async () => {
    const { el } = await setupEditor(
        "<p>[<strong>Text content line A</strong><br><i>Text content line B</i>]</p>",
        { config: { includePlugins: [HighlightPlugin, FakeEditInteractionPlugin] } }
    );
    await expandToolbar();
    await contains(".o-we-toolbar .o_hb_select_highlight").click();
    await contains(".o_popover .o_text_highlight_underline").click();
    expect("span:contains(Text content line A)").toHaveClass("o_text_highlight_underline");
    expect("span:contains(Text content line B)").toHaveClass("o_text_highlight_underline");

    await contains("#highlightPicker").click();
    await contains(".o_popover .o_text_highlight_jagged").click();
    expect("span:contains(Text content line A)").toHaveClass("o_text_highlight_jagged");
    expect("span:contains(Text content line B)").toHaveClass("o_text_highlight_jagged");

    await contains("button[title='Reset']").click();
    expect(el.querySelector("p")).toHaveInnerHTML(
        "<strong>Text content line A</strong><br><i>Text content line B</i>"
    );
});

test("Edit mode interaction draws, redraws and removes the highlight svgs", async () => {
    await setupWebsiteBuilder("<h1>Catchy Headline</h1>", {
        loadIframeBundles: true,
        interactions: ["website.text_highlight"],
    });
    const h1 = queryOne(":iframe h1");
    setSelection({ anchorNode: h1, anchorOffset: 0, focusNode: h1, focusOffset: 1 });
    await expandToolbar();
    await contains(".o-we-toolbar button[title='Apply highlight']").click();
    await contains(".o_popover .o_text_highlight_underline").click();
    await waitFor(":iframe h1 span.o_text_highlight_underline svg.o_text_highlight_svg");

    await contains(".o_popover #highlightPicker").click();
    await contains(".o_popover .o_text_highlight_jagged").click();
    await waitFor(":iframe h1 span.o_text_highlight_jagged svg.o_text_highlight_svg");

    await contains(".o_popover button[title='Reset']").click();
    await waitForNone(":iframe h1 svg");
    expect(":iframe h1").toHaveInnerHTML("Catchy Headline");
});
