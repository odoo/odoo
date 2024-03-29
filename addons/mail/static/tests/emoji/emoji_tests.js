/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { EMOJI_PER_ROW } from "@web/core/emoji_picker/emoji_picker";
import { triggerHotkey } from "@web/../tests/helpers/utils";
import { click, contains, insertText } from "@web/../tests/utils";

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

QUnit.test("updating search emoji should scroll top", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await contains(".o-EmojiPicker-content", { scroll: 0 });
    await scroll(".o-EmojiPicker-content", 150);
    await insertText("input[placeholder='Search for an emoji']", "m");
    await contains(".o-EmojiPicker-content", { scroll: 0 });
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
    await contains(".o-EmojiPicker-content .o-Emoji[data-index='0'].o-active");
    triggerHotkey("ArrowRight");
    await contains(".o-EmojiPicker-content .o-Emoji[data-index='1'].o-active");
    triggerHotkey("ArrowDown");
    await contains(`.o-EmojiPicker-content .o-Emoji[data-index='${EMOJI_PER_ROW + 1}'].o-active`);
    triggerHotkey("ArrowLeft");
    await contains(`.o-EmojiPicker-content .o-Emoji[data-index='${EMOJI_PER_ROW}'].o-active`);
    triggerHotkey("ArrowUp");
    await contains(".o-EmojiPicker-content .o-Emoji[data-index='0'].o-active");
    const codepoints = $(".o-EmojiPicker-content .o-Emoji[data-index='0'].o-active").data(
        "codepoints"
    );
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
    await contains(".o-Emoji", {
        text: "😀",
        after: ["span", { textContent: "Frequently used" }],
        before: ["span", { textContent: "Smileys & Emotion" }],
    });
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
    await contains(".o-Emoji", {
        text: "👽",
        after: ["span", { textContent: "Frequently used" }],
        before: [
            ".o-Emoji",
            {
                text: "😀",
                after: ["span", { textContent: "Frequently used" }],
                before: ["span", { textContent: "Smileys & Emotion" }],
            },
        ],
    });
});

QUnit.test("posting :wink: in message should impact recent", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", ":wink:");
    await click(".o-mail-Composer-send:enabled");
    await click("button[aria-label='Emojis']");
    await contains(".o-Emoji", {
        text: "😉",
        after: ["span", { textContent: "Frequently used" }],
        before: ["span", { textContent: "Smileys & Emotion" }],
    });
});

QUnit.test("posting :snowman: in message should impact recent", async () => {
    // the snowman emoji is composed of two codepoints, making it a corner case
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", ":snowman:");
    await click(".o-mail-Composer-send:enabled");
    await click("button[aria-label='Emojis']");
    await contains(".o-Emoji", {
        text: "☃️",
        after: ["span", { textContent: "Frequently used" }],
        before: ["span", { textContent: "Smileys & Emotion" }],
    });
});

QUnit.test("first category should be highlighted by default", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await contains(".o-EmojiPicker-navbar :nth-child(1 of .o-Emoji).o-active");
});

QUnit.test(
    "selecting an emoji while holding down the Shift key prevents the emoji picker from closing",
    async () => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({ name: "" });
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await click("button[aria-label='Emojis']");
        await click(".o-EmojiPicker-content .o-Emoji", { shiftKey: true, text: "👺" });
        await contains(".o-EmojiPicker-navbar [title='Frequently used']");
        await contains(".o-EmojiPicker");
        await contains(".o-mail-Composer-input", { value: "👺" });
    }
);
