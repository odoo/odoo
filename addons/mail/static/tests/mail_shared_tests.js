import { click, contains, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";
import { expect, mockTouch, mockUserAgent, queryFirst } from "@odoo/hoot";

export async function mailCanAddMessageReactionMobile() {
    mockTouch(true);
    mockUserAgent("android");
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create([
        {
            body: "Hello world",
            res_id: channelId,
            message_type: "comment",
            model: "discuss.channel",
        },
        {
            body: "Hello Odoo",
            res_id: channelId,
            message_type: "comment",
            model: "discuss.channel",
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 2 });
    await contains(".o-mail-Message:contains('Hello world')");
    await click(".o-mail-Message:contains('Hello world') [title='Expand']");
    await click(".o-dropdown-item:contains('Add a Reaction')");
    await contains(".o-overlay-item:has(.modal .o-EmojiPicker)");
    const emojiPickerZIndex = parseInt(
        getComputedStyle(queryFirst(".o-overlay-item:has(.modal .o-EmojiPicker)")).zIndex
    );
    const chatWindowZIndex = parseInt(getComputedStyle(queryFirst(".o-mail-ChatWindow")).zIndex);
    expect(chatWindowZIndex).toBeLessThan(emojiPickerZIndex, {
        message: "emoji picker modal should be above chat window",
    });
    await click(".modal .o-EmojiPicker .o-Emoji:contains('😀')");
    await contains(".o-mail-MessageReaction:contains('😀')");
    // Can quickly add new reactions
    await click(".o-mail-MessageReactions button[title='Add a Reaction']");
    await click(".modal .o-EmojiPicker .o-Emoji:contains('🤣')");
    await contains(".o-mail-MessageReaction:contains('🤣')");
    await contains(".o-mail-MessageReaction:contains('😀')");
}

export async function mailCanCopyTextToClipboardMobile() {
    mockTouch(true);
    mockUserAgent("android");
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create([
        {
            body: "Hello world",
            res_id: channelId,
            message_type: "comment",
            model: "discuss.channel",
        },
        {
            body: "Hello Odoo",
            res_id: channelId,
            message_type: "comment",
            model: "discuss.channel",
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 2 });
    await contains(".o-mail-Message:contains('Hello world')");
    await click(".o-mail-Message:contains('Hello world') [title='Expand']");
    await contains(".o-dropdown-item:contains('Copy to Clipboard')");
}
