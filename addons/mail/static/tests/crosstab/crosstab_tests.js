/** @odoo-module **/

import {
    afterNextRender,
    click,
    insertText,
    start,
    startServer,
    waitUntil,
} from "@mail/../tests/helpers/test_utils";

import { triggerHotkey, patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module("crosstab");

QUnit.test("Messages are received cross-tab", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "General",
    });
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    await tab1.openDiscuss(channelId);
    await tab2.openDiscuss(channelId);
    await tab1.insertText(".o-mail-Composer-input", "Hello World!");
    await tab1.click("button:contains(Send)");
    assert.containsOnce(tab1.target, ".o-mail-Message:contains(Hello World!)");
    assert.containsOnce(tab2.target, ".o-mail-Message:contains(Hello World!)");
});

QUnit.test("Delete starred message updates counter", async (assert) => {
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
    await tab1.openDiscuss(channelId);
    await tab2.openDiscuss(channelId);
    assert.containsOnce(tab2.target, "button:contains(Starred1)");
    await afterNextRender(() =>
        tab1.env.services.rpc("/mail/message/update_content", {
            message_id: messageId,
            body: "",
            attachment_ids: [],
        })
    );
    assert.containsNone(tab2.target, "button:contains(Starred1)");
});

QUnit.test("Thread rename", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        create_uid: pyEnv.currentPartnerId,
        name: "General",
    });
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    await tab1.openDiscuss(channelId);
    await tab2.openDiscuss(channelId);
    await tab1.insertText(".o-mail-Discuss-threadName", "Sales", { replace: true });
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.containsOnce(tab2.target, ".o-mail-Discuss-threadName[title='Sales']");
    assert.containsOnce(tab2.target, ".o-mail-DiscussCategoryItem:contains(Sales)");
});

QUnit.test("Thread description update", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        create_uid: pyEnv.currentPartnerId,
        name: "General",
    });
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    await tab1.openDiscuss(channelId);
    await tab2.openDiscuss(channelId);
    await tab1.insertText(".o-mail-Discuss-threadDescription", "The very best channel", {
        replace: true,
    });
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.containsOnce(
        tab2.target,
        ".o-mail-Discuss-threadDescription[title='The very best channel']"
    );
});

QUnit.test("Channel subscription is renewed when channel is manually added", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General", channel_member_ids: [] });
    const { env, openDiscuss } = await start();
    patchWithCleanup(env.services["bus_service"], {
        forceUpdateChannels() {
            assert.step("update-channels");
        },
    });
    await openDiscuss();
    await click("[title='Add or join a channel']");
    await insertText(".o-mail-ChannelSelector", "General");
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.verifySteps(["update-channels"]);
});

QUnit.test("Channel subscription is renewed when channel is added from invite", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "Sales", channel_member_ids: [] });
    const { env, openDiscuss } = await start();
    patchWithCleanup(env.services["bus_service"], {
        forceUpdateChannels() {
            assert.step("update-channels");
        },
    });
    await openDiscuss();
    // simulate receiving invite
    await afterNextRender(() => {
        env.services.orm.call("discuss.channel", "add_members", [[channelId]], {
            partner_ids: [pyEnv.currentPartnerId],
        });
    });
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
    await openDiscuss();
    await click(".o-mail-DiscussCategoryItem .btn[title='Leave this channel']");
    assert.verifySteps(["update-channels"]);
});

QUnit.test("Adding attachments", async (assert) => {
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
    await tab1.openDiscuss(channelId);
    await tab2.openDiscuss(channelId);
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "test.txt",
        mimetype: "text/plain",
    });
    await afterNextRender(() =>
        tab1.env.services.rpc("/mail/message/update_content", {
            body: "Hello world!",
            attachment_ids: [attachmentId],
            message_id: messageId,
        })
    );
    assert.containsOnce(tab2.target, ".o-mail-AttachmentCard:contains(test.txt)");
});

QUnit.test("Remove attachment from message", async (assert) => {
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
    await tab1.openDiscuss(channelId);
    await tab2.openDiscuss(channelId);
    assert.containsOnce(tab1.target, ".o-mail-AttachmentCard:contains(test.txt)");
    await tab2.click(".o-mail-AttachmentCard-unlink");
    await tab2.click(".modal-footer .btn:contains(Ok)");
    assert.containsNone(tab1.target, ".o-mail-AttachmentCard:contains(test.txt)");
});

QUnit.test("Message delete notification", async (assert) => {
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
    await openDiscuss();
    await click("[title='Expand']");
    await click("[title='Mark as Todo']");
    assert.containsOnce($, "button:contains(Inbox) .badge");
    assert.containsOnce($, "button:contains(Starred) .badge");
    pyEnv["bus.bus"]._sendone(pyEnv.currentPartnerId, "mail.message/delete", {
        message_ids: [messageId],
    });
    await waitUntil(".o-mail-Message", 0);
    assert.containsNone($, "button:contains(Inbox) .badge");
    assert.containsNone($, "button:contains(Starred) .badge");
});
