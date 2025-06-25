import { expect, test } from "@odoo/hoot";
import { click, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { setupEditor } from "@html_editor/../tests/_helpers/editor";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expandToolbar } from "@html_editor/../tests/_helpers/toolbar";
import { HighlightPlugin } from "@website/builder/plugins/highlight/highlight_plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { contains } from "@web/../tests/web_test_helpers";
import { closestElement } from "@html_editor/utils/dom_traversal";

defineMailModels();

test("Can highlight a selected text", async () => {
    await setupEditor("<p>This is [highlighted]</p>", {
        config: { Plugins: [...MAIN_PLUGINS, HighlightPlugin] },
    });

    await expandToolbar();
    expect(".o-select-highlight").toHaveCount(1);
    await click(".o-we-toolbar .o-select-highlight");
    await waitFor(".o_popover .o_text_highlight_underline");

    expect("p>.o_text_highlight_underline").toHaveCount(0);
    await click(".o_popover .o_text_highlight_underline");
    expect("p>.o_text_highlight_underline").toHaveCount(1);
});

test("Can set a color to a highlight", async () => {
    await setupEditor(
        `
        <p>
            <span class="o_text_highlight o_text_highlight_freehand_2">[highlight 3]</span>
        </p>`,
        { config: { Plugins: [...MAIN_PLUGINS, HighlightPlugin] } }
    );
    await expandToolbar();
    expect(".o-select-highlight").toHaveCount(1);
    await click(".o-we-toolbar .o-select-highlight");
    await animationFrame();
    await click("#colorButton");
    await animationFrame();
    await click("button[style='background-color: var(--o-color-1)']");
    await animationFrame();
    const color = getComputedStyle(document.documentElement).getPropertyValue("--o-color-1");
    expect("span.o_text_highlight_freehand_2").toHaveStyle({
        "--text-highlight-color": color,
    });
});

test("Changing highlight keep the color and the width", async () => {
    await setupEditor(
        `<p>
            <span class="o_text_highlight o_text_highlight_freehand_2" style="--text-highlight-color: #E79C9C; --text-highlight-width: 2px;">[highlight 3]</span>
        </p>`,
        { config: { Plugins: [...MAIN_PLUGINS, HighlightPlugin] } }
    );
    await expandToolbar();
    expect(".o-select-highlight").toHaveCount(1);
    await contains(".o-we-toolbar .o-select-highlight").click();
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
        { config: { Plugins: [...MAIN_PLUGINS, HighlightPlugin] } }
    );
    await expandToolbar();
    expect(".o-select-highlight").toHaveCount(1);
    let selectionData = editor.shared.selection.getEditableSelection();
    expect(selectionData.anchorOffset).toBe(1);
    expect(selectionData.focusOffset).toBe(2);
    await click(".o-we-toolbar .o-select-highlight");
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
        { config: { Plugins: [...MAIN_PLUGINS, HighlightPlugin] } }
    );
    await expandToolbar();
    expect(".o-select-highlight").toHaveCount(1);
    expect(".o_text_highlight").toHaveCount(1);
    await click(".o-we-toolbar .o-select-highlight");
    await waitFor("button[title='Reset']");
    await click("button[title='Reset']");
    expect(".o_text_highlight").toHaveCount(0);
});

test("Similar adjacent highlights are merged", async () => {
    await setupEditor(
        `<p>
            <span class="o_text_highlight o_text_highlight_freehand_2" style="--text-highlight-width: 1px;">highlight</span><span class="o_text_highlight o_text_highlight_freehand_1">[highlight2]</span>
        </p>`,
        { config: { Plugins: [...MAIN_PLUGINS, HighlightPlugin] } }
    );
    await expandToolbar();
    expect(".o-select-highlight").toHaveCount(1);
    await contains(".o-we-toolbar .o-select-highlight").click();

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
            <span class="o_text_highlight o_text_highlight_freehand_2" style="--text-highlight-color: #E79C9C; --text-highlight-width: 2px;">highligh[t]<svg class="o_text_highlight_svg"></svg></span>
        </p>`,
        { config: { Plugins: [...MAIN_PLUGINS, HighlightPlugin] } }
    );
    await expandToolbar();
    const selectedHighlights = (editor) =>
        editor.shared.selection
            .getTargetedNodes()
            .map((n) => closestElement(n, ".o_text_highlight"))
            .filter(Boolean);
    expect("p>.o_text_highlight_freehand_2").toHaveCount(1);
    expect(selectedHighlights(editor)).toHaveLength(1);
    await contains(".o-we-toolbar .fa-eraser").click();
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
        { config: { Plugins: [...MAIN_PLUGINS, HighlightPlugin] } }
    );
    await expandToolbar();
    expect(".o-select-highlight").toHaveCount(1);
    expect(".o_text_highlight").toHaveCount(2);
    await contains(".o-we-toolbar .o-select-highlight").click();
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
