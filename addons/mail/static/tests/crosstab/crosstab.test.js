/** @odoo-module alias=@mail/../tests/crosstab/crosstab_tests default=false */
const test = QUnit.test; // QUnit.test()

import { rpc } from "@web/core/network/rpc";

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { openDiscuss, start } from "@mail/../tests/helpers/test_utils";

import { patchDate, patchWithCleanup, triggerHotkey } from "@web/../tests/helpers/utils";
import { assertSteps, click, contains, insertText, step } from "@web/../tests/utils";

QUnit.module("crosstab");

test("Messages are received cross-tab", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
    });
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    tab1.openDiscuss(channelId);
    tab2.openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "Hello World!", { target: tab1.target });
    await click("button:enabled", { target: tab1.target, text: "Send" });
    await contains(".o-mail-Message-content", { target: tab1.target, text: "Hello World!" });
    await contains(".o-mail-Message-content", { target: tab2.target, text: "Hello World!" });
});

test("Delete starred message updates counter", async () => {
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
    await contains("button", { target: tab2.target, text: "Starred1" });

    rpc("/mail/message/update_content", {
        message_id: messageId,
        body: "",
        attachment_ids: [],
    });
    await contains("button", { count: 0, target: tab2.target, text: "Starred1" });
});

test("Thread rename", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        create_uid: pyEnv.currentUserId,
        name: "General",
    });
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    tab1.openDiscuss(channelId);
    tab2.openDiscuss(channelId);
    await insertText(".o-mail-Discuss-threadName:enabled", "Sales", {
        replace: true,
        target: tab1.target,
    });
    triggerHotkey("Enter");
    await contains(".o-mail-Discuss-threadName[title='Sales']", { target: tab2.target });
    await contains(".o-mail-DiscussSidebarChannel", { target: tab2.target, text: "Sales" });
});

test("Thread description update", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        create_uid: pyEnv.currentUserId,
        name: "General",
    });
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    tab1.openDiscuss(channelId);
    tab2.openDiscuss(channelId);
    await insertText(".o-mail-Discuss-threadDescription", "The very best channel", {
        replace: true,
        target: tab1.target,
    });
    triggerHotkey("Enter");
    await contains(".o-mail-Discuss-threadDescription[title='The very best channel']", {
        target: tab2.target,
    });
});

test("Channel subscription is renewed when channel is added from invite", async () => {
    const pyEnv = await startServer();
    const [, channelId] = pyEnv["discuss.channel"].create([
        { name: "R&D" },
        { name: "Sales", channel_member_ids: [] },
    ]);
    // Patch the date to consider those channels as already known by the server
    // when the client starts.
    const later = luxon.DateTime.now().plus({ seconds: 2 });
    patchDate(later.year, later.month, later.day, later.hour, later.minute, later.second);
    const { env } = await start();
    patchWithCleanup(env.services["bus_service"], {
        forceUpdateChannels() {
            step("update-channels");
        },
    });
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel");
    env.services.orm.call("discuss.channel", "add_members", [[channelId]], {
        partner_ids: [pyEnv.currentPartnerId],
    });
    await contains(".o-mail-DiscussSidebarChannel", { count: 2 });
    await assertSteps(["update-channels"]);
});

test("Adding attachments", async () => {
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
    rpc("/mail/message/update_content", {
        body: "Hello world!",
        attachment_ids: [attachmentId],
        message_id: messageId,
    });
    await contains(".o-mail-AttachmentCard", { target: tab2.target, text: "test.txt" });
});

test("Remove attachment from message", async () => {
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
    await contains(".o-mail-AttachmentCard", { target: tab1.target, text: "test.txt" });

    await click(".o-mail-AttachmentCard-unlink", { target: tab2.target });
    await click(".modal-footer .btn", { text: "Ok", target: tab2.target });
    await contains(".o-mail-AttachmentCard", { count: 0, target: tab1.target, text: "test.txt" });
});

test("Message delete notification", async () => {
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
    await start();
    await openDiscuss();
    await click("[title='Expand']");
    await click("[title='Mark as Todo']");
    await contains("button", { text: "Inbox", contains: [".badge", { text: "1" }] });
    await contains("button", { text: "Starred", contains: [".badge", { text: "1" }] });
    pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.message/delete", {
        message_ids: [messageId],
    });
    await contains(".o-mail-Message", { count: 0 });
    await contains("button", { text: "Inbox", contains: [".badge", { count: 0 }] });
    await contains("button", { text: "Starred", contains: [".badge", { count: 0 }] });
});
