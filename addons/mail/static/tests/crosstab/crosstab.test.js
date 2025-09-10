import {
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";

import { inputFiles } from "@web/../tests/utils";
import {
    asyncStep,
    getService,
    mockService,
    serverState,
    waitForSteps,
} from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("Messages are received cross-tab", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true });
    await openDiscuss(channelId, { target: env1 });
    await openDiscuss(channelId, { target: env2 });
    await contains(`${env1.selector} .o-mail-Thread:contains('Welcome to #General!')`); // wait for loaded and focus in input
    await contains(`${env2.selector} .o-mail-Thread:contains('Welcome to #General!')`); // wait for loaded and focus in input
    await insertText(`${env1.selector} .o-mail-Composer-input`, "Hello World!");
    await press("Enter");
    await contains(`${env1.selector} .o-mail-Message-content`, { text: "Hello World!" });
    await contains(`${env2.selector} .o-mail-Message-content`, { text: "Hello World!" });
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
    await insertText(`${env1.selector} .o-mail-DiscussContent-threadName:enabled`, "Sales", {
        replace: true,
    });
    triggerHotkey("Enter");
    await contains(`${env2.selector} .o-mail-DiscussContent-threadName[title='Sales']`);
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
        `${env1.selector} .o-mail-DiscussContent-threadDescription`,
        "The very best channel",
        {
            replace: true,
        }
    );
    triggerHotkey("Enter");
    await contains(
        `${env2.selector} .o-mail-DiscussContent-threadDescription[title='The very best channel']`
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
    mockService("bus_service", {
        forceUpdateChannels() {
            asyncStep("update-channels");
        },
    });
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarChannel");
    getService("orm").call("discuss.channel", "add_members", [[channelId]], {
        partner_ids: [serverState.partnerId],
    });
    await contains(".o-mail-DiscussSidebarChannel", { count: 2 });
    await waitForSteps(["update-channels"]); // FIXME: sometimes 1 or 2 update-channels
});

test("Adding attachments", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "Hogwarts Legacy" });
    pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true });
    await openDiscuss(channelId, { target: env1 });
    await openDiscuss(channelId, { target: env2 });
    const file = new File(["file content"], "test.txt", { type: "text/plain" });
    await contains(`${env1.selector} .o-mail-Message:contains('Hello world!')`);
    await contains(`${env2.selector} .o-mail-Message:contains('Hello world!')`);
    await click(`${env1.selector} .o-mail-Message button[title='Edit']`);
    await click(`${env1.selector} .o-mail-Message .o-mail-Composer button[title='More Actions']`);
    await click(`${env1.selector} .o_popover button[name='upload-files']`);
    await inputFiles(`${env1.selector} .o-mail-Message .o-mail-Composer .o_input_file`, [file]);
    await contains(
        `${env1.selector} .o-mail-AttachmentContainer:not(.o-isUploading):contains(test.txt) .fa-check`
    );
    await click(`${env1.selector} .o-mail-Message .o-mail-Composer button[data-type='save']`);

    await contains(
        `${env2.selector} .o-mail-AttachmentContainer:not(.o-isUploading):contains(test.txt)`
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
    await click(`${env2.selector} .o-mail-Attachment-unlink`);
    await click(`${env2.selector} .modal-footer .btn`, { text: "Ok" });
    await contains(`${env1.selector} .o-mail-AttachmentCard`, { count: 0, text: "test.txt" });
});

test("Message (hard) delete notification", async () => {
    // Note: This isn't a notification from when user click on "Delete message" action:
    // this happens when mail_message server record is effectively deleted (unlink)
    const pyEnv = await startServer();
    pyEnv["res.users"].write(serverState.userId, { notification_type: "inbox" });
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
    await openDiscuss("mail.box_inbox");
    await click("[title='Add Star']");
    await contains("button", { text: "Inbox", contains: [".badge", { text: "1" }] });
    await contains("button", { text: "Starred messages", contains: [".badge", { text: "1" }] });
    const [partner] = pyEnv["res.partner"].read(serverState.partnerId);
    pyEnv["bus.bus"]._sendone(partner, "mail.message/delete", {
        message_ids: [messageId],
    });
    await contains(".o-mail-Message", { count: 0 });
    await contains("button", { text: "Inbox", contains: [".badge", { count: 0 }] });
    await contains("button", { text: "Starred messages", contains: [".badge", { count: 0 }] });
});
