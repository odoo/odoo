import { addBuilderPlugin, setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { expect, test, describe } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { TextEffectPlugin } from "@html_builder/plugins/font/text_effect_plugin";
import { press, waitFor } from "@odoo/hoot-dom";
import { getContent, setSelection } from "@html_editor/../tests/_helpers/selection";

describe.current.tags("desktop");

test("apply text effect", async () => {
    addBuilderPlugin(TextEffectPlugin);
    await setupHTMLBuilder(`<p>Text</p>`);
    const p = await waitFor(":iframe p");
    expect(":iframe p").toHaveCount(1);
    setSelection({
        anchorNode: p,
        anchorOffset: 0,
        focusNode: p,
        focusOffset: 1,
    });
    await contains(".oi-ellipsis-v").click();
    await contains(".o-select-text-effect").click();
    await contains(`[data-action-id="setTextEffect"][data-action-value*="sharp"]`).click();
    expect(`:iframe [data-text-effect*="sharp"]`).toHaveStyle("text-shadow");
});

test("change text effect", async () => {
    addBuilderPlugin(TextEffectPlugin);
    await setupHTMLBuilder(`<p>Text</p>`);
    const p = await waitFor(":iframe p");
    expect(":iframe p").toHaveCount(1);
    setSelection({
        anchorNode: p,
        anchorOffset: 0,
        focusNode: p,
        focusOffset: 1,
    });
    await contains(".oi-ellipsis-v").click();
    await contains(".o-select-text-effect").click();
    await contains(`[data-action-id="setTextEffect"][data-action-value*="sharp"]`).click();
    expect(`:iframe [data-text-effect*="sharp"]`).toHaveStyle("text-shadow");

    // Change text effect
    await contains(".o_text_effect_popover .btn-secondary").click();
    await contains(`[data-action-id="setTextEffect"][data-action-value*="ribbon"]`).click();
    expect(`:iframe [data-text-effect*="ribbon"]`).toHaveStyle("text-shadow");
    expect(`:iframe [data-text-effect*="ribbon"]`).toHaveStyle("transform");
    expect(`:iframe [data-text-effect*="ribbon"]`).toHaveStyle("-webkit-text-stroke");
});

test("remove text effect", async () => {
    addBuilderPlugin(TextEffectPlugin);
    const { contentEl } = await setupHTMLBuilder(`<p>Text</p>`);
    const p = await waitFor(":iframe p");
    expect(":iframe p").toHaveCount(1);
    setSelection({
        anchorNode: p,
        anchorOffset: 0,
        focusNode: p,
        focusOffset: 1,
    });
    await contains(".oi-ellipsis-v").click();
    await contains(".o-select-text-effect").click();
    await contains(`[data-action-id="setTextEffect"][data-action-value*="sharp"]`).click();
    expect(`:iframe [data-text-effect*="sharp"]`).toHaveStyle("text-shadow");

    // Remove text effect
    await contains(".fa-trash").click();
    expect(getContent(contentEl)).toBe("<p>[]Text</p>");
});

test("remove effect if empty", async () => {
    addBuilderPlugin(TextEffectPlugin);
    const { contentEl } = await setupHTMLBuilder(`<p>Text</p>`);
    const p = await waitFor(":iframe p");
    expect(":iframe p").toHaveCount(1);
    setSelection({
        anchorNode: p,
        anchorOffset: 0,
        focusNode: p,
        focusOffset: 1,
    });
    await contains(".oi-ellipsis-v").click();
    await contains(".o-select-text-effect").click();
    await press("escape");
    expect(getContent(contentEl)).toBe("<p>[Text]</p>");
});
