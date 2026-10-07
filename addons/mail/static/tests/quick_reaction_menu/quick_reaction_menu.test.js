import {
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { QuickReactionMenu } from "@mail/core/common/quick_reaction_menu";
import { describe, test } from "@odoo/hoot";
import { animationFrame, press, waitFor, waitForNone } from "@odoo/hoot-dom";

describe.current.tags("desktop");
defineMailModels();

test("can toggle reaction from quick reaction menu", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Hello world!");
    await press("Enter");
    await click("[title='Add a Reaction']");
    await click(".o-mail-QuickReactionMenu button:text('👍')");
    await waitFor(".o-mail-MessageReaction:text('👍 1'):count(1)");
    await waitForNone(".o-mail-QuickReactionMenu");
    await click(".o-mail-Message-actions [title='Add a Reaction']");
    await click(".o-mail-QuickReactionMenu button:text('👍')");
    await waitForNone(".o-mail-MessageReaction:text('👍 1')");
    await waitForNone(".o-mail-QuickReactionMenu");
});

test("toggle emoji picker from quick reaction menu", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Hello world!");
    await press("Enter");
    await click("[title='Add a Reaction']");
    await click(".o-mail-QuickReactionMenu [title='Toggle Emoji Picker']");
    await waitFor(".o-EmojiPicker:count(1)");
    await click(".o-mail-QuickReactionMenu [title='Toggle Emoji Picker']");
    await waitForNone(".o-EmojiPicker");
});

test("show default emojis when no frequent emojis are available", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Hello world!");
    await press("Enter");
    await click("[title='Add a Reaction']");
    await contains(".o-mail-QuickReactionMenu-emoji", {
        count: QuickReactionMenu.DEFAULT_EMOJIS.length,
    });
    for (const emoji of QuickReactionMenu.DEFAULT_EMOJIS) {
        await contains(".o-mail-QuickReactionMenu-emoji:text('" + emoji + "')");
    }
    await click(".o-mail-QuickReactionMenu [title='Toggle Emoji Picker']");
    await click(".o-Emoji:text('🤢')");
    await click(".o-mail-Message-actions [title='Add a Reaction']");
    await contains(
        ".o-mail-QuickReactionMenu-emoji:text('" + QuickReactionMenu.DEFAULT_EMOJIS.at(-1) + "')",
        {
            count: 0,
        }
    );
    await waitFor(".o-mail-QuickReactionMenu-emoji:text('🤢'):count(1)");
});

test("navigate quick reaction menu using tab key", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Hello world!");
    await press("Enter");
    await click("[title='Add a Reaction']");
    for (const emoji of QuickReactionMenu.DEFAULT_EMOJIS) {
        await contains(".o-mail-QuickReactionMenu-emoji:focus:text('" + emoji + "')");
        await press("Tab");
    }
    await waitFor(".o-mail-QuickReactionMenu-emojiPicker:focus:count(1)");
});

test("navigate quick reaction menu using arrow keys", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Hello world!");
    await press("Enter");
    await click("[title='Add a Reaction']");
    for (const emoji of QuickReactionMenu.DEFAULT_EMOJIS) {
        await contains(".o-mail-QuickReactionMenu-emoji:focus:text('" + emoji + "')");
        await press("ArrowRight");
    }
    await waitFor(".o-mail-QuickReactionMenu-emojiPicker:focus:count(1)");
    await press("ArrowLeft");
    for (const emoji of [...QuickReactionMenu.DEFAULT_EMOJIS].reverse()) {
        await contains(".o-mail-QuickReactionMenu-emoji:focus:text('" + emoji + "')");
        await press("ArrowLeft");
    }
    await waitFor(".o-mail-QuickReactionMenu-emojiPicker:focus:count(1)");
});

test("can quick search emoji from quick reaction", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Hello world!");
    await press("Enter");
    await click("[title='Add a Reaction']");
    await waitFor(".o-mail-QuickReactionMenu:count(1)");
    await press("b");
    await waitFor(".o-EmojiPicker:count(1)");
    await waitFor(".o-EmojiPicker-search input:value('b'):count(1)");
    for (const ch of [..."roccoli"]) {
        await press(ch);
    }
    await waitFor(".o-EmojiPicker-search input:value('broccoli'):count(1)");
    await animationFrame();
    await press("Enter");
    await waitFor(".o-mail-MessageReaction:text('🥦 1'):count(1)");
});

test("shift-clicking on an emoji keeps the emoji picker open", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Hello world!");
    await press("Enter");
    await click("[title='Add a Reaction']");
    const defaultEmoji = QuickReactionMenu.DEFAULT_EMOJIS[0];
    await click(`.o-mail-QuickReactionMenu-emoji:text(${defaultEmoji})`, { shiftKey: true });
    await waitFor(`.o-mail-MessageReaction:text(${defaultEmoji} 1):count(1)`);
    await waitFor(".o-mail-QuickReactionMenu:count(1)");
    await click(`.o-mail-QuickReactionMenu-emoji:text(${defaultEmoji})`);
    await waitForNone(`.o-mail-MessageReaction:text(${defaultEmoji} 1)`);
    await waitForNone(".o-mail-QuickReactionMenu");
    await click("[title='Add a Reaction']");
    await click(".o-mail-QuickReactionMenu-emojiPicker");
    await click(".o-EmojiPicker-content .o-Emoji:text(👺)", { shiftKey: true });
    await waitFor(".o-mail-MessageReaction:text(👺 1):count(1)");
    await waitFor(".o-EmojiPicker:count(1)");
    await click(".o-EmojiPicker-content .o-Emoji:text(👺)");
    await waitForNone(".o-mail-MessageReaction:text(👺 1)");
    await waitForNone(".o-EmojiPicker");
    await waitForNone(".o-mail-QuickReactionMenu");
});

test.tags("focus required");
test("return focus to thread composer on close", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Hello world!");
    await press("Enter");
    await waitFor(".o-mail-Composer-input:focus:count(1)");
    await click("[title='Add a Reaction']");
    await waitFor(".o-mail-QuickReactionMenu-emoji:focus:text('👍'):count(1)");
    await press("Enter");
    await waitFor(".o-mail-MessageReaction:text('👍 1'):count(1)");
    await waitFor(".o-mail-Composer-input:focus:count(1)");
});

test.tags("focus required");
test("return focus to message edition composer on close", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Hello world!");
    await press("Enter");
    await contains(".o-mail-Composer-input", { value: "" });
    await insertText(".o-mail-Composer-input", "Goodbye world!!");
    await press("Enter");
    await click(".o-mail-Message:last [title='Expand']");
    await click(".o-dropdown-item:text('Edit')");
    await waitFor(".o-mail-Message .o-mail-Composer-input:focus:count(1)");
    await click("[title='Add a Reaction']");
    await waitFor(".o-mail-QuickReactionMenu-emoji:focus:text('👍'):count(1)");
    await press("Enter");
    await waitFor(".o-mail-MessageReaction:text('👍 1'):count(1)");
    await waitFor(".o-mail-Message .o-mail-Composer-input:focus:count(1)");
});
