/* @odoo-module */

import {
    afterNextRender,
    click,
    insertText,
    start,
    startServer,
} from "@mail/../tests/helpers/test_utils";
import { EMOJI_PER_ROW } from "@mail/new/emoji_picker/emoji_picker";

import { triggerHotkey } from "@web/../tests/helpers/utils";

QUnit.module("emoji");

QUnit.test("search emoji from keywords", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await insertText("input[placeholder='Search for an emoji']", "mexican");
    assert.containsOnce($, ".o-mail-Emoji:contains(🌮)");
});

QUnit.test("search emoji from keywords with special regex character", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await insertText("input[placeholder='Search for an emoji']", "(blood");
    assert.containsOnce($, ".o-mail-Emoji:contains(🆎)");
});

QUnit.test("Press Escape in emoji picker closes the emoji picker", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await afterNextRender(() => triggerHotkey("Escape"));
    assert.containsNone($, ".o-mail-EmojiPicker");
});

QUnit.test("Basic keyboard navigation", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    assert.containsOnce($, ".o-mail-EmojiPicker-content .o-mail-Emoji[data-index=0].bg-300"); // bg-300 means active
    await afterNextRender(() => triggerHotkey("ArrowRight"));
    assert.containsOnce($, ".o-mail-EmojiPicker-content .o-mail-Emoji[data-index=1].bg-300");
    await afterNextRender(() => triggerHotkey("ArrowDown"));
    assert.containsOnce(
        $,
        `.o-mail-EmojiPicker-content .o-mail-Emoji[data-index=${EMOJI_PER_ROW + 1}].bg-300`
    );
    await afterNextRender(() => triggerHotkey("ArrowLeft"));
    assert.containsOnce(
        $,
        `.o-mail-EmojiPicker-content .o-mail-Emoji[data-index=${EMOJI_PER_ROW}].bg-300`
    );
    await afterNextRender(() => triggerHotkey("ArrowUp"));
    assert.containsOnce($, ".o-mail-EmojiPicker-content .o-mail-Emoji[data-index=0].bg-300");
    const codepoints = $(".o-mail-EmojiPicker-content .o-mail-Emoji[data-index=0].bg-300").data(
        "codepoints"
    );
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.strictEqual($(".o-mail-Composer-input").val(), codepoints);
});
