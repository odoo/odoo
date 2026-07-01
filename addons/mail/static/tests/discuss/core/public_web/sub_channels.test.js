import {
    click,
    contains,
    defineMailModels,
    hover,
    insertText,
    onRpcAfter,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { animationFrame, mockDate } from "@odoo/hoot-mock";
import { Command, serverState } from "@web/../tests/web_test_helpers";

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
    await click(".o-mail-NotificationItem-name:text(General)");
    await contains(".o-mail-DiscussContent-threadName", { value: "General" });
    await click("button[title='Threads']");
    await click(".o-mail-SubChannelPreview .o-mail-SubChannelPreview-name:text('New Thread')");
    await contains(".o-mail-DiscussContent-threadName", { value: "New Thread" });
    // Should access sub-thread when clicking on the notification.
    await click(".o-mail-NotificationItem-name:text(General)");
    await contains(".o-mail-DiscussContent-threadName", { value: "New Thread" });
    await contains(
        `.o-mail-NotificationMessage:text('${serverState.partnerName} started a thread: New Thread.1:00 PM')`
    );
    await click(".o-mail-NotificationMessage a:text('New Thread')");
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
    await click(
        ".o-mail-MessagingMenuItem:has(:text('General New Thread')) [title='Channel Actions']"
    );
    await click(".o-dropdown-item:text('Hide Until New Message')");
    await contains(".o-mail-NotificationItem:has(:text('General New Thread'))", { count: 0 });
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
    await contains(
        ".o-mail-Message:has(:text('Selling a training session and selling the products after the training session is more efficient.'))"
    );
    await click(".o-mail-NotificationItem:has(.o-mail-NotificationItem-name:text('General'))");
    await click(".o-mail-Message-actions [title='Expand']");
    await contains(".o-dropdown-item:contains('Create Thread')", { count: 0 });
    await contains(".o-mail-SubChannelPreview:contains('Selling a training session and')");
    await click(".o-mail-SubChannelPreview:contains('Selling a training session and')");
    await contains(".o-mail-DiscussContent-threadName", {
        value: "Selling a training session and",
    });
    await contains(".o-mail-SubChannelPreview:contains('Selling a training session and')", {
        count: 0,
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
    await click(".o-mail-NotificationItem:has(.o-mail-NotificationItem-name:text('General'))");
    await contains(
        ".o-mail-NotificationMessage:text('" +
            serverState.partnerName +
            " started a thread: hello alex.1:00 PM')"
    );
});

test("create sub thread from existing message (slow network)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        model: "discuss.channel",
        res_id: channelId,
        body: "<p>Selling a training session and selling the products after the training session is more efficient.</p>",
    });
    const { promise, resolve } = Promise.withResolvers();
    onRpcAfter("/discuss/channel/sub_channel/create", async () => await promise);
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Message-actions [title='Expand']");
    await click(".o-dropdown-item:contains('Create Thread')");
    await animationFrame();
    resolve();
    await contains(".o-mail-DiscussContent-threadName", {
        value: "Selling a training session and",
    });
    await contains(
        ".o-mail-Message:has(:text('Selling a training session and selling the products after the training session is more efficient.'))"
    );
});

test("create sub thread from sub-thread list", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMemberList"); // wait for auto-open of this panel
    await click("button[title='Threads']");
    await contains(".o-mail-SubChannelList:text('This conversation has no threads yet.')");
    await click("button[aria-label='Create Thread']");
    await contains(".o-mail-DiscussContent-threadName", { value: "New Thread" });
    await click(".o-mail-NotificationItem:has(.o-mail-NotificationItem-name:text('General'))");
    await contains(".o-mail-DiscussContent-threadName", { value: "General" });
    await click(".o-mail-DiscussContent-header button[title='Threads']");
    await insertText(
        ".o-mail-ActionPanel:has(.o-mail-SubChannelList) .o-mail-SearchInput input",
        "MyEpicThread"
    );
    await contains(".o-mail-SubChannelList:text('No threads found.')");
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
    await click(".o-mail-NotificationItem:has(:text('ThreadOne'))");
    await contains(".o-mail-DiscussContent-threadName", { value: "ThreadOne" });
    await click("button[title='Threads']");
    await insertText(".o-mail-ActionPanel input[placeholder='Search by name']", "ThreadTwo");
    await click(".o-mail-ActionPanel button:text('Create')");
    await click(".o-mail-NotificationItem:has(:text('ThreadTwo'))");
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
    await contains(".o-discuss-ChannelMemberList"); // wait for auto-open of this panel
    await click("button[title='Threads']");
    await insertText(
        ".o-mail-ActionPanel input[placeholder='Search by name']",
        "Sub thread for channel"
    );
    await click(".o-mail-ActionPanel button:text('Create')");
    await click(".o-mail-NotificationItem:has(:text('Sub thread for channel'))");
    await click(".o-mail-MessagingMenu-tab[data-id='chat']");
    await click(".o-mail-NotificationItem:has(:text('Group'))");
    await contains(".o-mail-DiscussContent-threadName", { value: "Group" });
    await click("button[title='Threads']");
    await insertText(
        ".o-mail-ActionPanel input[placeholder='Search by name']",
        "Sub thread for group"
    );
    await click(".o-mail-ActionPanel button:text('Create')");
    await click(".o-mail-MessagingMenu-tab[data-id='channel']");
    await click(".o-mail-NotificationItem:has(:text('Sub thread for group'))");
    await click(".o-mail-MessagingMenu-tab[data-id='chat']");
    await click(".o-mail-NotificationItem:has(:text('Demo'))");
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
    await contains(".o-mail-NotificationItem.o-active:has(:text('General'))");
    await insertText(".o-mail-Composer-input", "@");
    await contains(".o-mail-Composer-suggestion", { count: 2 });
    await contains(".o-mail-Composer-suggestion:has(:text('Mitchell Admin'))");
    await contains(".o-mail-Composer-suggestion:has(:text('p1'))");
    await click(".o-mail-NotificationItem:has(:text('Thread'))");
    await contains(".o-mail-NotificationItem.o-active:has(:text('Thread'))");
    await insertText(".o-mail-Composer-input", "@");
    await contains(".o-mail-Composer-suggestion", { count: 2 });
    await contains(".o-mail-Composer-suggestion:has(:text('Mitchell Admin'))");
    await contains(".o-mail-Composer-suggestion:has(:text('p1'))");
});

test("sub-thread is visually muted when mute is active", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussContent-threadName", { value: "General" });
    await click("button[title='Threads']");
    await click("button[aria-label='Create Thread']");
    await contains(".o-mail-NotificationItem.opacity-50:has(:text('New Thread'))", { count: 0 });
    await click(".o-mail-NotificationItem:has(:text('General New Thread'))");
    await click("button[title='Notification Settings']");
    await hover("button:has(:text('Mute Conversation'))");
    await click(".o-dropdown-item:contains('Until I turn it back on')");
    await contains(".o-mail-NotificationItem.opacity-50:has(:text('New Thread'))");
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
    await click(".o-mail-NotificationMessage a:text('Message 1')");
    await contains(
        ".o_notification:has(.o_notification_bar.bg-danger):text('This thread is no longer available.')"
    );
});

test("Can delete channel thread as author of thread", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const subChannelID = pyEnv["discuss.channel"].create({
        name: "test thread",
        parent_channel_id: channelId,
    });
    await start();
    await openDiscuss(subChannelID);
    await contains(".o-mail-DiscussContent-threadName[title='test thread']");
    await click(".o-mail-NotificationItem:has(:text('test thread')) [title='Channel Actions']");
    await click(".o-dropdown-item:contains('Delete Thread')");
    await click(".modal button:contains('Delete Thread')");
    await contains(".o-mail-DiscussContent-threadName[title='General']");
    await contains(
        `.o-mail-NotificationMessage :text(Mitchell Admin deleted the thread "test thread")`
    );
});

test("can mention all group chat members inside its sub-thread", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Lilibeth" });
    const groupChannelId = pyEnv["discuss.channel"].create({
        name: "Our channel",
        channel_type: "group",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    const groupSubChannelId = pyEnv["discuss.channel"].create({
        name: "New Thread",
        parent_channel_id: groupChannelId,
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
    });
    await start();
    await openDiscuss(groupSubChannelId);
    await insertText(".o-mail-Composer-input", "@");
    await contains(".o-mail-Composer-suggestion", { count: 2 });
});

test("should temporarily repin unpinned thread while it is being viewed", async () => {
    mockDate("2023-06-07T06:07:00");
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "Main Channel",
        channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
    });
    const [subChannelId] = pyEnv["discuss.channel"].create([
        {
            name: "Sub Channel 1",
            parent_channel_id: channelId,
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    unpin_dt: "2023-06-06 06:07:00",
                    last_interest_dt: "2023-06-05 06:07:00",
                }),
            ],
        },
        {
            name: "Sub Channel 2",
            parent_channel_id: channelId,
        },
    ]);
    await start();
    await openDiscuss(subChannelId);
    await contains(".o-mail-NotificationItem:has(:text('Sub Channel 2'))");
    await contains(".o-mail-NotificationItem.o-active:has(:text('Sub Channel 1'))");
    await click(".o-mail-NotificationItem:has(:text('Sub Channel 2'))");
    await contains(".o-mail-NotificationItem:has(:text('Sub Channel 1'))", { count: 0 });
    // Sub channel 1 is expired and disappears when its not active thread
    await contains(".o-mail-NotificationItem.o-active:has(:text('Sub Channel 2'))");
    await click("button[title='Threads']");
    await contains(".o-mail-SubChannelPreview-name:eq(0):text('Sub Channel 2')");
    await contains(".o-mail-SubChannelPreview-name:eq(1):text('Sub Channel 1')");
    await click(".o-mail-SubChannelPreview-name:text('Sub Channel 1')");
    await contains(".o-mail-NotificationItem:has(:text('Sub Channel 2'))");
    await contains(".o-mail-NotificationItem.o-active:has(:text('Sub Channel 1'))");
    // Sub channel 1 is persistently pinned when posting a message
    await insertText(".o-mail-Composer-input", "Batman");
    await click(".o-mail-Composer button[title='Send']:enabled");
    await click(".o-mail-NotificationItem:has(:text('Sub Channel 2'))");
    await contains(".o-mail-NotificationItem:has(:text('Sub Channel 1'))");
    await contains(".o-mail-NotificationItem.o-active:has(:text('Sub Channel 2'))");
});
