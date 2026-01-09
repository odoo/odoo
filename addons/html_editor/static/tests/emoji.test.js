import { describe, expect, test } from "@odoo/hoot";
import { click, press, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { loadBundle } from "@web/core/assets";
import { setupEditor } from "./_helpers/editor";
import { getContent } from "./_helpers/selection";
import { ensureDistinctHistoryStep, insertText, undo } from "./_helpers/user_actions";
import { expectElementCount } from "./_helpers/ui_expectations";

test.tags("desktop");
test("add an emoji with powerbox", async () => {
    const { el, editor } = await setupEditor("<p>ab[]</p>");
    await loadBundle("web.assets_emoji");

    await expectElementCount(".o-EmojiPicker", 0);
    expect(getContent(el)).toBe("<p>ab[]</p>");

    await insertText(editor, "/emoji");
    await press("enter");
    await expectElementCount(".o-EmojiPicker", 1);

    await click(".o-EmojiPicker .o-Emoji");
    expect(getContent(el)).toBe("<p>ab😀[]</p>");
});

test("click on emoji command to open emoji picker", async () => {
    const { el, editor } = await setupEditor("<p>ab[]</p>");
    await loadBundle("web.assets_emoji");

    await expectElementCount(".o-EmojiPicker", 0);
    expect(getContent(el)).toBe("<p>ab[]</p>");

    await insertText(editor, "/emoji");
    await animationFrame();
    await click(".active .o-we-command-name");
    await expectElementCount(".o-EmojiPicker", 1);
});

test.tags("desktop");
test("undo an emoji", async () => {
    const { el, editor } = await setupEditor("<p>ab[]</p>");
    await loadBundle("web.assets_emoji");
    expect(getContent(el)).toBe("<p>ab[]</p>");

    await insertText(editor, "test");
    await ensureDistinctHistoryStep();
    await insertText(editor, "/emoji");
    await press("enter");
    await waitFor(".o-EmojiPicker", { timeout: 1000 });
    await click(".o-EmojiPicker .o-Emoji");
    expect(getContent(el)).toBe("<p>abtest😀[]</p>");

    undo(editor);
    expect(getContent(el)).toBe("<p>abtest[]</p>");
});

test("close emoji picker with escape", async () => {
    const { el, editor } = await setupEditor("<p>ab[]</p>");
    await loadBundle("web.assets_emoji");
    expect(getContent(el)).toBe("<p>ab[]</p>");

    await insertText(editor, "/emoji");
    await press("enter");
    await waitFor(".o-EmojiPicker", { timeout: 1000 });
    expect(getContent(el)).toBe("<p>ab</p>");

    await press("escape");
    await animationFrame();
    await expectElementCount(".o-EmojiPicker", 0);
    expect(getContent(el)).toBe("<p>ab[]</p>");
});

describe("Emoji list picker", () => {
    test("should open emoji list picker on typing : followed by two chars", async () => {
        const { editor } = await setupEditor("<p>[]<br></p>");
        await loadBundle("web.assets_emoji");
        await insertText(editor, ":");
        await animationFrame();
        expect(".o-we-SuggestionList").toHaveCount(0);
        await insertText(editor, "w");
        await animationFrame();
        expect(".o-we-SuggestionList").toHaveCount(0);
        await insertText(editor, "a");
        await expectElementCount(".o-we-SuggestionList", 1);
    });

    test("should insert emoji using emoji list picker", async () => {
        const { el, editor } = await setupEditor("<p>[]<br></p>");
        await loadBundle("web.assets_emoji");
        await insertText(editor, ":wave");
        await expectElementCount(".o-we-SuggestionList", 1);
        await animationFrame();
        press("enter");
        expect(getContent(el)).toBe("<p>👋[]</p>");
        await expectElementCount(".o-we-SuggestionList", 0);
        await insertText(editor, ":burger");
        await expectElementCount(".o-we-SuggestionList", 1);
        await animationFrame();
        await click(".o-we-SuggestionList > div");
        expect(getContent(el)).toBe("<p>👋🍔[]</p>");
    });

    test("should close emoji list picker on escape", async () => {
        const { editor } = await setupEditor("<p>[]<br></p>");
        await loadBundle("web.assets_emoji");
        await insertText(editor, ":wave");
        await expectElementCount(".o-we-SuggestionList", 1);
        press("escape");
        await expectElementCount(".o-we-SuggestionList", 0);
    });
});
