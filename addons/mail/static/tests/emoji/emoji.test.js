import { patchTranslations, preloadBundle } from "@web/../tests/web_test_helpers";

import {
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, getFixture, test } from "@odoo/hoot";

import { queryFirst } from "@odoo/hoot-dom";

describe.current.tags("desktop");
defineMailModels();
preloadBundle("web.assets_emoji");

test("emoji picker works well with translation with double quotes", async () => {
    patchTranslations({
        "Japanese “here” button": `Bouton "ici" japonais`,
    });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await insertText("input[placeholder='Search emoji']", "ici");
    await contains(`.o-Emoji[title='Bouton "ici" japonais']`);
});

test("search emoji from keywords", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await insertText("input[placeholder='Search emoji']", "mexican");
    await contains(".o-Emoji", { text: "🌮" });
});

test("search emoji from keywords should be case insensitive", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await insertText("input[placeholder='Search emoji']", "ok");
    await contains(".o-Emoji", { text: "🆗" }); // all search terms are uppercase OK
});

test("search emoji from keywords with special regex character", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await insertText("input[placeholder='Search emoji']", "(blood");
    await contains(".o-Emoji", { text: "🆎" });
});

test("updating search emoji should scroll top", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await contains(".o-EmojiPicker-content", { scroll: 0 });
    await scroll(".o-EmojiPicker-content", 150);
    await insertText("input[placeholder='Search emoji']", "m");
    await contains(".o-EmojiPicker-content", { scroll: 0 });
});

test("Press Escape in emoji picker closes the emoji picker", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    triggerHotkey("Escape");
    await contains(".o-EmojiPicker", { count: 0 });
});

test("Basic keyboard navigation", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-input:focus"); // as to ensure no race condition with auto-focus of emoji picker
    await click("button[aria-label='Emojis']");
    await contains(".o-Emoji[data-index='0'].o-active");
    // detect amount of emojis per row for navigation
    const emojis = Array.from(
        getFixture().querySelectorAll(".o-EmojiPicker-category[data-category='1'] ~ .o-Emoji")
    );
    const baseOffset = emojis[0].offsetTop;
    const breakIndex = emojis.findIndex((item) => item.offsetTop > baseOffset);
    const EMOJI_PER_ROW = breakIndex === -1 ? emojis.length : breakIndex;
    triggerHotkey("ArrowRight");
    await contains(".o-EmojiPicker-content .o-Emoji[data-index='1'].o-active");
    triggerHotkey("ArrowDown");
    await contains(`.o-EmojiPicker-content .o-Emoji[data-index='${EMOJI_PER_ROW + 1}'].o-active`);
    triggerHotkey("ArrowLeft");
    await contains(`.o-EmojiPicker-content .o-Emoji[data-index='${EMOJI_PER_ROW}'].o-active`);
    triggerHotkey("ArrowUp");
    await contains(".o-EmojiPicker-content .o-Emoji[data-index='0'].o-active");
    const { codepoints } = queryFirst(
        ".o-EmojiPicker-content .o-Emoji[data-index='0'].o-active"
    ).dataset;
    triggerHotkey("Enter");
    await contains(".o-EmojiPicker", { count: 0 });
    await contains(".o-mail-Composer-input", { value: codepoints });
});

test("recent category (basic)", async () => {
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

test("search emojis prioritize frequently used emojis", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await contains(".o-EmojiPicker-navbar [title='Frequently used']", { count: 0 });
    await click(".o-EmojiPicker-content .o-Emoji", { text: "🤥" });
    await click("button[aria-label='Emojis']");
    await contains(".o-EmojiPicker-navbar [title='Frequently used']");
    await insertText("input[placeholder='Search emoji']", "lie");
    await contains(".o-EmojiPicker-sectionIcon", { count: 0 }); // await search performed
    await contains(".o-EmojiPicker-content .o-Emoji:eq(0)", { text: "🤥" });
});

test("search matches only frequently used emojis", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await contains(".o-EmojiPicker-navbar [title='Frequently used']", { count: 0 });
    await click(".o-EmojiPicker-content .o-Emoji", { text: "🥦" });
    await click("button[aria-label='Emojis']");
    await contains(".o-EmojiPicker-navbar [title='Frequently used']");
    await insertText("input[placeholder='Search emoji']", "brocoli");
    await contains(".o-EmojiPicker-sectionIcon", { count: 0 }); // await search performed
    await contains(".o-EmojiPicker-content .o-Emoji:eq(0)", { text: "🥦" });
    await contains(".o-EmojiPicker-content .o-Emoji", { count: 1 });
    await contains(".o-EmojiPicker-content", { text: "No emoji matches your search", count: 0 });
    await insertText("input[placeholder='Search emoji']", "2");
    await contains(".o-EmojiPicker-content", { text: "No emoji matches your search" });
});

test("emoji usage amount orders frequent emojis", async () => {
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

test("first category should be highlighted by default", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[aria-label='Emojis']");
    await contains(".o-EmojiPicker-navbar :nth-child(1 of .o-Emoji).o-active");
});

test("selecting an emoji while holding down the Shift key prevents the emoji picker from closing", async () => {
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
