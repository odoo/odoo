/** @odoo-module */

import { test } from "@odoo/hoot";

import { EMOJI_PER_ROW } from "@web/core/emoji_picker/emoji_picker";
import {
    click,
    contains,
    insertText,
    openDiscuss,
    start,
    startServer,
    triggerHotkey,
} from "../mail_test_helpers";

test.skip("search emoji from keywords", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await insertText("input[placeholder='Search for an emoji']", "mexican");
    await contains(".o-Emoji", { text: "🌮" });
});

test.skip("search emoji from keywords should be case insensitive", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await insertText("input[placeholder='Search for an emoji']", "ok");
    await contains(".o-Emoji", { text: "🆗" }); // all search terms are uppercase OK
});

test.skip("search emoji from keywords with special regex character", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await insertText("input[placeholder='Search for an emoji']", "(blood");
    await contains(".o-Emoji", { text: "🆎" });
});

test.skip("updating search emoji should scroll top", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await contains(".o-EmojiPicker-content", { scroll: 0 });
    await scroll(".o-EmojiPicker-content", 150);
    await insertText("input[placeholder='Search for an emoji']", "m");
    await contains(".o-EmojiPicker-content", { scroll: 0 });
});

test.skip("Press Escape in emoji picker closes the emoji picker", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    triggerHotkey("Escape");
    await contains(".o-EmojiPicker", { count: 0 });
});

test.skip("Basic keyboard navigation", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
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

test.skip("recent category (basic)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
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

test.skip("emoji usage amount orders frequent emojis", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
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

test.skip("first category should be highlighted by default", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await contains(".o-EmojiPicker-navbar :nth-child(1 of .o-Emoji).o-active");
});

test.skip("selecting an emoji while holding down the Shift key prevents the emoji picker from closing", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await click(".o-EmojiPicker-content .o-Emoji", { shiftKey: true, text: "👺" });
    await contains(".o-EmojiPicker-navbar [title='Frequently used']");
    await contains(".o-EmojiPicker");
    await contains(".o-mail-Composer-input", { value: "👺" });
});
