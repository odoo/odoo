import {
    assertSteps,
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    start,
    startServer,
    step,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { getService, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";

import { rpc } from "@web/core/network/rpc";

describe.current.tags("desktop");
defineMailModels();

test("Messages are received cross-tab", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true });
    await openDiscuss(channelId, { target: env1 });
    await openDiscuss(channelId, { target: env2 });
    await insertText(".o-mail-Composer-input", "Hello World!", { target: env1 });
    await click("button[aria-label='Send']:enabled", { target: env1 });
    await contains(".o-mail-Message-content", { target: env1, text: "Hello World!" });
    await contains(".o-mail-Message-content", { target: env2, text: "Hello World!" });
});

test("Delete starred message updates counter", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello World!",
        model: "discuss.channel",
        message_type: "comment",
        res_id: channelId,
        starred_partner_ids: [serverState.partnerId],
    });
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true });
    await openDiscuss(channelId, { target: env1 });
    await openDiscuss(channelId, { target: env2 });
    await contains(".o-mail-Message", { target: env1, text: "Hello World!" });
    await contains(".o-mail-Message", { target: env2, text: "Hello World!" });
    await contains("button", { target: env2, text: "Starred1" });
    await click(":nth-child(1 of .o-mail-Message) [title='Expand']", { target: env2 });
    await click(".o-mail-Message-moreMenu [title='Delete']", { target: env2 });
    await click("button", { text: "Confirm" }, { target: env2 });
    await contains("button", { count: 0, target: env2, text: "Starred1" });
});

test("Thread rename [REQUIRE FOCUS]", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        create_uid: serverState.userId,
        name: "General",
    });
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true });
    await openDiscuss(channelId, { target: env1 });
    await openDiscuss(channelId, { target: env2 });
    await insertText(".o-mail-Discuss-threadName:enabled", "Sales", {
        replace: true,
        target: env1,
    });
    triggerHotkey("Enter");
    await contains(".o-mail-Discuss-threadName[title='Sales']", { target: env2 });
    await contains(".o-mail-DiscussSidebarChannel", { target: env2, text: "Sales" });
});

test("Thread description update [REQUIRE FOCUS]", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        create_uid: serverState.userId,
        name: "General",
    });
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true });
    await openDiscuss(channelId, { target: env1 });
    await openDiscuss(channelId, { target: env2 });
    await insertText(".o-mail-Discuss-threadDescription", "The very best channel", {
        replace: true,
        target: env1,
    });
    triggerHotkey("Enter");
    await contains(".o-mail-Discuss-threadDescription[title='The very best channel']", {
        target: env2,
    });
});

test.skip("Channel subscription is renewed when channel is added from invite", async () => {
    const now = luxon.DateTime.now();
    mockDate(`${now.year}-${now.month}-${now.day} ${now.hour}:${now.minute}:${now.second}`);
    const pyEnv = await startServer();
    const [, channelId] = pyEnv["discuss.channel"].create([
        { name: "R&D" },
        { name: "Sales", channel_member_ids: [] },
    ]);
    // Patch the date to consider those channels as already known by the server
    // when the client starts.
    const later = now.plus({ seconds: 10 });
    mockDate(
        `${later.year}-${later.month}-${later.day} ${later.hour}:${later.minute}:${later.second}`
    );
    await start();
    patchWithCleanup(getService("bus_service"), {
        forceUpdateChannels() {
            step("update-channels");
        },
    });
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel");
    getService("orm").call("discuss.channel", "add_members", [[channelId]], {
        partner_ids: [serverState.partnerId],
    });
    await contains(".o-mail-DiscussSidebarChannel", { count: 2 });
    await assertSteps(["update-channels"]); // FIXME: sometimes 1 or 2 update-channels
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
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true });
    await openDiscuss(channelId, { target: env1 });
    await openDiscuss(channelId, { target: env2 });
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "test.txt",
        mimetype: "text/plain",
    });
    rpc("/mail/message/update_content", {
        body: "Hello world!",
        attachment_ids: [attachmentId],
        message_id: messageId,
    });
    await contains(".o-mail-AttachmentCard", { target: env2, text: "test.txt" });
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
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true });
    await openDiscuss(channelId, { target: env1 });
    await openDiscuss(channelId, { target: env2 });
    await contains(".o-mail-AttachmentCard", { target: env1, text: "test.txt" });
    await click(".o-mail-AttachmentCard-unlink", { target: env2 });
    await click(".modal-footer .btn", { text: "Ok", target: env2 });
    await contains(".o-mail-AttachmentCard", { count: 0, target: env1, text: "test.txt" });
});

test("Message delete notification", async () => {
    const pyEnv = await startServer();
    const messageId = pyEnv["mail.message"].create({
        body: "Needaction message",
        model: "res.partner",
        res_id: serverState.partnerId,
        needaction: true,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_type: "inbox",
        notification_status: "sent",
        res_partner_id: serverState.partnerId,
    });
    await start();
    await openDiscuss();
    await click("[title='Mark as Todo']");
    await contains("button", { text: "Inbox", contains: [".badge", { text: "1" }] });
    await contains("button", { text: "Starred", contains: [".badge", { text: "1" }] });
    const [partner] = pyEnv["res.partner"].read(serverState.partnerId);
    pyEnv["bus.bus"]._sendone(partner, "mail.message/delete", {
        message_ids: [messageId],
    });
    await contains(".o-mail-Message", { count: 0 });
    await contains("button", { text: "Inbox", contains: [".badge", { count: 0 }] });
    await contains("button", { text: "Starred", contains: [".badge", { count: 0 }] });
});
