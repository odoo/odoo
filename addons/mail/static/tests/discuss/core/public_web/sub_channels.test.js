import {
    actionPanel,
    click,
    contains as mailContains,
    defineMailModels,
    hover,
    insertText,
    onRpcAfter,
    openDiscuss,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { insertTextInComposer } from "@mail/../tests/mail_test_helpers_composer";
import { describe, press, test, waitFor, waitForNone } from "@odoo/hoot";
import { animationFrame, mockDate } from "@odoo/hoot-mock";
import { Command, contains, serverState } from "@web/../tests/web_test_helpers";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { user } from "@web/core/user";

describe.current.tags("desktop");
defineMailModels();

/** @param {string} name */
const sideChannel = (name) =>
    `.o-mail-DiscussSideChannel:has(.o-mail-ActionPanel-header p:text('${name}')):count(1)`;

test("navigate to sub channel", async () => {
    mockDate("2025-01-01 12:00:00", +1);
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    // Should open sub-thread in split view after its creation.
    await mailContains(".o-mail-DiscussContent-threadName", { value: "General" });
    await click("button[title='Threads']");
    await click("button[aria-label='Create Thread']");
    await waitFor(sideChannel("New Thread"));
    await waitForNone(".o-mail-SubChannelList");
    await mailContains(".o-mail-DiscussContent-threadName", { value: "General" });
    // Should open sub-thread in split view when clicking on the thread list.
    await click(".o-mail-DiscussSideChannel button[title='Close panel']");
    await waitForNone(".o-mail-DiscussSideChannel");
    await click("button[title='Threads']");
    await click(".o-mail-SubChannelPreview .o-mail-SubChannelPreview-name:text('New Thread')");
    await waitFor(sideChannel("New Thread"));
    await mailContains(".o-mail-DiscussContent-threadName", { value: "General" });
    // Should open sub-thread in split view when clicking on the notification.
    await click(".o-mail-DiscussSideChannel button[title='Close panel']");
    await waitForNone(".o-mail-DiscussSideChannel");
    const messages = pyEnv["mail.message"].search_read([["message_type", "=", "notification"]]);
    const time = deserializeDateTime(messages.at(-1).date).toLocaleString(
        luxon.DateTime.TIME_SIMPLE,
        { locale: user.lang }
    );
    await waitFor(
        `.o-mail-NotificationMessage:text('${serverState.partnerName} started a thread: New Thread. ${time}'):count(1)`
    );
    await click(".o-mail-NotificationMessage a:text('New Thread')");
    await waitFor(sideChannel("New Thread"));
    await mailContains(".o-mail-DiscussContent-threadName", { value: "General" });
    // Should access sub-thread in full view from the split view.
    await click(".o-mail-DiscussSideChannel button[title='Open in Full View']");
    await mailContains(".o-mail-DiscussContent-threadName", { value: "New Thread" });
    await waitForNone(".o-mail-DiscussSideChannel");
});

test("thread list loads the threads of the opened channel", async () => {
    const pyEnv = await startServer();
    const [generalId, salesId] = pyEnv["discuss.channel"].create([
        { name: "General" },
        { name: "Sales" },
    ]);
    // not joined, so it is only known once the thread list loads it
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: partnerId })],
        name: "Sales Thread",
        parent_channel_id: salesId,
    });
    await start();
    await openDiscuss(generalId);
    await waitFor(`${actionPanel("Members")}:count(1)`); // wait for auto-open of this panel
    // closing it stops its auto-open, so the thread list stays open across conversations
    await click("button[title='Members']");
    await click("button[title='Threads']");
    await waitFor(".o-mail-SubChannelList :text('This conversation has no threads yet.')");
    await click(".o-mail-NotificationItem-name:text(Sales)");
    await mailContains(".o-mail-DiscussContent-threadName", { value: "Sales" });
    await waitFor(".o-mail-SubChannelPreview:has(:text('Sales Thread')):count(1)");
});

test("thread list clears its search when another channel is opened", async () => {
    const pyEnv = await startServer();
    const [generalId, salesId] = pyEnv["discuss.channel"].create([
        { name: "General" },
        { name: "Sales" },
    ]);
    pyEnv["discuss.channel"].create([
        { name: "General Thread", parent_channel_id: generalId },
        { name: "Sales Thread", parent_channel_id: salesId },
    ]);
    await start();
    await openDiscuss(generalId);
    await waitFor(`${actionPanel("Members")}:count(1)`); // wait for auto-open of this panel
    // closing it stops its auto-open, so the thread list stays open across conversations
    await click("button[title='Members']");
    await click("button[title='Threads']");
    await insertText(".o-mail-SearchInput input[placeholder='Search by name']", "Thread");
    await waitFor(".o-mail-SubChannelPreview:has(:text('General Thread')):count(1)");
    await click(".o-mail-NotificationItem-name:text(Sales)");
    await mailContains(".o-mail-DiscussContent-threadName", { value: "Sales" });
    // the search of the previous channel is cleared and its threads replaced
    await mailContains(".o-mail-SearchInput input[placeholder='Search by name']", { value: "" });
    await waitFor(".o-mail-SubChannelPreview:has(:text('Sales Thread')):count(1)");
    await waitFor(".o-mail-SubChannelPreview:count(1)");
});

test("picking a thread from the thread list keeps the members panel opening by default", async () => {
    const pyEnv = await startServer();
    const [generalId] = pyEnv["discuss.channel"].create([{ name: "General" }, { name: "Sales" }]);
    pyEnv["discuss.channel"].create({ name: "General Thread", parent_channel_id: generalId });
    await start();
    await openDiscuss(generalId);
    await waitFor(`${actionPanel("Members")}:count(1)`); // wait for auto-open of this panel
    await click("button[title='Threads']");
    await click(".o-mail-SubChannelPreview-name:text('General Thread')");
    await waitFor(sideChannel("General Thread"));
    await mailContains(".o-mail-DiscussContent-threadName", { value: "General" });
    await click(".o-mail-NotificationItem-name:text(Sales)");
    await mailContains(".o-mail-DiscussContent-threadName", { value: "Sales" });
    await waitFor(`${actionPanel("Members")}:count(1)`);
});

test("side channel covered by another panel is closed", async () => {
    const pyEnv = await startServer();
    const [generalId] = pyEnv["discuss.channel"].create([{ name: "General" }, { name: "Sales" }]);
    const messageId = pyEnv["mail.message"].create({
        body: "Message to pin",
        message_type: "comment",
        model: "discuss.channel",
        res_id: generalId,
    });
    pyEnv["discuss.channel"].set_message_pin(generalId, messageId, true);
    await start();
    await openDiscuss(generalId);
    await waitFor(`${actionPanel("Members")}:count(1)`); // wait for auto-open of this panel
    await click("button[title='Threads']");
    await click("button[aria-label='Create Thread']");
    await waitFor(sideChannel("New Thread"));
    await click(".o-mail-DiscussSideChannel button[title='Close panel']");
    await waitForNone(".o-mail-DiscussSideChannel");
    // panel stack: members, side channel, then pinned messages replaces the side channel
    await click("button[title='Members']");
    await waitFor(`${actionPanel("Members")}:count(1)`);
    await click(".o-mail-DiscussContent-main .o-mail-NotificationMessage a:text('New Thread')");
    await waitFor(sideChannel("New Thread"));
    await click(
        ".o-mail-DiscussContent-main .o-mail-NotificationMessage a[data-oe-type='pin-menu']"
    );
    await waitFor(`${actionPanel("Pinned Messages")}:count(1)`);
    await waitForNone(".o-mail-DiscussSideChannel");
    // panel stack: members, pinned messages, side channel, then pinned messages again
    await click(".o-mail-DiscussContent-main .o-mail-NotificationMessage a:text('New Thread')");
    await waitFor(sideChannel("New Thread"));
    await click(
        ".o-mail-DiscussContent-main .o-mail-NotificationMessage a[data-oe-type='pin-menu']"
    );
    await waitFor(`${actionPanel("Pinned Messages")}:count(1)`);
    await waitForNone(".o-mail-DiscussSideChannel");
    await click("button[title='Hide Pinned Messages']");
    await waitFor(`${actionPanel("Members")}:count(1)`);
    await click(".o-mail-DiscussContent-main .o-mail-NotificationMessage a:text('New Thread')");
    await waitFor(sideChannel("New Thread"));
    await click(".o-mail-NotificationItem-name:text(Sales)");
    await mailContains(".o-mail-DiscussContent-threadName", { value: "Sales" });
    await waitFor(`${actionPanel("Members")}:count(1)`);
    await click("button[title='Members']");
    await waitForNone(".o-mail-ActionPanel");
});

test("can manually unpin a sub-thread", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    // Open thread so this is pinned
    await mailContains(".o-mail-DiscussContent-threadName", { value: "General" });
    await click("button[title='Threads']");
    await click("button[aria-label='Create Thread']");
    await waitFor(sideChannel("New Thread"));
    await click(
        ".o-mail-MessagingMenuItem:has(:text('Gene… New Thread')) [title='Channel Actions']"
    );
    await click(".o-dropdown-item:text('Hide Until New Message')");
    await waitForNone(".o-mail-NotificationItem:has(:text('Gene… New Thread'))");
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
    await hover(".o-mail-Message");
    await click(".o-mail-Message-actions [title='Expand']");
    await click(".o-dropdown-item:contains('Create Thread')");
    await waitFor(sideChannel("Selling a training session and"));
    await mailContains(".o-mail-DiscussContent-threadName", { value: "General" });
    await waitFor(
        ".o-mail-DiscussSideChannel .o-mail-Message:has(:text('Selling a training session and selling the products after the training session is more efficient.')):count(1)"
    );
    await click(".o-mail-DiscussSideChannel button[title='Close panel']");
    await waitForNone(".o-mail-DiscussSideChannel");
    await hover(".o-mail-Message");
    await click(".o-mail-Message-actions [title='Expand']");
    await waitForNone(".o-dropdown-item:contains('Create Thread')");
    await waitFor(".o-mail-SubChannelPreview:contains('Selling a training session and'):count(1)");
    await click(".o-mail-SubChannelPreview:contains('Selling a training session and')");
    await waitFor(sideChannel("Selling a training session and"));
    await mailContains(".o-mail-DiscussContent-threadName", { value: "General" });
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
    await hover(".o-mail-Message");
    await click(".o-mail-Message-actions [title='Expand']");
    await click(".o-dropdown-item:contains('Create Thread')");
    await mailContains(".o-mail-DiscussContent-threadName", { value: "hello alex" });
    await click(".o-mail-NotificationItem:has(.o-mail-NotificationItem-name:text('General'))");
    await mailContains(
        ".o-mail-NotificationMessage:text('" +
            serverState.partnerName +
            " started a thread: hello alex. 1:00 PM')"
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
    await hover(".o-mail-Message");
    await click(".o-mail-Message-actions [title='Expand']");
    await click(".o-dropdown-item:contains('Create Thread')");
    await animationFrame();
    resolve();
    await waitFor(sideChannel("Selling a training session and"));
    await waitFor(
        ".o-mail-DiscussSideChannel .o-mail-Message:has(:text('Selling a training session and selling the products after the training session is more efficient.')):count(1)"
    );
});

test("create sub thread from sub-thread list", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await waitFor(`${actionPanel("Members")}:count(1)`); // wait for auto-open of this panel
    await click("button[title='Threads']");
    await waitFor(".o-mail-SubChannelList:text('This conversation has no threads yet.'):count(1)");
    await click("button[aria-label='Create Thread']");
    await waitFor(sideChannel("New Thread"));
    await waitForNone(".o-mail-SubChannelList");
    await mailContains(".o-mail-DiscussContent-threadName", { value: "General" });
    // panel actions are compacted in a dropdown among the header actions while side channel is open
    await waitForNone(".o-mail-DiscussContent-panelActions");
    await waitForNone(".o-mail-DiscussContent-header button[title='Threads']");
    await click(".o-mail-DiscussContent-headerActions button[title='More Actions']");
    await click(".o-dropdown-item:text('Threads')");
    await insertText(
        ".o-mail-ActionPanel:has(.o-mail-SubChannelList) .o-mail-SearchInput input",
        "MyEpicThread"
    );
    await waitFor(".o-mail-SubChannelList:text('No threads found.'):count(1)");
    await click("button[aria-label='Create Thread']");
    await waitFor(sideChannel("MyEpicThread"));
    await waitForNone(".o-mail-SubChannelList");
    await mailContains(".o-mail-DiscussContent-threadName", { value: "General" });
});

test("search messages hotkey while panel actions are compacted", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await waitFor(`${actionPanel("Members")}:count(1)`); // wait for auto-open of this panel
    await click("button[title='Threads']");
    await click("button[aria-label='Create Thread']");
    await waitFor(sideChannel("New Thread"));
    await waitForNone(".o-mail-DiscussContent-panelActions");
    await press("alt+f");
    await waitFor(`${actionPanel("Search Messages")}:count(1)`);
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
    await contains(".o-mail-NotificationItem:has(:text('ThreadOne')):count(1)").click();
    await mailContains(".o-mail-DiscussContent-threadName", { value: "ThreadOne" });
    await contains("button[title='Threads']:count(1)").click();
    await insertText(".o-mail-ActionPanel input[placeholder='Search by name']", "ThreadTwo");
    await contains(".o-mail-ActionPanel button:text('Create'):count(1)").click();
    await contains(".o-mail-NotificationItem:has(:text('ThreadTwo')):count(1)").click();
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
    await waitFor(`${actionPanel("Members")}:count(1)`); // wait for auto-open of this panel
    await contains("button[title='Threads']:count(1)").click();
    await insertText(
        ".o-mail-ActionPanel input[placeholder='Search by name']",
        "Sub thread for channel"
    );
    await contains(".o-mail-ActionPanel button:text('Create'):count(1)").click();
    await contains(
        ".o-mail-NotificationItem:has(:text('Sub thread for channel')):count(1)"
    ).click();
    await contains(".o-mail-MessagingMenu-tab[data-id='chat']:count(1)").click();
    await contains(".o-mail-NotificationItem:has(:text('Group')):count(1)").click();
    await mailContains(".o-mail-DiscussContent-threadName", { value: "Group" });
    await contains("button[title='Threads']:count(1)").click();
    await insertText(
        ".o-mail-ActionPanel input[placeholder='Search by name']",
        "Sub thread for group"
    );
    await contains(".o-mail-ActionPanel button:text('Create'):count(1)").click();
    await contains(".o-mail-MessagingMenu-tab[data-id='channel']:count(1)").click();
    await contains(".o-mail-NotificationItem:has(:text('Sub thread for group')):count(1)").click();
    await contains(".o-mail-MessagingMenu-tab[data-id='chat']:count(1)").click();
    await contains(".o-mail-NotificationItem:has(:text('Demo')):count(1)").click();
    await waitForNone("button[title='Threads']");
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
    await waitFor(".o-mail-NotificationItem.o-active:has(:text('General')):count(1)");
    await insertTextInComposer(".o-mail-Composer", "@");
    await waitFor(".o-mail-Composer-suggestion:count(2)");
    await waitFor(".o-mail-Composer-suggestion:has(:text('Mitchell Admin')):count(1)");
    await waitFor(".o-mail-Composer-suggestion:has(:text('p1')):count(1)");
    await contains(".o-mail-NotificationItem:has(:text('Thread')):count(1)").click();
    await waitFor(".o-mail-NotificationItem.o-active:has(:text('Thread')):count(1)");
    await insertTextInComposer(".o-mail-Composer", "@");
    await waitFor(".o-mail-Composer-suggestion:count(2)");
    await waitFor(".o-mail-Composer-suggestion:has(:text('Mitchell Admin')):count(1)");
    await waitFor(".o-mail-Composer-suggestion:has(:text('p1')):count(1)");
});

test("sub-thread is visually muted when mute is active", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await mailContains(".o-mail-DiscussContent-threadName", { value: "General" });
    await contains("button[title='Threads']:count(1)").click();
    await contains("button[aria-label='Create Thread']:count(1)").click();
    await waitForNone(".o-mail-NotificationItem.opacity-50:has(:text('New Thread'))");
    await contains(".o-mail-NotificationItem:has(:text('Gene… New Thread')):count(1)").click();
    await contains("button[title='Notification Settings']:count(1)").click();
    await hover("button:has(:text('Mute Conversation'))");
    await contains(".o-dropdown-item:contains('Until I turn it back on'):count(1)").click();
    await waitFor(".o-mail-NotificationItem.opacity-50:has(:text('New Thread')):count(1)");
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
    await contains(".o-mail-NotificationMessage a:text('Message 1'):count(1)").click();
    await waitFor(
        ".o_notification:has(.o_notification_bar.bg-danger):text('This thread is no longer available.'):count(1)"
    );
});

test("Renaming a thread should update the message notification in parent channel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await mailContains(".o-mail-DiscussContent-threadName", { value: "General" });
    await contains("button[title='Threads']:count(1)").click();
    await contains("button[aria-label='Create Thread']:count(1)").click();
    await contains(".o-mail-DiscussSideChannel button[title='Open in Full View']:count(1)").click();
    await waitFor("input.o-mail-DiscussContent-threadName:value(New Thread):count(1)");
    await insertText(".o-mail-DiscussContent-threadName:enabled", "Renamed Thread", {
        replace: true,
    });
    triggerHotkey("Enter");
    await contains(".o-mail-NotificationItem-name:text(General):count(1)").click();
    await waitFor(".o-mail-NotificationMessage a:text('Renamed Thread'):count(1)");
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
    await waitFor(".o-mail-DiscussContent-threadName[title='test thread']:count(1)");
    await click(".o-mail-NotificationItem:has(:text('test thread')) [title='Channel Actions']");
    await click(".o-dropdown-item:contains('Delete Thread')");
    await click(".modal button:contains('Delete Thread')");
    await waitFor(".o-mail-DiscussContent-threadName[title='General']:count(1)");
    await waitFor(
        `.o-mail-NotificationMessage :text(Mitchell Admin deleted the thread "test thread"):count(1)`
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
    await insertTextInComposer(".o-mail-Composer", "@");
    await waitFor(".o-mail-Composer-suggestion:count(2)");
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
    await waitFor(".o-mail-NotificationItem:has(:text('Sub Channel 2')):count(1)");
    await waitFor(".o-mail-NotificationItem.o-active:has(:text('Sub Channel 1')):count(1)");
    await click(".o-mail-NotificationItem:has(:text('Sub Channel 2'))");
    await waitForNone(".o-mail-NotificationItem:has(:text('Sub Channel 1'))");
    // Sub channel 1 is expired and disappears when its not active thread
    await waitFor(".o-mail-NotificationItem.o-active:has(:text('Sub Channel 2')):count(1)");
    await click("button[title='Threads']");
    await waitFor(".o-mail-SubChannelPreview-name:eq(0):text('Sub Channel 2'):count(1)");
    await waitFor(".o-mail-SubChannelPreview-name:eq(1):text('Sub Channel 1'):count(1)");
    await click(".o-mail-SubChannelPreview-name:text('Sub Channel 1')");
    await waitFor(".o-mail-NotificationItem:has(:text('Sub Channel 2')):count(1)");
    await waitFor(".o-mail-NotificationItem.o-active:has(:text('Sub Channel 1')):count(1)");
    // Sub channel 1 is persistently pinned when posting a message
    await insertTextInComposer(".o-mail-Composer", "Batman");
    await click(".o-mail-Composer button[title='Send']:enabled");
    await click(".o-mail-NotificationItem:has(:text('Sub Channel 2'))");
    await waitFor(".o-mail-NotificationItem:has(:text('Sub Channel 1')):count(1)");
    await waitFor(".o-mail-NotificationItem.o-active:has(:text('Sub Channel 2')):count(1)");
});

test("pin notification in side channel opens its pinned messages in full view", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Parent message",
        model: "discuss.channel",
        pinned_at: "2023-04-03 08:15:04",
        res_id: channelId,
    });
    const subChannelId = pyEnv["discuss.channel"].create({
        name: "ThreadOne",
        parent_channel_id: channelId,
    });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: subChannelId,
    });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Threads']");
    await click(".o-mail-SubChannelPreview .o-mail-SubChannelPreview-name:text('ThreadOne')");
    await waitFor(sideChannel("ThreadOne"));
    await hover(".o-mail-DiscussSideChannel .o-mail-Message");
    await click(".o-mail-DiscussSideChannel .o-mail-Message [title='Expand']");
    await click(".dropdown-item:text('Pin')");
    await click(".modal-footer button:text('Pin Message')");
    await click(
        ".o-mail-DiscussSideChannel .o-mail-NotificationMessage a[data-oe-type='pin-menu']:text('all pinned messages')"
    );
    await mailContains(".o-mail-DiscussContent-threadName", { value: "ThreadOne" });
    await waitForNone(".o-mail-DiscussSideChannel");
    await waitFor(
        `${actionPanel("Pinned Messages")} .o-mail-Message:has(:text('Hello world!')):count(1)`
    );
    await waitForNone(
        `${actionPanel("Pinned Messages")} .o-mail-Message:has(:text('Parent message'))`
    );
});

test.tags("focus required");
test("escape in side channel composer discards reply, then closes the panel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const subChannelId = pyEnv["discuss.channel"].create({
        name: "ThreadOne",
        parent_channel_id: channelId,
    });
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "Hello world!",
        message_type: "comment",
        model: "discuss.channel",
        res_id: subChannelId,
    });
    await start();
    await openDiscuss(channelId);
    await click("button[title='Threads']");
    await click(".o-mail-SubChannelPreview .o-mail-SubChannelPreview-name:text('ThreadOne')");
    await waitFor(sideChannel("ThreadOne"));
    await hover(".o-mail-DiscussSideChannel .o-mail-Message");
    await click(".o-mail-DiscussSideChannel .o-mail-Message [title='Expand']");
    await click(".o-dropdown-item:text('Reply')");
    await waitFor(".o-mail-DiscussSideChannel .o-mail-Composer-replyingToJumpClickable");
    await waitFor(".o-mail-DiscussSideChannel .o-mail-Composer-html:focus");
    await triggerHotkey("Escape");
    await waitForNone(".o-mail-DiscussSideChannel .o-mail-Composer-replyingToJumpClickable");
    await waitFor(sideChannel("ThreadOne"));
    await animationFrame();
    await waitFor(".o-mail-DiscussSideChannel .o-mail-Composer-html:focus");
    await triggerHotkey("Escape");
    await waitForNone(".o-mail-DiscussSideChannel");
    await waitFor(".o-mail-Composer-html:focus");
});
