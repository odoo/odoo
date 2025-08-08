import {
    click,
    contains,
    defineMailModels,
    insertText,
    onRpcAfter,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Deferred, mockDate, animationFrame } from "@odoo/hoot-mock";
import { Command, serverState, withUser } from "@web/../tests/web_test_helpers";
import { rpc } from "@web/core/network/rpc";

describe.current.tags("desktop");
defineMailModels();

test("navigate to sub channel", async () => {
    mockDate("2025-01-01 12:00:00", +1);
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    // Should access sub-thread after its creation.
    await contains(".o-mail-DiscussContent-threadName", { value: "General" });
    await click("button[title='Threads']");
    await click("button[aria-label='Create Thread']");
    await contains(".o-mail-DiscussContent-threadName", { value: "New Thread" });
    // Should access sub-thread when clicking on the menu.
    await click(".o-mail-DiscussSidebarChannel", { name: "General" });
    await contains(".o-mail-DiscussContent-threadName", { value: "General" });
    await click("button[title='Threads']");
    await click(".o-mail-SubChannelList-thread", { text: "New Thread" });
    await contains(".o-mail-DiscussContent-threadName", { value: "New Thread" });
    // Should access sub-thread when clicking on the notification.
    await click(".o-mail-DiscussSidebarChannel", { name: "General" });
    await contains(".o-mail-DiscussContent-threadName", { value: "New Thread" });
    await contains(".o-mail-NotificationMessage", {
        text: `${serverState.partnerName} started a thread: New Thread.1:00 PM`,
    });
    await click(".o-mail-NotificationMessage a", { text: "New Thread" });
    await contains(".o-mail-DiscussContent-threadName", { value: "New Thread" });
});

test("can manually unpin a sub-thread", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    // Open thread so this is pinned
    await contains(".o-mail-DiscussContent-threadName", { value: "General" });
    await click("button[title='Threads']");
    await click("button[aria-label='Create Thread']");
    await contains(".o-mail-DiscussContent-threadName", { value: "New Thread" });
    await click("[title='Threads Actions']");
    await click(".o-dropdown-item:contains('Unpin Conversation')");
    await contains(".o-mail-DiscussSidebar-item", { text: "New Thread", count: 0 });
});

test("create sub thread from existing message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        model: "discuss.channel",
        res_id: channelId,
        body: "<p>Selling a training session and selling the products after the training session is more efficient.</p>",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message-actions [title='Expand']");
    await click(".o-dropdown-item:contains('Create Thread')");
    await contains(".o-mail-DiscussContent-threadName", {
        value: "Selling a training session and",
    });
    await contains(".o-mail-Message", {
        text: "Selling a training session and selling the products after the training session is more efficient.",
    });
    await click(".o-mail-DiscussSidebarChannel", { name: "General" });
    await click(".o-mail-Message-actions [title='Expand']");
    await contains(".o-dropdown-item:contains('Create Thread')", { count: 0 });
    await click(".o-dropdown-item:contains('View Thread')");
    await contains(".o-mail-DiscussContent-threadName", {
        value: "Selling a training session and",
    });
});

test("should allow creating a thread from an existing thread", async () => {
    mockDate("2025-01-01 12:00:00", +1);
    const pyEnv = await startServer();
    const parent_channel_id = pyEnv["discuss.channel"].create({ name: "General" });
    const sub_channel_id = pyEnv["discuss.channel"].create({
        name: "sub channel",
        parent_channel_id: parent_channel_id,
    });
    pyEnv["mail.message"].create({
        model: "discuss.channel",
        res_id: sub_channel_id,
        body: "<p>hello alex</p>",
    });
    await start();
    await openDiscuss(sub_channel_id);
    await click(".o-mail-Message-actions [title='Expand']");
    await click(".o-dropdown-item:contains('Create Thread')");
    await contains(".o-mail-DiscussContent-threadName", { value: "hello alex" });
    await click(".o-mail-DiscussSidebarChannel", { name: "General" });
    await contains(".o-mail-NotificationMessage", {
        text: `${serverState.partnerName} started a thread: hello alex.1:00 PM`,
    });
});

test("create sub thread from existing message (slow network)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        model: "discuss.channel",
        res_id: channelId,
        body: "<p>Selling a training session and selling the products after the training session is more efficient.</p>",
    });
    const createSubChannelDef = new Deferred();
    onRpcAfter("/discuss/channel/sub_channel/create", async () => await createSubChannelDef);
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message-actions [title='Expand']");
    await click(".o-dropdown-item:contains('Create Thread')");
    await animationFrame();
    createSubChannelDef.resolve();
    await contains(".o-mail-DiscussContent-threadName", {
        value: "Selling a training session and",
    });
    await contains(".o-mail-Message", {
        text: "Selling a training session and selling the products after the training session is more efficient.",
    });
});

test("create sub thread from sub-thread list", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Threads']");
    await contains(".o-mail-SubChannelList", { text: "This channel has no thread yet." });
    await click("button[aria-label='Create Thread']");
    await contains(".o-mail-DiscussContent-threadName", { value: "New Thread" });
    await click(".o-mail-DiscussSidebarChannel", { name: "General" });
    await contains(".o-mail-DiscussContent-threadName", { value: "General" });
    await click(".o-mail-DiscussContent-header button[title='Threads']");
    await insertText(
        ".o-mail-ActionPanel:has(.o-mail-SubChannelList) .o_searchview_input",
        "MyEpicThread"
    );
    await click("button[aria-label='Search button']");
    await contains(".o-mail-SubChannelList", { text: 'No thread named "MyEpicThread"' });
    await click("button[aria-label='Create Thread']");
    await contains(".o-mail-DiscussContent-threadName", { value: "MyEpicThread" });
});

test("'Thread' menu available in threads", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
    });
    const subChannelID = pyEnv["discuss.channel"].create({
        name: "ThreadOne",
        parent_channel_id: channelId,
    });
    await start();
    await openDiscuss(subChannelID);
    await click(".o-mail-DiscussSidebar-item", { text: "ThreadOne" });
    await contains(".o-mail-DiscussContent-threadName", { value: "ThreadOne" });
    await click("button[title='Threads']");
    await insertText(".o-mail-ActionPanel input[placeholder='Search by name']", "ThreadTwo");
    await click(".o-mail-ActionPanel button", { text: "Create" });
    await click(".o-mail-DiscussSidebar-item", { text: "ThreadTwo" });
});

test("sub thread is available for channel and group, not for chat", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
    });
    pyEnv["discuss.channel"].create({
        name: "Group",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "group",
    });
    pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Threads']");
    await insertText(
        ".o-mail-ActionPanel input[placeholder='Search by name']",
        "Sub thread for channel"
    );
    await click(".o-mail-ActionPanel button", { text: "Create" });
    await click(".o-mail-DiscussSidebar-item", { text: "Sub thread for channel" });
    await click(".o-mail-DiscussSidebarChannel", { text: "Group" });
    await contains(".o-mail-DiscussContent-threadName", { value: "Group" });
    await click("button[title='Threads']");
    await insertText(
        ".o-mail-ActionPanel input[placeholder='Search by name']",
        "Sub thread for group"
    );
    await click(".o-mail-ActionPanel button", { text: "Create" });
    await click(".o-mail-DiscussSidebar-item", { text: "Sub thread for group" });
    await click(".o-mail-DiscussSidebarChannel", { text: "Demo" });
    await contains("button[title='Threads']", { count: 0 });
});

test("mention suggestions in thread match channel restrictions", async () => {
    const pyEnv = await startServer();
    const groupId = pyEnv["res.groups"].create({ name: "testGroup" });
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        group_public_id: groupId,
    });
    pyEnv["discuss.channel"].create({
        name: "Thread",
        parent_channel_id: channelId,
    });
    pyEnv["res.users"].write(serverState.userId, { group_ids: [Command.link(groupId)] });
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { email: "p1@odoo.com", name: "p1" },
        { email: "p2@odoo.com", name: "p2" },
    ]);
    pyEnv["res.users"].create([
        { partner_id: partnerId_1, group_ids: [Command.link(groupId)] },
        { partner_id: partnerId_2 },
    ]);
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussSidebar-item.o-active:contains('General')");
    await insertText(".o-mail-Composer-input", "@");
    await contains(".o-mail-Composer-suggestion", { count: 2 });
    await contains(".o-mail-Composer-suggestion", { text: "Mitchell Admin" });
    await contains(".o-mail-Composer-suggestion", { text: "p1" });
    await click(".o-mail-DiscussSidebar-item:contains('Thread')");
    await contains(".o-mail-DiscussSidebar-item.o-active:contains('Thread')");
    await insertText(".o-mail-Composer-input", "@");
    await contains(".o-mail-Composer-suggestion", { count: 2 });
    await contains(".o-mail-Composer-suggestion", { text: "Mitchell Admin" });
    await contains(".o-mail-Composer-suggestion", { text: "p1" });
});

test("sub-thread is visually muted when mute is active", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussContent-threadName", { value: "General" });
    await click("button[title='Threads']");
    await click("button[aria-label='Create Thread']");
    await contains(".opacity-50.o-mail-DiscussSidebar-item:contains('New Thread')", { count: 0 });
    await click(".o-mail-DiscussSidebar-item:contains('New Thread')");
    await click("button[title='Notification Settings']");
    await click("button:contains('Mute Conversation')");
    await click("button:contains('Until I turn it back on')");
    await contains(".opacity-50.o-mail-DiscussSidebar-item:contains('New Thread')");
});

test("muted channel hides sub-thread unless channel is selected or thread has unread messages", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const partnerId2 = pyEnv["res.partner"].create({ email: "p1@odoo.com", name: "p1" });
    const userId2 = pyEnv["res.users"].create({ name: "User 2", partner_id: partnerId2 });
    const partnerId = serverState.partnerId;
    const subChannelId = pyEnv["discuss.channel"].create({
        name: "New Thread",
        parent_channel_id: channelId,
        channel_member_ids: [
            Command.create({ partner_id: partnerId }),
            Command.create({ partner_id: partnerId2 }),
        ],
    });
    pyEnv["discuss.channel"].create({ name: "Other" });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-DiscussSidebar-item:contains('General')");
    await click("button[title='Notification Settings']");
    await click("button:contains('Mute Conversation')");
    await click("button:contains('Until I turn it back on')");
    await click(".o-mail-DiscussSidebar-item:contains('Other')");
    await contains(".o-mail-DiscussSidebar-item:contains('New Thread')", { count: 0 });
    await click(".o-mail-DiscussSidebar-item:contains('General')");
    await contains(".o-mail-DiscussSidebar-item:contains('New Thread')");
    await click(".o-mail-DiscussSidebar-item:contains('Other')");
    await contains(".o-mail-DiscussSidebar-item:contains('New Thread')", { count: 0 });
    withUser(userId2, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Some message", message_type: "comment" },
            thread_id: subChannelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-DiscussSidebar-item:contains('New Thread')");
});

test("show notification when clicking on deleted thread", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "Test Channel" });
    const activeThreadId = pyEnv["discuss.channel"].create({
        name: "Message 1",
        parent_channel_id: channelId,
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: `<div class="o_mail_notification"> started a thread:<a href="#" class="o_channel_redirect" data-oe-id="${activeThreadId}" data-oe-model="discuss.channel">Message 1</a></div>`,
        message_type: "notification",
        model: "discuss.channel",
        res_id: channelId,
    });
    pyEnv["discuss.channel"].unlink(activeThreadId);
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-NotificationMessage a", { text: "Message 1" });
    await contains(".o_notification:has(.o_notification_bar.bg-danger)", {
        text: "This thread is no longer available.",
    });
});
