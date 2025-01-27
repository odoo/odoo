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
import { Deferred, animationFrame } from "@odoo/hoot-mock";
import { Command, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("navigate to sub channel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    // Should access sub-thread after its creation.
    await contains(".o-mail-Discuss-threadName", { value: "General" });
    await click("button[title='Threads']");
    await click("button[aria-label='Create Thread']");
    await contains(".o-mail-Discuss-threadName", { value: "New Thread" });
    // Should access sub-thread when clicking on the menu.
    await click(".o-mail-DiscussSidebarChannel", { name: "General" });
    await contains(".o-mail-Discuss-threadName", { value: "General" });
    await click("button[title='Threads']");
    await click(".o-mail-SubChannelList-thread", { text: "New Thread" });
    await contains(".o-mail-Discuss-threadName", { value: "New Thread" });
    // Should access sub-thread when clicking on the notification.
    await click(".o-mail-DiscussSidebarChannel", { name: "General" });
    await contains(".o-mail-Discuss-threadName", { value: "New Thread" });
    await contains(".o-mail-NotificationMessage", {
        text: `${serverState.partnerName} started a thread: New Thread. See all threads.`,
    });
    await click(".o-mail-NotificationMessage a", { text: "New Thread" });
    await contains(".o-mail-Discuss-threadName", { value: "New Thread" });
});

test("can manually unpin a sub-thread", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    // Open thread so this is pinned
    await contains(".o-mail-Discuss-threadName", { value: "General" });
    await click("button[title='Threads']");
    await click("button[aria-label='Create Thread']");
    await contains(".o-mail-Discuss-threadName", { value: "New Thread" });
    await click("button[title='Unpin Thread']", {
        parent: [".o-mail-DiscussSidebar-item", { text: "New Thread" }],
    });
    await contains(".o-mail-DiscussSidebar-item", { text: "New Thread", count: 0 });
});

test("open sub channel menu from notification", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Discuss-threadName", { value: "General" });
    await click("button[title='Threads']");
    await click("button[aria-label='Create Thread']");
    await contains(".o-mail-Discuss-threadName", { value: "New Thread" });
    await click(".o-mail-DiscussSidebarChannel", { name: "General" });
    await contains(".o-mail-NotificationMessage", {
        text: `${serverState.partnerName} started a thread: New Thread. See all threads.`,
    });
    await click(".o-mail-NotificationMessage a", { text: "See all threads" });
    await contains(".o-mail-SubChannelList");
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
    await click("[title='Create Thread']");
    await contains(".o-mail-Discuss-threadName", { value: "Selling a training session and" });
    await contains(".o-mail-Message", {
        text: "Selling a training session and selling the products after the training session is more efficient.",
    });
    await click(".o-mail-DiscussSidebarChannel", { name: "General" });
    await click(".o-mail-Message-actions [title='Expand']");
    await contains("[title='Create Thread']", { count: 0 });
    await click("[title='View Thread']");
    await contains(".o-mail-Discuss-threadName", { value: "Selling a training session and" });
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
    await click("[title='Create Thread']");
    await animationFrame();
    createSubChannelDef.resolve();
    await contains(".o-mail-Discuss-threadName", { value: "Selling a training session and" });
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
    await contains(".o-mail-Discuss-threadName", { value: "New Thread" });
    await click(".o-mail-DiscussSidebarChannel", { name: "General" });
    await click("button[title='Threads']");
    await insertText(
        ".o-mail-ActionPanel:has(.o-mail-SubChannelList) .o_searchview_input",
        "MyEpicThread"
    );
    await click("button[aria-label='Search button']");
    await contains(".o-mail-SubChannelList", { text: 'No thread named "MyEpicThread"' });
    await click("button[aria-label='Create Thread']");
    await contains(".o-mail-Discuss-threadName", { value: "MyEpicThread" });
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
    await click("button[title='Threads']");
    await insertText(".o-mail-ActionPanel input[placeholder='Search by name']", "ThreadTwo");
    await click(".o-mail-ActionPanel button", { text: "Create" });
    await click(".o-mail-DiscussSidebar-item", { text: "ThreadTwo" });
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
    pyEnv["res.users"].write(serverState.userId, { groups_id: [Command.link(groupId)] });
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { email: "p1@odoo.com", name: "p1" },
        { email: "p2@odoo.com", name: "p2" },
    ]);
    pyEnv["res.users"].create([
        { partner_id: partnerId_1, groups_id: [Command.link(groupId)] },
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
