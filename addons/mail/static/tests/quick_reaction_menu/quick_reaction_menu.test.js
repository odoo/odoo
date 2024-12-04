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
import { press } from "@odoo/hoot-dom";

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
    await click(".o-mail-QuickReactionMenu button", { text: "👍" });
    await contains(".o-mail-MessageReaction", { text: "👍1" });
    await click("[title='Add a Reaction']");
    await click(".o-mail-QuickReactionMenu button", { text: "👍" });
    await contains(".o-mail-MessageReaction", { text: "👍1", count: 0 });
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
    await contains(".o-EmojiPicker");
    await click(".o-mail-QuickReactionMenu [title='Toggle Emoji Picker']");
    await contains(".o-EmojiPicker", { count: 0 });
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
        await contains(".o-mail-QuickReactionMenu-emoji", { text: emoji });
    }
    await click(".o-mail-QuickReactionMenu [title='Toggle Emoji Picker']");
    await click(".o-Emoji", { text: "🤢" });
    await click("[title='Add a Reaction']");
    await contains(".o-mail-QuickReactionMenu-emoji", {
        text: QuickReactionMenu.DEFAULT_EMOJIS.at(-1),
        count: 0,
    });
    await contains(".o-mail-QuickReactionMenu-emoji", { text: "🤢" });
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
        await contains(".o-mail-QuickReactionMenu-emoji:focus", { text: emoji });
        await press("Tab");
    }
    await contains(".o-mail-QuickReactionMenu-emojiPicker:focus");
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
        await contains(".o-mail-QuickReactionMenu-emoji:focus", { text: emoji });
        await press("ArrowRight");
    }
    await contains(".o-mail-QuickReactionMenu-emojiPicker:focus");
    await press("ArrowLeft");
    for (const emoji of QuickReactionMenu.DEFAULT_EMOJIS.reverse()) {
        await contains(".o-mail-QuickReactionMenu-emoji:focus", { text: emoji });
        await press("ArrowLeft");
    }
    await contains(".o-mail-QuickReactionMenu-emojiPicker:focus");
});
