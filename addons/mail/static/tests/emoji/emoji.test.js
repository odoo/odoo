import { defineParams, preloadBundle, serverState } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

import {
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    scroll,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, getFixture, queryFirst, test } from "@odoo/hoot";
import { queryAllTexts, waitFor, waitForNone } from "@odoo/hoot-dom";

import { signal } from "@odoo/owl";
import { emojiLoader } from "@web/core/emoji_picker/emoji_loader";

describe.current.tags("desktop");
defineMailModels();
preloadBundle("web.assets_emoji");

test("emoji picker correctly handles translations with special characters", async () => {
    // Reset emoji loader to reload translations *for* the current test
    patch(emojiLoader, {
        _categories: signal.Array([]),
        _emojis: signal.Array([]),
        _loadingPromise: null,
        _map: null,
    });
    defineParams({
        translations: {
            "Japanese “here” button": `Bouton "ici" japonais`,
            "heavy dollar sign": `Symbole du dollar\nlourd`,
        },
    });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Add Emojis']");
    await insertText(".o-EmojiPicker-search input", "ici");
    await waitFor(`.o-Emoji[title='Bouton "ici" japonais']:count(1)`);
    await insertText(".o-EmojiPicker-search input", "dollar", { replace: true });
    await waitFor(`.o-Emoji[title*='Symbole du dollar']:count(1)`);
});

test("search emoji from keywords", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Add Emojis']");
    await insertText(".o-EmojiPicker-search input", "mexican");
    await waitFor(".o-Emoji:text('🌮'):count(1)");
    await insertText(".o-EmojiPicker-search input", "9", { replace: true });
    await waitFor(".o-Emoji:eq(0):text('🕘'):count(1)");
    await waitFor(".o-Emoji:eq(1):text('🕤'):count(1)");
    await waitFor(".o-Emoji:eq(2):text('9️⃣'):count(1)");
});

test("search emoji from keywords should be case insensitive", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Add Emojis']");
    await insertText(".o-EmojiPicker-search input", "ok");
    await waitFor(".o-Emoji:text('🆗'):count(1)"); // all search terms are uppercase OK
});

test("search emoji from keywords with special regex character", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Add Emojis']");
    await insertText(".o-EmojiPicker-search input", "(blood");
    await waitFor(".o-Emoji:text('🆎'):count(1)");
});

test("updating search emoji should scroll top", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Add Emojis']");
    await contains(".o-EmojiPicker-content", { scroll: 0 });
    await scroll(".o-EmojiPicker-content", 150);
    await insertText(".o-EmojiPicker-search input", "m");
    await contains(".o-EmojiPicker-content", { scroll: 0 });
});

test("Press Escape in emoji picker closes the emoji picker", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Add Emojis']");
    triggerHotkey("Escape");
    await waitForNone(".o-EmojiPicker");
});

test("Basic keyboard navigation", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer-input:focus:count(1)"); // as to ensure no race condition with auto-focus of emoji picker
    await click("button[title='Add Emojis']");
    await waitFor(".o-Emoji[data-index='0'].o-active:count(1)");
    // detect amount of emojis per row for navigation
    const emojis = Array.from(
        getFixture().querySelectorAll(".o-EmojiPicker-category[data-category='1'] ~ .o-Emoji")
    );
    const baseOffset = emojis[0].offsetTop;
    const breakIndex = emojis.findIndex((item) => item.offsetTop > baseOffset);
    const EMOJI_PER_ROW = breakIndex === -1 ? emojis.length : breakIndex;
    triggerHotkey("ArrowRight");
    await waitFor(".o-EmojiPicker-content .o-Emoji[data-index='1'].o-active:count(1)");
    triggerHotkey("ArrowDown");
    await waitFor(
        `.o-EmojiPicker-content .o-Emoji[data-index='${EMOJI_PER_ROW + 1}'].o-active:count(1)`
    );
    triggerHotkey("ArrowLeft");
    await waitFor(
        `.o-EmojiPicker-content .o-Emoji[data-index='${EMOJI_PER_ROW}'].o-active:count(1)`
    );
    triggerHotkey("ArrowUp");
    await waitFor(".o-EmojiPicker-content .o-Emoji[data-index='0'].o-active:count(1)");
    const { codepoints } = queryFirst(
        ".o-EmojiPicker-content .o-Emoji[data-index='0'].o-active"
    ).dataset;
    triggerHotkey("Enter");
    await waitForNone(".o-EmojiPicker");
    await contains(".o-mail-Composer-input", { value: codepoints });
});

test("recent category (basic)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Add Emojis']");
    await waitForNone(".o-EmojiPicker-navbar [title='Frequently used']");
    await click(".o-EmojiPicker-content .o-Emoji:text('😀')");
    await click("button[title='Add Emojis']");
    await waitFor(".o-EmojiPicker-navbar [title='Frequently used']:count(1)");
    await contains(".o-Emoji:text('😀')", {
        after: ["small", { textContent: "Frequently used" }],
        before: ["small", { textContent: "Smileys & Emotion" }],
    });
});

test("search emojis prioritize frequently used emojis", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Add Emojis']");
    await waitForNone(".o-EmojiPicker-navbar [title='Frequently used']");
    await click(".o-EmojiPicker-content .o-Emoji:text('🤥')");
    await click("button[title='Add Emojis']");
    await waitFor(".o-EmojiPicker-navbar [title='Frequently used']:count(1)");
    await insertText(".o-EmojiPicker-search input", "lie");
    await waitForNone(".o-EmojiPicker-sectionIcon"); // await search performed
    await waitFor(".o-EmojiPicker-content .o-Emoji:eq(0):text('🤥'):count(1)");
});

test("search matches only frequently used emojis", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Add Emojis']");
    await waitForNone(".o-EmojiPicker-navbar [title='Frequently used']");
    await click(".o-EmojiPicker-content .o-Emoji:text('🥦')");
    await click("button[title='Add Emojis']");
    await waitFor(".o-EmojiPicker-navbar [title='Frequently used']:count(1)");
    await insertText(".o-EmojiPicker-search input", "brocoli");
    await waitForNone(".o-EmojiPicker-sectionIcon"); // await search performed
    await waitFor(".o-EmojiPicker-content .o-Emoji:eq(0):text('🥦'):count(1)");
    await waitFor(".o-EmojiPicker-content .o-Emoji:count(1)");
    await waitForNone(".o-EmojiPicker-content:has(:text('No emojis match your search'))");
    await insertText(".o-EmojiPicker-search input", "2");
    await waitFor(".o-EmojiPicker-content:has(:text('No emojis match your search')):count(1)");
});

test("emoji usage amount orders frequent emojis", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Add Emojis']");
    await click(".o-EmojiPicker-content .o-Emoji:text('😀')");
    await click("button[title='Add Emojis']");
    await click(".o-EmojiPicker-content .o-Emoji:text('👽')");
    await click("button[title='Add Emojis']");
    await click(".o-EmojiPicker-content .o-Emoji:text('👽')");
    await click("button[title='Add Emojis']");
    await contains(".o-Emoji:text('👽')", {
        after: ["small", { textContent: "Frequently used" }],
        before: [
            ".o-Emoji:text('😀')",
            {
                after: ["small", { textContent: "Frequently used" }],
                before: ["small", { textContent: "Smileys & Emotion" }],
            },
        ],
    });
});

test("first category should be highlighted by default", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Add Emojis']");
    await waitFor(".o-EmojiPicker-navbar :nth-child(1 of .o-Emoji).o-active");
});

test("selecting an emoji while holding down the Shift key prevents the emoji picker from closing", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Add Emojis']");
    await click(".o-EmojiPicker-content .o-Emoji:text('👺')", { shiftKey: true });
    await waitFor(".o-EmojiPicker-navbar [title='Smileys & Emotion']:count(1)");
    await waitFor(".o-EmojiPicker:count(1)");
    await contains(".o-mail-Composer-input", { value: "👺" });
});

test("shortcodes shown in emoji title in message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    pyEnv["mail.message"].create({
        res_id: channelId,
        model: "discuss.channel",
        body: "💑😇",
        author_id: serverState.partnerId,
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Message:has(:text('💑😇')):count(1)");
    await waitFor(".o-mail-Message span[title=':couple_with_heart:']:text('💑'):count(1)");
    await waitFor(".o-mail-Message span[title=':innocent: :halo:']:text('😇'):count(1)");
});

test("Emoji picker shows failure to load emojis", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    // Simulate failure to load emojis
    patch(emojiLoader, {
        _emojis: signal.Array([]),
    });
    await openDiscuss(channelId);
    await click("button[title='Add Emojis']");
    await waitFor(".o-EmojiPicker:text('😵‍💫 Failed to load emojis...'):count(1)");
});

test("Frequently used category only appears when the emoji picker is reopened", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Add Emojis']");
    await click(".o-EmojiPicker-content .o-Emoji:text('😀')", { shiftKey: true });
    await contains(".o-mail-Composer-input", { value: "😀" });
    await click(".o-EmojiPicker-content .o-Emoji:text('😝')", { shiftKey: true });
    await contains(".o-mail-Composer-input", { value: "😀😝" });
    await waitFor(".o-EmojiPicker-section:count(8)");
    expect(queryAllTexts(".o-EmojiPicker-section small")).toEqual([
        "SMILEYS & EMOTION",
        "PEOPLE & BODY",
        "ANIMALS & NATURE",
        "FOOD & DRINK",
        "TRAVEL & PLACES",
        "ACTIVITIES",
        "OBJECTS",
        "SYMBOLS",
    ]);
    triggerHotkey("Escape");
    await click("button[title='Add Emojis']");
    await waitFor(".o-EmojiPicker-section:count(9)");
    expect(queryAllTexts(".o-EmojiPicker-section small")).toEqual([
        "FREQUENTLY USED",
        "SMILEYS & EMOTION",
        "PEOPLE & BODY",
        "ANIMALS & NATURE",
        "FOOD & DRINK",
        "TRAVEL & PLACES",
        "ACTIVITIES",
        "OBJECTS",
        "SYMBOLS",
    ]);
});

test("clear search icon appears with a search term and clears it on click", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "" });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Add Emojis']");
    await waitFor(".o-EmojiPicker-search input:count(1)");
    await insertText(".o-EmojiPicker-search input", "ok");
    await waitFor("[data-icon='cancel']:count(1)");
    await click("[data-icon='cancel']");
    await contains(".o-EmojiPicker-search input", { value: "" });
    await waitForNone("[data-icon='cancel']");
});
