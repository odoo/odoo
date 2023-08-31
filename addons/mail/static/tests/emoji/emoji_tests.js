/* @odoo-module */

import { EMOJI_PER_ROW } from "@web/core/emoji_picker/emoji_picker";
import { click, contains, insertText, start, startServer } from "@mail/../tests/helpers/test_utils";

import { triggerHotkey } from "@web/../tests/helpers/utils";

QUnit.module("emoji");

QUnit.test("search emoji from keywords", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await insertText("input[placeholder='Search for an emoji']", "mexican");
    await contains(".o-Emoji", { text: "🌮" });
});

QUnit.test("search emoji from keywords should be case insensitive", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await insertText("input[placeholder='Search for an emoji']", "ok");
    await contains(".o-Emoji", { text: "🆗" }); // all search terms are uppercase OK
});

QUnit.test("search emoji from keywords with special regex character", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await insertText("input[placeholder='Search for an emoji']", "(blood");
    await contains(".o-Emoji", { text: "🆎" });
});

QUnit.test("Press Escape in emoji picker closes the emoji picker", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    triggerHotkey("Escape");
    await contains(".o-EmojiPicker", { count: 0 });
});

QUnit.test("Basic keyboard navigation", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await contains(".o-EmojiPicker-content .o-Emoji[data-index=0].bg-200"); // bg-200 means active
    triggerHotkey("ArrowRight");
    await contains(".o-EmojiPicker-content .o-Emoji[data-index=1].bg-200");
    triggerHotkey("ArrowDown");
    await contains(`.o-EmojiPicker-content .o-Emoji[data-index=${EMOJI_PER_ROW + 1}].bg-200`);
    triggerHotkey("ArrowLeft");
    await contains(`.o-EmojiPicker-content .o-Emoji[data-index=${EMOJI_PER_ROW}].bg-200`);
    triggerHotkey("ArrowUp");
    await contains(".o-EmojiPicker-content .o-Emoji[data-index=0].bg-200");
    const codepoints = $(".o-EmojiPicker-content .o-Emoji[data-index=0].bg-200").data("codepoints");
    triggerHotkey("Enter");
    await contains(".o-EmojiPicker", { count: 0 });
    await contains(".o-mail-Composer-input", { value: codepoints });
});

QUnit.test("recent category (basic)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await contains(".o-EmojiPicker-navbar [title='Frequently used']", { count: 0 });
    await click(".o-EmojiPicker-content .o-Emoji", { text: "😀" });
    await click("button[aria-label='Emojis']");
    await contains(".o-EmojiPicker-navbar [title='Frequently used']");
    await contains(
        "span:contains(Frequently used) ~ .o-Emoji:contains(😀) ~ span:contains(Smileys & Emotion)"
    );
});

QUnit.test("emoji usage amount orders frequent emojis", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await click(".o-EmojiPicker-content .o-Emoji", { text: "😀" });
    await click("button[aria-label='Emojis']");
    await click(".o-EmojiPicker-content .o-Emoji", { text: "👽" });
    await click("button[aria-label='Emojis']");
    await click(".o-EmojiPicker-content .o-Emoji", { text: "👽" });
    await click("button[aria-label='Emojis']");
    await contains(
        "span:contains(Frequently used) ~ .o-Emoji:contains(😀) ~ span:contains(Smileys & Emotion)"
    );
    await contains(
        "span:contains(Frequently used) ~ .o-Emoji:contains(👽) ~ span:contains(Smileys & Emotion)"
    );
    await contains(
        "span:contains(Frequently used) ~ .o-Emoji:contains(👽) ~ .o-Emoji:contains(😀) ~ span:contains(Smileys & Emotion)"
    );
});

QUnit.test("posting :wink: in message should impact recent", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", ":wink:");
    await click(".o-mail-Composer-send:not(:disabled)");
    await click("button[aria-label='Emojis']");
    await contains(
        "span:contains(Frequently used) ~ .o-Emoji:contains(😉) ~ span:contains(Smileys & Emotion)"
    );
});

QUnit.test("posting :snowman: in message should impact recent", async () => {
    // the snowman emoji is composed of two codepoints, making it a corner case
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", ":snowman:");
    await click(".o-mail-Composer-send:not(:disabled)");
    await click("button[aria-label='Emojis']");
    await contains(
        "span:contains(Frequently used) ~ .o-Emoji:contains(☃️) ~ span:contains(Smileys & Emotion)"
    );
});

QUnit.test("first category should be highlighted by default", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await contains(".o-EmojiPicker-navbar .o-Emoji:eq(0).bg-300");
});

QUnit.test(
    "selecting an emoji while holding down the Shift key prevents the emoji picker from closing",
    async () => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "" });
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await click("button[aria-label='Emojis']");
        (await contains(".o-EmojiPicker-content .o-Emoji:contains(👺)"))[0].dispatchEvent(
            new MouseEvent("click", { shiftKey: true })
        );
        await contains(".o-EmojiPicker-navbar [title='Frequently used']");
        await contains(".o-EmojiPicker");
        await contains(".o-mail-Composer-input", { value: "👺" });
    }
);
