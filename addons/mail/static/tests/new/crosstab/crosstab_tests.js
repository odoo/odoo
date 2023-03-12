/** @odoo-module **/

import { afterNextRender, click, start, startServer } from "@mail/../tests/helpers/test_utils";

import { triggerHotkey, patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module("crosstab");

QUnit.test("Messages are received cross-tab", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
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
    const channelId = pyEnv["mail.channel"].create({
        name: "General",
    });
    const messageId = pyEnv["mail.message"].create({
        body: "Hello World!",
        model: "mail.channel",
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
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
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
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
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

QUnit.test("Channel subscription is renewed when channel is added", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "Sales", channel_member_ids: [] });
    const { env, openDiscuss } = await start();
    patchWithCleanup(env.services["bus_service"], {
        forceUpdateChannels() {
            assert.step("update-channels");
        },
    });
    await openDiscuss();
    await afterNextRender(() => {
        env.services.orm.call("mail.channel", "add_members", [[channelId]], {
            partner_ids: [pyEnv.currentPartnerId],
        });
    });
    assert.verifySteps(["update-channels"]);
});

QUnit.test("Channel subscription is renewed when channel is left", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({ name: "Sales" });
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
    const channelId = pyEnv["mail.channel"].create({ name: "Hogwarts Legacy" });
    const messageId = pyEnv["mail.message"].create({
        body: "Hello world!",
        model: "mail.channel",
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
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "test.txt",
        mimetype: "text/plain",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        body: "Hello World!",
        message_type: "comment",
        model: "mail.channel",
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

QUnit.test("Add member to channel", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
    const userId = pyEnv["res.users"].create({ name: "Harry" });
    pyEnv["res.partner"].create({ name: "Harry", user_ids: [userId] });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[title='Show Member List']");
    assert.containsOnce($, ".o-mail-ChannelMember:contains(Mitchell Admin)");
    await click("button[title='Add Users']");
    await click(".o-mail-ChannelInvitation-selectable:contains(Harry)");
    await click("button[title='Invite to Channel']");
    assert.containsOnce($, ".o-mail-ChannelMember:contains(Harry)");
});

QUnit.test("Remove member from channel", async (assert) => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "Harry" });
    const partnerId = pyEnv["res.partner"].create({
        name: "Harry",
        user_ids: [userId],
    });
    const channelId = pyEnv["mail.channel"].create({
        name: "General",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
    });
    const { env, openDiscuss } = await start();
    await openDiscuss(channelId);
    await click("button[title='Show Member List']");
    assert.containsOnce($, ".o-mail-ChannelMember:contains(Harry)");
    env.services.orm.call("mail.channel", "action_unfollow", [channelId], {
        context: { mockedUserId: userId },
    });
});
