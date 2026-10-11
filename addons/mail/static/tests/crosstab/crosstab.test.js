import {
    click,
    contains as mailContains,
    defineMailModels,
    hover,
    insertText,
    openDiscuss,
    start,
    startServer,
    triggerHotkey,
    MENU_ACTIVE_IDS,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, setInputFiles, test } from "@odoo/hoot";
import { press, waitFor, waitForNone } from "@odoo/hoot-dom";
import { mockDate } from "@odoo/hoot-mock";

import { Command, getService, mockService, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("Messages are received cross-tab", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true, waitUntilSubscribe: false });
    await openDiscuss(channelId, { target: env1 });
    await openDiscuss(channelId, { target: env2 });
    await waitFor(`${env1.selector} .o-mail-Thread:contains('Welcome to #General!'):count(1)`); // wait for loaded and focus in input
    await waitFor(`${env2.selector} .o-mail-Thread:contains('Welcome to #General!'):count(1)`); // wait for loaded and focus in input
    await insertText(`${env1.selector} .o-mail-Composer-input`, "Hello World!");
    await press("Enter");
    await waitFor(`${env1.selector} .o-mail-Message-content:text('Hello World!'):count(1)`);
    await waitFor(`${env2.selector} .o-mail-Message-content:text('Hello World!'):count(1)`);
});

test.tags("focus required");
test("Thread rename", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        create_uid: serverState.userId,
        name: "General",
    });
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true, waitUntilSubscribe: false });
    await openDiscuss(channelId, { target: env1 });
    await openDiscuss(channelId, { target: env2 });
    await insertText(`${env1.selector} .o-mail-DiscussContent-threadName:enabled`, "Sales", {
        replace: true,
    });
    triggerHotkey("Enter");
    await waitFor(`${env2.selector} .o-mail-DiscussContent-threadName[title='Sales']:count(1)`);
    await waitFor(`${env2.selector} .o-mail-NotificationItem:has(:text('Sales')):count(1)`);
});

test.tags("focus required");
test("Thread description update", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        create_uid: serverState.userId,
        name: "General",
    });
    const env1 = await start({ asTab: true });
    const env2 = await start({ asTab: true, waitUntilSubscribe: false });
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
    await waitFor(
        `${env2.selector} .o-mail-DiscussContent-threadDescription[title='The very best channel']:count(1)`
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
            expect.step("update-channels");
        },
    });
    await openDiscuss();
    await waitFor(".o-mail-MessagingMenuItem:count(1)");
    getService("mail.store").fetchStoreData("/discuss/channel/add_members", {
        channel_id: channelId,
        user_ids: [serverState.userId],
    });
    await waitFor(".o-mail-MessagingMenuItem:count(2)");
    await expect.waitForSteps(["update-channels"]); // FIXME: sometimes 1 or 2 update-channels
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
    const env2 = await start({ asTab: true, waitUntilSubscribe: false });
    await openDiscuss(channelId, { target: env1 });
    await openDiscuss(channelId, { target: env2 });
    const file = new File(["file content"], "test.txt", { type: "text/plain" });
    await waitFor(`${env1.selector} .o-mail-Message:contains('Hello world!'):count(1)`);
    await waitFor(`${env2.selector} .o-mail-Message:contains('Hello world!'):count(1)`);
    await hover(`${env1.selector} .o-mail-Message`);
    await click(`${env1.selector} .o-mail-Message button[title='Expand']`);
    await click(`${env1.selector} .o-dropdown-item:text('Edit')`);
    await click(`${env1.selector} .o-mail-Message .o-mail-Composer button[title='More Actions']`);
    await click(`${env1.selector} .o_popover button[name='upload-files']`);
    await click(`${env1.selector} .o-mail-Message .o-mail-Composer .o_input_file`);
    await setInputFiles([file]);
    await waitFor(
        `${env1.selector} .o-mail-AttachmentContainer:not(.o-isUploading):contains(test.txt):count(1)`
    );
    await click(`${env1.selector} .o-mail-Message .o-mail-Composer button[data-type='save']`);

    await waitFor(
        `${env2.selector} .o-mail-AttachmentContainer:not(.o-isUploading):contains(test.txt):count(1)`
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
    const env2 = await start({ asTab: true, waitUntilSubscribe: false });
    await openDiscuss(channelId, { target: env1 });
    await openDiscuss(channelId, { target: env2 });
    await waitFor(`${env1.selector} .o-mail-AttachmentCard:has(:text('test.txt')):count(1)`);
    await click(`${env2.selector} .o-mail-Attachment-unlink`);
    await click(`${env2.selector} .modal-footer .btn:text('Delete Attachment')`);
    await waitForNone(`${env1.selector} .o-mail-AttachmentCard:has(:text('test.txt'))`);
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
    await openDiscuss(MENU_ACTIVE_IDS.NOTIFICATION);
    await click(".o-mail-MessagingMenuItem [title='Message Actions']");
    await click(".o-dropdown-item:contains('Bookmark')");
    await mailContains("button:has(:text('Notifications'))", { contains: [".badge:text('1')"] });
    await mailContains("button:has(:text('Bookmarks'))", { contains: [".badge:text('1')"] });
    const [partner] = pyEnv["res.partner"].read(serverState.partnerId);
    pyEnv["bus.bus"]._sendone(partner, "mail.message/delete", {
        message_ids: [messageId],
    });
    await waitForNone(".o-mail-Message");
    await mailContains("button:has(:text('Notifications'))", {
        contains: [".badge", { count: 0 }],
    });
    await waitForNone("button:has(:text('Bookmarks'))");
});

test("Mark conversation as read when sole unread message has been deleted", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
        channel_member_ids: [
            Command.create({
                message_unread_counter: 1,
                new_message_separator: 0,
                partner_id: serverState.partnerId,
                seen_message_id: false,
            }),
        ],
    });
    const messageId = pyEnv["mail.message"].create({
        body: "Unread message",
        message_type: "comment",
        model: "discuss.channel",
        partner_ids: [serverState.partnerId],
        res_id: channelId,
    });
    await start();
    // Do not open the conversation so that seen_message_id stays unset.
    await openDiscuss(MENU_ACTIVE_IDS.CHANNEL);
    await waitFor(".o-mail-NotificationItem-badge:count(1)");
    pyEnv["mail.message"].unlink(messageId);
    await waitForNone(".o-mail-NotificationItem-badge");
});
