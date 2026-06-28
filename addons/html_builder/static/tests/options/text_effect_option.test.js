import { addBuilderPlugin, setupHTMLBuilder } from "@html_builder/../tests/helpers";
import { expect, test, describe } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { TextEffectPlugin } from "@html_builder/plugins/font/text_effect_plugin";
import { getTextEffectPresetHash } from "@html_builder/plugins/font/text_effect_util";
import {
    advanceTime,
    animationFrame,
    hover,
    press,
    queryOne,
    waitFor,
    waitForNone,
} from "@odoo/hoot-dom";
import { getContent, setSelection } from "@html_editor/../tests/_helpers/selection";

describe.current.tags("desktop");

test("apply preset", async () => {
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
    await contains(".o_text_effect_popover .dropdown-item:contains('Flat')").click();
    await waitForNone(".o_text_effect_popover");
    expect(`:iframe [data-text-effect*="flat"]`).toHaveStyle("text-shadow");
});

test("open applies blurred black by default", async () => {
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

    expect(".o_text_effect_popover").toHaveCount(1);
    expect(".o_text_effect_popover .active:contains('Blurred (Black)')").toHaveCount(1);
    expect(`:iframe [data-text-effect*="blurred_black"]`).toHaveStyle("text-shadow");
});

test("switch preset", async () => {
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
    await contains(".o_text_effect_popover .dropdown-item:contains('Flat')").click();
    await waitForNone(".o_text_effect_popover");
    expect(`:iframe [data-text-effect*="flat"]`).toHaveStyle("text-shadow");

    // Change text effect
    await contains(".o-select-text-effect").click();
    await contains(".o_text_effect_popover .dropdown-item:contains('Outline')").click();
    await waitForNone(".o_text_effect_popover");
    expect(`:iframe [data-text-effect*="outline"]`).toHaveStyle("-webkit-text-stroke");
});

test("remove", async () => {
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
    await contains(".o_text_effect_popover .dropdown-item:contains('Flat')").click();
    await waitForNone(".o_text_effect_popover");
    expect(`:iframe [data-text-effect*="flat"]`).toHaveStyle("text-shadow");

    // Remove text effect
    await contains(".o-select-text-effect").click();
    await contains(".o_text_effect_popover .dropdown-item:contains('No Shadow')").click();
    await waitForNone(".o_text_effect_popover");
    expect(":iframe [data-text-effect]").toHaveCount(0);
    expect(getContent(contentEl)).toBe("<p>[Text]</p>");
    expect(".o-select-text-effect").not.toHaveClass("active");
});

test("remove if empty", async () => {
    addBuilderPlugin(TextEffectPlugin);
    const { getEditor } = await setupHTMLBuilder(`<p><span data-text-effect="{}">Text</span></p>`);
    const cleanedEl = getEditor().getElContent();
    expect(cleanedEl.querySelector("[data-text-effect]")).toBe(null);
});

test("remove if no shadow or outline", async () => {
    addBuilderPlugin(TextEffectPlugin);
    const { getEditor } = await setupHTMLBuilder(
        `<p><span data-text-effect='{"preset":"custom","presetHash":"00000000"}'>Text</span></p>`
    );
    const cleanedEl = getEditor().getElContent();
    expect(cleanedEl.querySelector("[data-text-effect]")).toBe(null);
});

test("custom opens the option", async () => {
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
    await contains(".o_text_effect_popover .dropdown-item:contains('Custom')").click();
    expect(".o_text_effect_popover:contains('Text Shadow')").toHaveCount(1);
    expect(".o_text_effect_popover .dropdown-item").toHaveCount(0);
});

test("custom preset opens the option", async () => {
    addBuilderPlugin(TextEffectPlugin);
    const { getEditor } = await setupHTMLBuilder(
        `<p><span data-text-effect='{"preset":"custom","shadows":[{"shadowBlur":"4px"}]}'>Preset</span> Text</p>`
    );
    const p = await waitFor(":iframe p");
    const textNode = getEditor().editable.querySelector("p").childNodes[1];
    expect(":iframe p").toHaveCount(1);
    setSelection({
        anchorNode: textNode,
        anchorOffset: 1,
        focusNode: textNode,
        focusOffset: 5,
    });
    await contains(".oi-ellipsis-v").click();
    await contains(".o-select-text-effect").click();
    await contains(".o_text_effect_popover .dropdown-item:contains('Custom Shadow')").click();
    expect(".o_text_effect_popover:contains('Text Shadow')").toHaveCount(1);
    expect(".o_text_effect_popover .dropdown-item").toHaveCount(0);
    expect(p.querySelectorAll("[data-text-effect]")).toHaveLength(2);
    const textEffect = JSON.parse(p.querySelectorAll("[data-text-effect]")[1].dataset.textEffect);
    expect(textEffect).toEqual({
        preset: "custom",
        presetHash: getTextEffectPresetHash(textEffect),
        shadows: [
            {
                shadowBlur: "4px",
            },
        ],
    });
});

test("custom shadow hash is updated when editing text effect", async () => {
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
    await contains(".o_text_effect_popover .dropdown-item:contains('Custom')").click();
    let textEffect = JSON.parse(queryOne(":iframe [data-text-effect]").dataset.textEffect);
    const initialHash = textEffect.presetHash;
    expect(initialHash).toBe(getTextEffectPresetHash(textEffect));

    await contains(".o_text_effect_popover .o-hb-text-effect-add-shadow").click();
    await animationFrame();

    textEffect = JSON.parse(queryOne(":iframe [data-text-effect]").dataset.textEffect);
    expect(textEffect.presetHash).not.toBe(initialHash);
    expect(textEffect.presetHash).toBe(getTextEffectPresetHash(textEffect));
});

test("open option by default if custom", async () => {
    addBuilderPlugin(TextEffectPlugin);
    await setupHTMLBuilder(
        `<p><span data-text-effect='{"preset":"custom","shadows":[{"shadowBlur":"4px"}]}'>Text</span></p>`
    );
    const textEffectEl = await waitFor(":iframe [data-text-effect]");
    setSelection({
        anchorNode: textEffectEl.firstChild,
        anchorOffset: 0,
        focusNode: textEffectEl.firstChild,
        focusOffset: 4,
    });
    await contains(".oi-ellipsis-v").click();
    await contains(".o-select-text-effect").click();
    expect(".o_text_effect_popover:contains('Text Shadow')").toHaveCount(1);
    expect(".o_text_effect_popover .dropdown-item").toHaveCount(0);

    await contains(".o_text_effect_popover .oi-chevron-left").click();
    expect(".o_text_effect_popover .active:contains('Custom Shadow')").toHaveCount(1);
});

test("selecting part of a text effect applies preset on the full text effect", async () => {
    addBuilderPlugin(TextEffectPlugin);
    const { getEditor } = await setupHTMLBuilder(
        `<p><span data-text-effect='{"preset":"flat","shadows":[{"shadowBlur":"1px"}]}'>Text</span></p>`
    );
    const textEffectEl = await waitFor(":iframe [data-text-effect]");
    setSelection({
        anchorNode: textEffectEl.firstChild,
        anchorOffset: 1,
        focusNode: textEffectEl.firstChild,
        focusOffset: 3,
    });
    await contains(".oi-ellipsis-v").click();
    await contains(".o-select-text-effect").click();
    await contains(".o_text_effect_popover .dropdown-item:contains('Outline')").click();
    await waitForNone(".o_text_effect_popover");

    const textEffects = getEditor().editable.querySelectorAll("[data-text-effect]");
    expect(textEffects).toHaveLength(1);
    expect(textEffects[0].textContent).toBe("Text");
    expect(JSON.parse(textEffects[0].dataset.textEffect).preset).toBe("outline");
});

test("selecting multiple text effects shows no active preset", async () => {
    addBuilderPlugin(TextEffectPlugin);
    await setupHTMLBuilder(
        `<h1><span data-text-effect='{"preset":"flat","shadows":[{"shadowBlur":"1px"}]}'>first</span> <span data-text-effect='{"preset":"outline","outline":"2px"}'>second</span></h1>`
    );
    const h1 = await waitFor(":iframe h1");
    const textEffects = h1.querySelectorAll("[data-text-effect]");
    setSelection({
        anchorNode: textEffects[0].firstChild,
        anchorOffset: 1,
        focusNode: textEffects[1].firstChild,
        focusOffset: 3,
    });
    await contains(".oi-ellipsis-v").click();
    await contains(".o-select-text-effect").click();

    expect(".o_text_effect_popover .dropdown-item.active").toHaveCount(0);
});

test("preview applies on full selection and stopping preview restores initial state", async () => {
    addBuilderPlugin(TextEffectPlugin);
    const { getEditor } = await setupHTMLBuilder(
        `<h1>Start <span data-text-effect='{"preset":"flat","shadows":[{"shadowBlur":"1px"}]}'>middle</span> end</h1>`
    );
    const h1 = await waitFor(":iframe h1");
    setSelection({
        anchorNode: h1.firstChild,
        anchorOffset: 2,
        focusNode: h1.lastChild,
        focusOffset: 3,
    });
    await contains(".oi-ellipsis-v").click();
    await contains(".o-select-text-effect").click();
    await hover(
        ".o_text_effect_popover .dropdown-item:contains('Outline') .o-hb-text-effect-preset"
    );
    await animationFrame();

    let textEffects = getEditor().editable.querySelectorAll("[data-text-effect]");
    expect(textEffects).toHaveLength(1);
    expect(textEffects[0].textContent).toBe("art middle en");
    expect(JSON.parse(textEffects[0].dataset.textEffect).preset).toBe("outline");

    await hover(":iframe h1");
    await animationFrame();

    textEffects = getEditor().editable.querySelectorAll("[data-text-effect]");
    expect(textEffects).toHaveLength(1);
    expect(textEffects[0].textContent).toBe("middle");
    expect(JSON.parse(textEffects[0].dataset.textEffect)).toEqual({
        preset: "flat",
        shadows: [{ shadowBlur: "1px" }],
    });
    expect(getEditor().editable.querySelector("h1").textContent).toBe("Start middle end");
});

test("add multiple shadows on an element", async () => {
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
    await contains(".o_text_effect_popover .dropdown-item:contains('Custom')").click();
    expect(".o_text_effect_popover [data-label='Color']").toHaveCount(1);
    await contains(".o_text_effect_popover .o-hb-text-effect-add-shadow").click();
    await contains(".o_text_effect_popover .o-hb-text-effect-add-shadow").click();
    await animationFrame();
    expect(".o_text_effect_popover [data-label='Color']").toHaveCount(3);
    expect(
        JSON.parse(queryOne(":iframe [data-text-effect]").dataset.textEffect).shadows
    ).toHaveLength(3);
});

test("delete one specific shadow on an element", async () => {
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
    await contains(".o_text_effect_popover .dropdown-item:contains('Custom')").click();
    await contains(".o_text_effect_popover .o-hb-text-effect-add-shadow").click();
    await contains(".o_text_effect_popover .o-hb-text-effect-add-shadow").click();
    await animationFrame();

    const nthShadowBlurSelector = (index) =>
        `.o-hb-text-effect-shadow:nth-child(${index + 1}) .hb-row[data-label='Blur'] input`;
    await contains(nthShadowBlurSelector(1)).edit(5);
    await contains(nthShadowBlurSelector(2)).edit(6);
    await contains(nthShadowBlurSelector(3)).edit(7);

    await animationFrame();
    await contains(".o-hb-text-effect-shadow:nth-child(3) .fa-trash").click();
    await animationFrame();

    expect(".o_text_effect_popover [data-label='Color']").toHaveCount(2);
    expect(
        JSON.parse(queryOne(":iframe [data-text-effect]").dataset.textEffect).shadows
    ).toHaveLength(2);

    expect(nthShadowBlurSelector(1)).toHaveValue(5);
    expect(nthShadowBlurSelector(2)).toHaveValue(7);
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
        await contains(".o_text_effect_popover .dropdown-item:contains('Flat')").click();
        await waitForNone(".o_text_effect_popover");
        expect(`:iframe [data-text-effect*="flat"]`).toHaveStyle("text-shadow");

        // Apply font size
        await contains(":iframe input").click();
        await press("5");
        await press("0");
        await advanceTime(200);
        await animationFrame();
        await waitFor(":iframe span[style] span[data-text-effect]");
        const fontSizeEl = queryOne(`:iframe span[style*="font-size"]`);
        const fontSizeProperty = fontSizeEl.style.fontSize; // Current representation of 50px

        // Remove text effect
        await contains(".o-select-text-effect").click();
        await contains(".o_text_effect_popover .dropdown-item:contains('No Shadow')").click();
        await waitForNone(".o_text_effect_popover");
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
        await contains(".o_text_effect_popover .dropdown-item:contains('Flat')").click();
        await waitForNone(".o_text_effect_popover");
        expect(`:iframe [data-text-effect*="flat"]`).toHaveStyle("text-shadow");
        await waitFor(":iframe span[style] span[data-text-effect]");

        // Remove text effect
        await contains(".o-select-text-effect").click();
        await contains(".o_text_effect_popover .dropdown-item:contains('No Shadow')").click();
        await waitForNone(".o_text_effect_popover");
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
        await contains(".o_text_effect_popover .dropdown-item:contains('Flat')").click();
        await waitForNone(".o_text_effect_popover");
        expect(`:iframe [data-text-effect*="flat"]`).toHaveStyle("text-shadow");

        // Apply bold
        await contains(".fa-bold").click();
        await waitFor(":iframe strong");

        // Remove bold
        await contains(".fa-bold").click();
        await waitForNone(":iframe strong");
        expect(`:iframe [data-text-effect*="flat"]`).toHaveStyle("text-shadow");
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
        await contains(".o_text_effect_popover .dropdown-item:contains('Flat')").click();
        await waitForNone(".o_text_effect_popover");
        expect(`:iframe [data-text-effect*="flat"]`).toHaveStyle("text-shadow");
        await waitFor(":iframe strong span[data-text-effect]");

        // Remove bold
        await contains(".fa-bold").click();
        await waitForNone(":iframe strong");
        expect(`:iframe [data-text-effect*="flat"]`).toHaveStyle("text-shadow");
    });
});
