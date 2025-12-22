import { expect, test } from "@odoo/hoot";
import { click, press, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { loadBundle } from "@web/core/assets";
import { setupEditor } from "./_helpers/editor";
import { getContent } from "./_helpers/selection";
import { insertText, undo } from "./_helpers/user_actions";
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
