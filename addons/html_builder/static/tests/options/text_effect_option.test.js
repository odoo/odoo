import { addBuilderPlugin, setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { expect, test, describe } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { TextEffectPlugin } from "@html_builder/plugins/font/text_effect_plugin";
import { advanceTime, animationFrame, press, queryOne, waitFor, waitForNone } from "@odoo/hoot-dom";
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

describe("nesting", () => {
    test("apply font size on text effect, then remove text effect should keep font size", async () => {
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
        await waitFor(":iframe span[data-text-effect]");
        await contains(".o-select-text-effect").click();
        await waitForNone(".o_text_effect_popover");

        // Apply font size
        await contains(":iframe input").click();
        await press("5");
        await press("0");
        await advanceTime(200);
        await animationFrame();
        await waitFor(":iframe span[data-text-effect] span[style]");
        const fontSizeEl = queryOne(":iframe span[data-text-effect] span[style]");
        const fontSizeProperty = fontSizeEl.style.fontSize; // Current representation of 50px

        // Remove text effect
        await contains(".o-select-text-effect").click();
        await contains(".fa-trash").click();
        expect(getContent(contentEl)).toBe(
            `<p><span class="o_rfs" style="font-size: ${fontSizeProperty};">[Text]</span></p>`
        );
    });
    test("apply text effect on font size, then remove text effect should keep font size", async () => {
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

        // Apply font size
        await contains(":iframe input").click();
        await press("5");
        await press("0");
        await advanceTime(200);
        await animationFrame();
        await waitFor(":iframe span[style]");
        const fontSizeEl = queryOne(":iframe span[style]");
        const fontSizeProperty = fontSizeEl.style.fontSize; // Current representation of 50px

        // Apply text effect
        await contains(".o-select-text-effect").click();
        await contains(`[data-action-id="setTextEffect"][data-action-value*="sharp"]`).click();
        expect(`:iframe [data-text-effect*="sharp"]`).toHaveStyle("text-shadow");
        await waitFor(":iframe span[style] span[data-text-effect]");

        // Remove text effect
        await contains(".fa-trash").click();
        expect(getContent(contentEl)).toBe(
            `<p><span class="o_rfs" style="font-size: ${fontSizeProperty};">[Text]</span></p>`
        );
    });

    test("apply bold on text effect, then remove bold should keep text effect", async () => {
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
        await waitFor(":iframe span[data-text-effect]");
        await contains(".o-select-text-effect").click();
        await waitForNone(".o_text_effect_popover");

        // Apply bold
        await contains(".fa-bold").click();
        await waitFor(":iframe strong");

        // Remove bold
        await contains(".fa-bold").click();
        await waitForNone(":iframe strong");
        expect(`:iframe [data-text-effect*="sharp"]`).toHaveStyle("text-shadow");
    });

    test("apply text effect on bold, then remove bold should keep text effect", async () => {
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

        // Apply bold
        await contains(".fa-bold").click();
        await waitFor(":iframe strong");

        // Apply text effect
        await contains(".oi-ellipsis-v").click();
        await contains(".o-select-text-effect").click();
        await contains(`[data-action-id="setTextEffect"][data-action-value*="sharp"]`).click();
        expect(`:iframe [data-text-effect*="sharp"]`).toHaveStyle("text-shadow");
        await waitFor(":iframe strong span[data-text-effect]");

        // Remove bold
        await contains(".fa-bold").click();
        await waitForNone(":iframe strong");
        expect(`:iframe [data-text-effect*="sharp"]`).toHaveStyle("text-shadow");
    });
});
