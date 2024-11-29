import { describe, test } from "@odoo/hoot";
import { QuickReactionMenu } from "@mail/core/common/quick_reaction_menu";
import {
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
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

test("can open emoji picker from quick reaction menu", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Hello world!");
    await press("Enter");
    await click("[title='Add a Reaction']");
    await click(".o-mail-QuickReactionMenu [title='Open Emoji Picker']");
    await contains(".o-EmojiPicker");
    await contains(".o-mail-QuickReactionMenu", { count: 0 });
    await click("[title='Add a Reaction']");
    await contains(".o-mail-QuickReactionMenu");
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
    await click(".o-mail-QuickReactionMenu [title='Open Emoji Picker']");
    await click(".o-Emoji", { text: "🤢" });
    await click("[title='Add a Reaction']");
    await contains(".o-mail-QuickReactionMenu-emoji", {
        text: QuickReactionMenu.DEFAULT_EMOJIS[0],
        count: 0,
    });
    await contains(".o-mail-QuickReactionMenu-emoji", { text: "🤢" });
});
