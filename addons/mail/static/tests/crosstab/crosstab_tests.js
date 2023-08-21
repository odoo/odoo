/* @odoo-module */

import { click, contains, start, startServer } from "@mail/../tests/helpers/test_utils";

import { patchWithCleanup, triggerHotkey } from "@web/../tests/helpers/utils";

QUnit.module("crosstab");

QUnit.test("Messages are received cross-tab", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
    });
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    tab1.openDiscuss(channelId);
    tab2.openDiscuss(channelId);
    await tab1.insertText(".o-mail-Composer-input", "Hello World!");
    await click("button:contains(Send):not(:disabled)", { target: tab1.target });
    await contains(".o-mail-Message:contains(Hello World!)", 1, { target: tab1.target });
    await contains(".o-mail-Message:contains(Hello World!)", 1, { target: tab2.target });
});

QUnit.test("Delete starred message updates counter", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
    });
    const messageId = pyEnv["mail.message"].create({
        body: "Hello World!",
        model: "discuss.channel",
        res_id: channelId,
        starred_partner_ids: [pyEnv.currentPartnerId],
    });
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    tab1.openDiscuss(channelId);
    tab2.openDiscuss(channelId);
    await contains("button:contains(Starred1)", 1, { target: tab2.target });
    tab1.env.services.rpc("/mail/message/update_content", {
        message_id: messageId,
        body: "",
        attachment_ids: [],
    });
    await contains("button:contains(Starred1)", 0, { target: tab2.target });
});

QUnit.test("Thread rename", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        create_uid: pyEnv.currentUserId,
        name: "General",
    });
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    tab1.openDiscuss(channelId);
    tab2.openDiscuss(channelId);
    await tab1.insertText(".o-mail-Discuss-threadName:not(:disabled)", "Sales", { replace: true });
    triggerHotkey("Enter");
    await contains(".o-mail-Discuss-threadName[title='Sales']", 1, { target: tab2.target });
    await contains(".o-mail-DiscussSidebarChannel:contains(Sales)", 1, { target: tab2.target });
});

QUnit.test("Thread description update", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        create_uid: pyEnv.currentUserId,
        name: "General",
    });
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    tab1.openDiscuss(channelId);
    tab2.openDiscuss(channelId);
    await tab1.insertText(".o-mail-Discuss-threadDescription", "The very best channel", {
        replace: true,
    });
    triggerHotkey("Enter");
    await contains(".o-mail-Discuss-threadDescription[title='The very best channel']", 1, {
        target: tab2.target,
    });
});

QUnit.test("Channel subscription is renewed when channel is added from invite", async (assert) => {
    const pyEnv = await startServer();
    const [, channelId] = pyEnv["discuss.channel"].create([
        { name: "R&D" },
        { name: "Sales", channel_member_ids: [] },
    ]);
    const { env, openDiscuss } = await start();
    patchWithCleanup(env.services["bus_service"], {
        forceUpdateChannels() {
            assert.step("update-channels");
        },
    });
    openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel");
    env.services.orm.call("discuss.channel", "add_members", [[channelId]], {
        partner_ids: [pyEnv.currentPartnerId],
    });
    await contains(".o-mail-DiscussSidebarChannel", 2);
    await new Promise((resolve) => setTimeout(resolve)); // update of channels is debounced
    assert.verifySteps(["update-channels"]);
});

QUnit.test("Channel subscription is renewed when channel is left", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "Sales" });
    const { env, openDiscuss } = await start();
    patchWithCleanup(env.services["bus_service"], {
        forceUpdateChannels() {
            assert.step("update-channels");
        },
    });
    openDiscuss();
    await click(".o-mail-DiscussSidebarChannel .btn[title='Leave this channel']");
    await contains(".o-mail-DiscussSidebarChannel", 0);
    await new Promise((resolve) => setTimeout(resolve)); // update of channels is debounced
    assert.verifySteps(["update-channels"]);
});

QUnit.test("Adding attachments", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "Hogwarts Legacy" });
    const messageId = pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    tab1.openDiscuss(channelId);
    tab2.openDiscuss(channelId);
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "test.txt",
        mimetype: "text/plain",
    });
    tab1.env.services.rpc("/mail/message/update_content", {
        body: "Hello world!",
        attachment_ids: [attachmentId],
        message_id: messageId,
    });
    await contains(".o-mail-AttachmentCard:contains(test.txt)", 1, { target: tab2.target });
});

QUnit.test("Remove attachment from message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "test.txt",
        mimetype: "text/plain",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        body: "Hello World!",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    tab1.openDiscuss(channelId);
    tab2.openDiscuss(channelId);
    await contains(".o-mail-AttachmentCard:contains(test.txt)", 1, { target: tab1.target });
    await click(".o-mail-AttachmentCard-unlink", { target: tab2.target });
    await click(".modal-footer .btn:contains(Ok)", { target: tab2.target });
    await contains(".o-mail-AttachmentCard:contains(test.txt)", 0, { target: tab1.target });
});

QUnit.test("Message delete notification", async () => {
    const pyEnv = await startServer();
    const messageId = pyEnv["mail.message"].create({
        body: "Needaction message",
        model: "discuss.channel",
        res_id: pyEnv.currentPartnerId,
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId], // not needed, for consistency
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_type: "inbox",
        notification_status: "sent",
        res_partner_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    openDiscuss();
    await click("[title='Expand']");
    await click("[title='Mark as Todo']");
    await contains("button:contains(Inbox) .badge");
    await contains("button:contains(Starred) .badge");
    pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.message/delete", {
        message_ids: [messageId],
    });
    await contains(".o-mail-Message", 0);
    await contains("button:contains(Inbox) .badge", 0);
    await contains("button:contains(Starred) .badge", 0);
});
