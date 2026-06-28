import {
    click,
    contains,
    hover,
    openDiscuss,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { expect, mockTouch, mockUserAgent, queryFirst } from "@odoo/hoot";
import { serverState } from "@web/../tests/web_test_helpers";

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
    await contains(".o-dropdown-item:contains('Copy Text')");
}

export async function mailChatterMessageActionsInvisibleWhenNotHovered() {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "TestPartner" });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Hello world",
        model: "res.partner",
        res_id: partnerId,
        message_type: "comment",
    });
    const isNodeVisible = (selector) => {
        const { visibility } = getComputedStyle(queryFirst(selector));
        return visibility === "visible";
    };
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Message-actions.invisible");
    await contains(".o-mail-Message-actions button", { count: 2 });
    expect(isNodeVisible(".o-mail-Message-actions button:eq(0)")).toBe(false);
    expect(isNodeVisible(".o-mail-Message-actions button:eq(1)")).toBe(false);
    await hover(".o-mail-Message");
    await contains(".o-mail-Message-actions:not(.invisible)");
    await contains(".o-mail-Message-actions button", { count: 2 });
    expect(isNodeVisible(".o-mail-Message-actions button:eq(0)")).toBe(true);
    expect(isNodeVisible(".o-mail-Message-actions button:eq(1)")).toBe(true);
}
