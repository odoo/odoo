import {
    addBuilderPlugin,
    openEffectsSection,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { expect, test, describe } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { TextEffectPlugin } from "@html_builder/plugins/font/text_effect_plugin";
import { EffectsPanelPlugin } from "@html_builder/plugins/effects/effects_plugin";
import { getTextEffectPresetHash } from "@html_builder/plugins/font/text_effect_util";
import {
    advanceTime,
    animationFrame,
    hover,
    press,
    queryAll,
    queryOne,
    waitFor,
    waitForNone,
} from "@odoo/hoot-dom";
import { getContent, setSelection } from "@html_editor/../tests/_helpers/selection";

describe.current.tags("desktop");

function addTextEffectPlugins() {
    addBuilderPlugin(TextEffectPlugin);
    addBuilderPlugin(EffectsPanelPlugin);
}

const preset = (name) => `.o-we-effects-panel .o_hb_text_effect_preset[title='${name}']`;

test("apply preset", async () => {
    addTextEffectPlugins();
    await setupHTMLBuilder(`<p>Text</p>`);
    const p = await waitFor(":iframe p");
    expect(":iframe p").toHaveCount(1);
    setSelection({
        anchorNode: p,
        anchorOffset: 0,
        focusNode: p,
        focusOffset: 1,
    });
    await contains("[data-icon='more_vert']").click();
    await openEffectsSection("textEffect");
    await contains(preset("Flat")).click();
    await animationFrame();
    expect(`:iframe [data-text-effect*="flat"]`).toHaveStyle("text-shadow");
});

test("opening the panel applies nothing", async () => {
    addTextEffectPlugins();
    await setupHTMLBuilder(`<p>Text</p>`);
    const p = await waitFor(":iframe p");
    setSelection({
        anchorNode: p,
        anchorOffset: 0,
        focusNode: p,
        focusOffset: 1,
    });
    await contains("[data-icon='more_vert']").click();
    await openEffectsSection("textEffect");

    expect(".o-we-effects-panel .o_hb_text_effect_preset").toHaveCount(6);
    expect(".o-we-effects-panel .o_hb_text_effect_preset.active").toHaveCount(0);
    expect(":iframe [data-text-effect]").toHaveCount(0);
});

test("switch preset", async () => {
    addTextEffectPlugins();
    await setupHTMLBuilder(`<p>Text</p>`);
    const p = await waitFor(":iframe p");
    expect(":iframe p").toHaveCount(1);
    setSelection({
        anchorNode: p,
        anchorOffset: 0,
        focusNode: p,
        focusOffset: 1,
    });
    await contains("[data-icon='more_vert']").click();
    await openEffectsSection("textEffect");
    await contains(preset("Flat")).click();
    await animationFrame();
    expect(`:iframe [data-text-effect*="flat"]`).toHaveStyle("text-shadow");

    // Change text effect
    await openEffectsSection("textEffect");
    await contains(preset("Outline")).click();
    await animationFrame();
    expect(`:iframe [data-text-effect*="outline"]`).toHaveStyle("-webkit-text-stroke");
});

test("remove", async () => {
    addTextEffectPlugins();
    const { contentEl } = await setupHTMLBuilder(`<p>Text</p>`);
    const p = await waitFor(":iframe p");
    expect(":iframe p").toHaveCount(1);
    setSelection({
        anchorNode: p,
        anchorOffset: 0,
        focusNode: p,
        focusOffset: 1,
    });
    await contains("[data-icon='more_vert']").click();
    await openEffectsSection("textEffect");
    await contains(preset("Flat")).click();
    await animationFrame();
    expect(`:iframe [data-text-effect*="flat"]`).toHaveStyle("text-shadow");

    // Remove text effect
    await openEffectsSection("textEffect");
    await contains(preset("No Shadow")).click();
    await animationFrame();
    expect(":iframe [data-text-effect]").toHaveCount(0);
    expect(getContent(contentEl)).toBe("<p>[Text]</p>");
    // The summary of a section shows once it is closed.
    await contains(".o-we-effects-section[data-section='textEffect'] .o-we-effects-section-toggle").click();
    expect(
        ".o-we-effects-section[data-section='textEffect'] .o-we-effects-section-summary"
    ).toHaveText("None");
});

test("remove if empty", async () => {
    addTextEffectPlugins();
    const { getEditor } = await setupHTMLBuilder(`<p><span data-text-effect="{}">Text</span></p>`);
    const cleanedEl = getEditor().getElContent();
    expect(cleanedEl.querySelector("[data-text-effect]")).toBe(null);
});

test("remove if no shadow or outline", async () => {
    addTextEffectPlugins();
    const { getEditor } = await setupHTMLBuilder(
        `<p><span data-text-effect='{"preset":"custom","presetHash":"00000000"}'>Text</span></p>`
    );
    const cleanedEl = getEditor().getElContent();
    expect(cleanedEl.querySelector("[data-text-effect]")).toBe(null);
});

test("presets and shadows are on the same page", async () => {
    addTextEffectPlugins();
    await setupHTMLBuilder(`<p>Text</p>`);
    const p = await waitFor(":iframe p");
    setSelection({
        anchorNode: p,
        anchorOffset: 0,
        focusNode: p,
        focusOffset: 1,
    });
    await contains("[data-icon='more_vert']").click();
    await openEffectsSection("textEffect");
    await contains(preset("Glow")).click();
    await animationFrame();
    expect(preset("Glow")).toHaveClass("active");
    expect(".o-we-effects-panel .o_hb_text_effect_shadow").toHaveCount(3);
    expect(".o-we-effects-section[data-section='textEffect'] .o-we-effects-section-summary").toHaveCount(0);
    await contains(".o-we-effects-section[data-section='textEffect'] .o-we-effects-section-toggle").click();
    expect(".o-we-effects-section[data-section='textEffect'] .o-we-effects-section-summary").toHaveText(
        "Glow"
    );
});

test("editing a preset makes it a custom effect, which becomes the active preset", async () => {
    addTextEffectPlugins();
    await setupHTMLBuilder(`<p>Text</p>`);
    const p = await waitFor(":iframe p");
    setSelection({
        anchorNode: p,
        anchorOffset: 0,
        focusNode: p,
        focusOffset: 1,
    });
    await expandToolbar();
    await openEffectsSection("textEffect");
    await contains(preset("Glow")).click();
    await animationFrame();
    expect(preset("Custom Shadow")).toHaveCount(0);

    // The blur is the third number of a shadow row.
    await contains(queryAll(".o_hb_text_effect_shadow")[0].querySelectorAll("input")[2]).edit(5);
    await animationFrame();
    const textEffect = JSON.parse(queryOne(":iframe [data-text-effect]").dataset.textEffect);
    expect(textEffect.preset).toBe("custom");
    expect(textEffect.presetHash).toBe(getTextEffectPresetHash(textEffect));
    expect(preset("Glow")).not.toHaveClass("active");
    expect(preset("Custom Shadow")).toHaveCount(1);
    expect(preset("Custom Shadow")).toHaveClass("active");

    await contains(".o-we-effects-section[data-section='textEffect'] .o-we-effects-section-toggle").click();
    expect(".o-we-effects-section[data-section='textEffect'] .o-we-effects-section-summary").toHaveText(
        "Custom"
    );
});

test("a custom effect replaced by a preset stays offered", async () => {
    addTextEffectPlugins();
    await setupHTMLBuilder(`<p>Text</p>`);
    const p = await waitFor(":iframe p");
    setSelection({
        anchorNode: p,
        anchorOffset: 0,
        focusNode: p,
        focusOffset: 1,
    });
    await expandToolbar();
    await openEffectsSection("textEffect");
    await contains(preset("Glow")).click();
    await animationFrame();
    await contains(queryAll(".o_hb_text_effect_shadow")[0].querySelectorAll("input")[2]).edit(5);
    await animationFrame();
    const customEffect = JSON.parse(queryOne(":iframe [data-text-effect]").dataset.textEffect);

    await contains(preset("Flat")).click();
    await animationFrame();
    expect(preset("Flat")).toHaveClass("active");
    expect(preset("Custom Shadow")).toHaveCount(1);
    expect(preset("Custom Shadow")).not.toHaveClass("active");

    await contains(preset("Custom Shadow")).click();
    await animationFrame();
    expect(preset("Custom Shadow")).toHaveClass("active");
    expect(JSON.parse(queryOne(":iframe [data-text-effect]").dataset.textEffect)).toEqual(
        customEffect
    );
});

test("custom effects of the page are offered as presets", async () => {
    addTextEffectPlugins();
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
    await contains("[data-icon='more_vert']").click();
    await openEffectsSection("textEffect");
    await contains(preset("Custom Shadow")).click();
    await animationFrame();
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
    addTextEffectPlugins();
    await setupHTMLBuilder(`<p>Text</p>`);
    const p = await waitFor(":iframe p");
    expect(":iframe p").toHaveCount(1);
    setSelection({
        anchorNode: p,
        anchorOffset: 0,
        focusNode: p,
        focusOffset: 1,
    });
    await contains("[data-icon='more_vert']").click();
    await openEffectsSection("textEffect");
    await contains(".o-we-effects-panel .o_hb_text_effect_add_shadow").click();
    await animationFrame();
    let textEffect = JSON.parse(queryOne(":iframe [data-text-effect]").dataset.textEffect);
    const initialHash = textEffect.presetHash;
    expect(initialHash).toBe(getTextEffectPresetHash(textEffect));

    await contains(".o-we-effects-panel .o_hb_text_effect_add_shadow").click();
    await animationFrame();

    textEffect = JSON.parse(queryOne(":iframe [data-text-effect]").dataset.textEffect);
    expect(textEffect.presetHash).not.toBe(initialHash);
    expect(textEffect.presetHash).toBe(getTextEffectPresetHash(textEffect));
});

test("a custom effect shows its shadows and its preset", async () => {
    addTextEffectPlugins();
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
    await contains("[data-icon='more_vert']").click();
    await openEffectsSection("textEffect");
    expect(".o-we-effects-panel .o_hb_text_effect_shadow").toHaveCount(1);
    expect(preset("Custom Shadow")).toHaveClass("active");
});

test("selecting part of a text effect applies preset on the full text effect", async () => {
    addTextEffectPlugins();
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
    await contains("[data-icon='more_vert']").click();
    await openEffectsSection("textEffect");
    await contains(preset("Outline")).click();
    await animationFrame();

    const textEffects = getEditor().editable.querySelectorAll("[data-text-effect]");
    expect(textEffects).toHaveLength(1);
    expect(textEffects[0].textContent).toBe("Text");
    expect(JSON.parse(textEffects[0].dataset.textEffect).preset).toBe("outline");
});

test("selecting multiple text effects shows no active preset", async () => {
    addTextEffectPlugins();
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
    await contains("[data-icon='more_vert']").click();
    await openEffectsSection("textEffect");

    expect(".o-we-effects-panel .o_hb_text_effect_preset.active").toHaveCount(0);
});

test("preview applies on full selection and stopping preview restores initial state", async () => {
    addTextEffectPlugins();
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
    await contains("[data-icon='more_vert']").click();
    await openEffectsSection("textEffect");
    await hover(preset("Outline"));
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
    addTextEffectPlugins();
    await setupHTMLBuilder(`<p>Text</p>`);
    const p = await waitFor(":iframe p");
    expect(":iframe p").toHaveCount(1);
    setSelection({
        anchorNode: p,
        anchorOffset: 0,
        focusNode: p,
        focusOffset: 1,
    });
    await contains("[data-icon='more_vert']").click();
    await openEffectsSection("textEffect");
    expect(".o-we-effects-panel .o_hb_text_effect_shadow").toHaveCount(0);
    await contains(".o-we-effects-panel .o_hb_text_effect_add_shadow").click();
    await animationFrame();
    await contains(".o-we-effects-panel .o_hb_text_effect_add_shadow").click();
    await contains(".o-we-effects-panel .o_hb_text_effect_add_shadow").click();
    await animationFrame();
    expect(".o-we-effects-panel .o_hb_text_effect_shadow").toHaveCount(3);
    expect(
        JSON.parse(queryOne(":iframe [data-text-effect]").dataset.textEffect).shadows
    ).toHaveLength(3);
});

test("delete one specific shadow on an element", async () => {
    addTextEffectPlugins();
    await setupHTMLBuilder(`<p>Text</p>`);
    const p = await waitFor(":iframe p");
    expect(":iframe p").toHaveCount(1);
    setSelection({
        anchorNode: p,
        anchorOffset: 0,
        focusNode: p,
        focusOffset: 1,
    });
    await contains("[data-icon='more_vert']").click();
    await openEffectsSection("textEffect");
    await contains(".o-we-effects-panel .o_hb_text_effect_add_shadow").click();
    await animationFrame();
    await contains(".o-we-effects-panel .o_hb_text_effect_add_shadow").click();
    await contains(".o-we-effects-panel .o_hb_text_effect_add_shadow").click();
    await animationFrame();

    // The blur is the third number of a shadow row.
    const blurInput = (index) => queryAll(".o_hb_text_effect_shadow")[index].querySelectorAll("input")[2];
    await contains(blurInput(0)).edit(5);
    await contains(blurInput(1)).edit(6);
    await contains(blurInput(2)).edit(7);

    await animationFrame();
    await contains(queryAll(".o_hb_text_effect_shadow .o_hb_text_effect_remove_shadow")[1]).click();
    await animationFrame();

    expect(".o-we-effects-panel .o_hb_text_effect_shadow").toHaveCount(2);
    expect(
        JSON.parse(queryOne(":iframe [data-text-effect]").dataset.textEffect).shadows
    ).toHaveLength(2);

    expect(blurInput(0)).toHaveValue(5);
    expect(blurInput(1)).toHaveValue(7);
});

describe("nesting", () => {
    test("apply font size on text effect, then remove text effect should keep font size", async () => {
        addTextEffectPlugins();
        const { contentEl } = await setupHTMLBuilder(`<p>Text</p>`);
        const p = await waitFor(":iframe p");
        expect(":iframe p").toHaveCount(1);
        setSelection({
            anchorNode: p,
            anchorOffset: 0,
            focusNode: p,
            focusOffset: 1,
        });
        await contains("[data-icon='more_vert']").click();
        await openEffectsSection("textEffect");
        await contains(preset("Flat")).click();
        await animationFrame();
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
        await openEffectsSection("textEffect");
        await contains(preset("No Shadow")).click();
        await animationFrame();
        expect(getContent(contentEl)).toBe(
            `<p><span style="font-size: ${fontSizeProperty};" class="o_rfs">[Text]</span></p>`
        );
    });

    test("apply text effect on font size, then remove text effect should keep font size", async () => {
        addTextEffectPlugins();
        const { contentEl } = await setupHTMLBuilder(`<p>Text</p>`);
        const p = await waitFor(":iframe p");
        expect(":iframe p").toHaveCount(1);
        setSelection({
            anchorNode: p,
            anchorOffset: 0,
            focusNode: p,
            focusOffset: 1,
        });
        await contains("[data-icon='more_vert']").click();

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
        await openEffectsSection("textEffect");
        await contains(preset("Flat")).click();
        await animationFrame();
        expect(`:iframe [data-text-effect*="flat"]`).toHaveStyle("text-shadow");
        await waitFor(":iframe span[style] span[data-text-effect]");

        // Remove text effect
        await openEffectsSection("textEffect");
        await contains(preset("No Shadow")).click();
        await animationFrame();
        expect(getContent(contentEl)).toBe(
            `<p><span style="font-size: ${fontSizeProperty};" class="o_rfs">[Text]</span></p>`
        );
    });

    test("apply bold on text effect, then remove bold should keep text effect", async () => {
        addTextEffectPlugins();
        await setupHTMLBuilder(`<p>Text</p>`);
        const p = await waitFor(":iframe p");
        expect(":iframe p").toHaveCount(1);
        setSelection({
            anchorNode: p,
            anchorOffset: 0,
            focusNode: p,
            focusOffset: 1,
        });
        await contains("[data-icon='more_vert']").click();
        await openEffectsSection("textEffect");
        await contains(preset("Flat")).click();
        await animationFrame();
        expect(`:iframe [data-text-effect*="flat"]`).toHaveStyle("text-shadow");

        // Apply bold
        await contains("[data-icon='format_bold']").click();
        await waitFor(":iframe strong");

        // Remove bold
        await contains("[data-icon='format_bold']").click();
        await waitForNone(":iframe strong");
        expect(`:iframe [data-text-effect*="flat"]`).toHaveStyle("text-shadow");
    });

    test("apply text effect on bold, then remove bold should keep text effect", async () => {
        addTextEffectPlugins();
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
        await contains("[data-icon='format_bold']").click();
        await waitFor(":iframe strong");

        // Apply text effect
        await contains("[data-icon='more_vert']").click();
        await openEffectsSection("textEffect");
        await contains(preset("Flat")).click();
        await animationFrame();
        expect(`:iframe [data-text-effect*="flat"]`).toHaveStyle("text-shadow");
        await waitFor(":iframe strong span[data-text-effect]");

        // Remove bold
        await contains("[data-icon='format_bold']").click();
        await waitForNone(":iframe strong");
        expect(`:iframe [data-text-effect*="flat"]`).toHaveStyle("text-shadow");
    });
});
