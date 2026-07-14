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
    await insertText(`${env1.selector} .o-mail-Composer-input`, "Hello World!");
    await click(`${env1.selector} button[aria-label='Send']:enabled`);
    await contains(`${env1.selector} .o-mail-Message-content`, { text: "Hello World!" });
    await contains(`${env2.selector} .o-mail-Message-content`, { text: "Hello World!" });
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
    await contains(`${env1.selector} .o-mail-Message`, { text: "Hello World!" });
    await contains(`${env2.selector} .o-mail-Message`, { text: "Hello World!" });
    await contains(`${env2.selector} button`, { text: "Starred1" });
    await click(`${env2.selector} :nth-child(1 of .o-mail-Message) [title='Expand']`);
    await click(`${env2.selector} .o-mail-Message-moreMenu [title='Delete']`);
    await click(`${env2.selector} button`, { text: "Confirm" });
    await contains(`${env2.selector} button`, { count: 0, text: "Starred1" });
});

test.tags("focus required");
test("Thread rename", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        create_uid: serverState.userId,
        name: "General",
    });
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true });
    await openDiscuss(channelId, { target: env1 });
    await openDiscuss(channelId, { target: env2 });
    await insertText(`${env1.selector} .o-mail-Discuss-threadName:enabled`, "Sales", {
        replace: true,
    });
    triggerHotkey("Enter");
    await contains(`${env2.selector} .o-mail-Discuss-threadName[title='Sales']`);
    await contains(`${env2.selector} .o-mail-DiscussSidebarChannel`, { text: "Sales" });
});

test.tags("focus required");
test("Thread description update", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        create_uid: serverState.userId,
        name: "General",
    });
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true });
    await openDiscuss(channelId, { target: env1 });
    await openDiscuss(channelId, { target: env2 });
    await insertText(
        `${env1.selector} .o-mail-Discuss-threadDescription`,
        "The very best channel",
        {
            replace: true,
        }
    );
    triggerHotkey("Enter");
    await contains(
        `${env2.selector} .o-mail-Discuss-threadDescription[title='The very best channel']`
    );
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
    await contains(
        `${env2.selector} .o-mail-AttachmentCard:not(.o-isUploading):contains(test.txt)`
    );
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
    await contains(`${env1.selector} .o-mail-AttachmentCard`, { text: "test.txt" });
    await click(`${env2.selector} .o-mail-AttachmentCard-unlink`);
    await click(`${env2.selector} .modal-footer .btn`, { text: "Ok" });
    await contains(`${env1.selector} .o-mail-AttachmentCard`, { count: 0, text: "test.txt" });
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
