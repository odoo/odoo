import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    scroll,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test, expect } from "@odoo/hoot";
import { disableAnimations } from "@odoo/hoot-mock";

describe.current.tags("desktop");
defineMailModels();

async function assertPinnedPanelUnpinCount(expectedCount) {
    await contains(".dropdown-item", { text: "Unpin", count: expectedCount });
    await click(".o-mail-DiscussContent-header button[title='Pinned Messages']");
    await contains(".o-discuss-PinnedMessagesPanel .o-mail-Message", {
        text: "Test pinned message",
    });
    expect(".o-discuss-PinnedMessagesPanel button[title='Unpin']").toHaveCount(expectedCount);
}

test("Pin message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMemberList"); // wait for auto-open of this panel
    await click(".o-mail-DiscussContent-header button[title='Pinned Messages']");
    await contains(".o-discuss-PinnedMessagesPanel p", {
        text: "This channel doesn't have any pinned messages.",
    });
    await click(".o-mail-Message [title='Expand']");
    await click(".dropdown-item", { text: "Pin" });
    await click(".modal-footer button", { text: "Yeah, pin it!" });
    await contains(".o-discuss-PinnedMessagesPanel .o-mail-Message", { text: "Hello world!" });
});

test("Unpin message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
        pinned_at: "2023-03-30 11:27:11",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMemberList"); // wait for auto-open of this panel
    await click(".o-mail-DiscussContent-header button[title='Pinned Messages']");
    await contains(".o-discuss-PinnedMessagesPanel .o-mail-Message");
    await click(".o-mail-Message [title='Expand']");
    await click(".dropdown-item", { text: "Unpin" });
    await click(".modal-footer button", { text: "Yes, remove it please" });
    await contains(".o-discuss-PinnedMessagesPanel .o-mail-Message", { count: 0 });
});

test("Open pinned panel from notification", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
    });
    await start();
    await openDiscuss(channelId);
    await click(":nth-child(1 of .o-mail-Message) [title='Expand']");
    await click(".dropdown-item", { text: "Pin" });
    await click(".modal-footer button", { text: "Yeah, pin it!" });
    await contains(".o-discuss-PinnedMessagesPanel", { count: 0 });
    await click(".o_mail_notification a", { text: "See all pinned messages" });
    await contains(".o-discuss-PinnedMessagesPanel");
});

test("Jump to message", async () => {
    disableAnimations();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
        pinned_at: "2023-04-03 08:15:04",
    });
    for (let i = 0; i < 20; i++) {
        pyEnv["mail.message"].create({
            body: "Non Empty Body ".repeat(25),
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMemberList"); // wait for auto-open of this panel
    await click(".o-mail-DiscussContent-header button[title='Pinned Messages']");
    await click(".o-discuss-PinnedMessagesPanel a[role='button']", { text: "Jump" });
    await contains(".o-mail-Thread .o-mail-Message-body", { text: "Hello world!", visible: true });
});

test("Jump to message from notification", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
    });
    for (let i = 0; i < 20; i++) {
        pyEnv["mail.message"].create({
            body: "Non Empty Body ".repeat(25),
            message_type: "comment",
            model: "discuss.channel",
            res_id: channelId,
        });
    }
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 21 });
    await click(":nth-child(1 of .o-mail-Message) [title='Expand']");
    await click(".dropdown-item", { text: "Pin" });
    await click(".modal-footer button", { text: "Yeah, pin it!" });
    await contains(".o_mail_notification");
    await scroll(".o-mail-Thread", "bottom");
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await click(".o_mail_notification a", { text: "message" });
    await contains(".o-mail-Thread", { count: 0, scroll: "bottom" });
});

test("can add reactions from pinned panel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
        pinned_at: "2025-10-09 11:15:04",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message-actions [title='Add a Reaction']");
    await click(".o-mail-QuickReactionMenu button", { text: "👍" });
    await contains(".o-mail-MessageReaction", { text: "👍1" });
    await click(".o-mail-DiscussContent-header button[title='Pinned Messages']");
    await click(".o-discuss-PinnedMessagesPanel .o-mail-Message [title='Add a Reaction']");
    await click(".o-mail-QuickReactionMenu button", { text: "👍" });
    await contains(".o-mail-MessageReaction", { count: 0 });
});

test("Guest user cannot see unpin button", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_type: "channel",
    });
    pyEnv["mail.message"].create({
        body: "Test pinned message",
        model: "discuss.channel",
        res_id: channelId,
        pinned_at: "2023-03-30 11:27:11",
    });
    await start({ authenticateAs: false });
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { text: "Test pinned message" });
    expect(".o-mail-Message [title='Expand']").toHaveCount(0);
    await assertPinnedPanelUnpinCount(0);
});

test("Internal user can see unpin button", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Test pinned message",
        model: "discuss.channel",
        res_id: channelId,
        pinned_at: "2023-03-30 11:27:11",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message [title='Expand']");
    await assertPinnedPanelUnpinCount(1);
});
