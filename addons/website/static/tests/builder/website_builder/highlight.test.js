import { expect, test } from "@odoo/hoot";
import { click, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { setupEditor } from "@html_editor/../tests/_helpers/editor";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expandToolbar } from "@html_editor/../tests/_helpers/toolbar";
import { HighlightPlugin } from "@website/builder/plugins/highlight/highlight_plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { contains } from "@web/../tests/web_test_helpers";

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
