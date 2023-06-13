/* @odoo-module */

import { EMOJI_PER_ROW } from "@web/core/emoji_picker/emoji_picker";
import {
    afterNextRender,
    click,
    insertText,
    start,
    startServer,
} from "@mail/../tests/helpers/test_utils";

import { triggerHotkey } from "@web/../tests/helpers/utils";

QUnit.module("emoji");

QUnit.test("search emoji from keywords", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await insertText("input[placeholder='Search for an emoji']", "mexican");
    assert.containsOnce($, ".o-Emoji:contains(🌮)");
});

QUnit.test("search emoji from keywords should be case insensitive", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await insertText("input[placeholder='Search for an emoji']", "ok");
    assert.containsOnce($, ".o-Emoji:contains(🆗)"); // all search terms are uppercase OK
});

QUnit.test("search emoji from keywords with special regex character", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await insertText("input[placeholder='Search for an emoji']", "(blood");
    assert.containsOnce($, ".o-Emoji:contains(🆎)");
});

QUnit.test("Press Escape in emoji picker closes the emoji picker", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await afterNextRender(() => triggerHotkey("Escape"));
    assert.containsNone($, ".o-EmojiPicker");
});

QUnit.test("Basic keyboard navigation", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    assert.containsOnce($, ".o-EmojiPicker-content .o-Emoji[data-index=0].bg-200"); // bg-200 means active
    await afterNextRender(() => triggerHotkey("ArrowRight"));
    assert.containsOnce($, ".o-EmojiPicker-content .o-Emoji[data-index=1].bg-200");
    await afterNextRender(() => triggerHotkey("ArrowDown"));
    assert.containsOnce(
        $,
        `.o-EmojiPicker-content .o-Emoji[data-index=${EMOJI_PER_ROW + 1}].bg-200`
    );
    await afterNextRender(() => triggerHotkey("ArrowLeft"));
    assert.containsOnce(
        $,
        `.o-EmojiPicker-content .o-Emoji[data-index=${EMOJI_PER_ROW}].bg-200`
    );
    await afterNextRender(() => triggerHotkey("ArrowUp"));
    assert.containsOnce($, ".o-EmojiPicker-content .o-Emoji[data-index=0].bg-200");
    const codepoints = $(".o-EmojiPicker-content .o-Emoji[data-index=0].bg-200").data(
        "codepoints"
    );
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.strictEqual($(".o-mail-Composer-input").val(), codepoints);
});

QUnit.test("recent category (basic)", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    assert.containsNone($, ".o-EmojiPicker-navbar [title='Frequently used']");
    await click(".o-EmojiPicker-content .o-Emoji:contains(😀)");
    await click("button[aria-label='Emojis']");
    assert.containsOnce($, ".o-EmojiPicker-navbar [title='Frequently used']");
    assert.containsOnce(
        $,
        "span:contains(Frequently used) ~ .o-Emoji:contains(😀) ~ span:contains(Smileys & Emotion)"
    );
});

QUnit.test("emoji usage amount orders frequent emojis", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await click(".o-EmojiPicker-content .o-Emoji:contains(😀)");
    await click("button[aria-label='Emojis']");
    await click(".o-EmojiPicker-content .o-Emoji:contains(👽)");
    await click("button[aria-label='Emojis']");
    await click(".o-EmojiPicker-content .o-Emoji:contains(👽)");
    await click("button[aria-label='Emojis']");
    assert.containsOnce(
        $,
        "span:contains(Frequently used) ~ .o-Emoji:contains(😀) ~ span:contains(Smileys & Emotion)"
    );
    assert.containsOnce(
        $,
        "span:contains(Frequently used) ~ .o-Emoji:contains(👽) ~ span:contains(Smileys & Emotion)"
    );
    assert.containsOnce(
        $,
        "span:contains(Frequently used) ~ .o-Emoji:contains(👽) ~ .o-Emoji:contains(😀) ~ span:contains(Smileys & Emotion)"
    );
});

QUnit.test("posting :wink: in message should impact recent", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", ":wink:");
    await click(".o-mail-Composer button[aria-label='Send']");
    await click("button[aria-label='Emojis']");
    assert.containsOnce(
        $,
        "span:contains(Frequently used) ~ .o-Emoji:contains(😉) ~ span:contains(Smileys & Emotion)"
    );
});

QUnit.test("posting :snowman: in message should impact recent", async (assert) => {
    // the snowman emoji is composed of two codepoints, making it a corner case
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", ":snowman:");
    await click(".o-mail-Composer button[aria-label='Send']");
    await click("button[aria-label='Emojis']");
    assert.containsOnce(
        $,
        "span:contains(Frequently used) ~ .o-Emoji:contains(☃️) ~ span:contains(Smileys & Emotion)"
    );
});

QUnit.test("first category should be highlight by default", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    assert.containsOnce($, ".o-EmojiPicker-navbar .o-Emoji:eq(0).bg-300");
});

QUnit.test(
    "selecting an emoji while holding down the Shift key prevents the emoji picker from closing",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "" });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await click("button[aria-label='Emojis']");
        await afterNextRender(() =>
            $(".o-EmojiPicker-content .o-Emoji:contains(👺)")[0].dispatchEvent(
                new MouseEvent("click", { shiftKey: true })
            )
        );
        assert.containsOnce($, ".o-EmojiPicker");
        assert.strictEqual($(".o-mail-Composer-input").val(), "👺");
    }
);
