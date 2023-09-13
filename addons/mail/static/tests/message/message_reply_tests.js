/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { nextTick, patchWithCleanup } from "@web/../tests/helpers/utils";
import { click, contains } from "@web/../tests/utils";

QUnit.module("message reply");

QUnit.test("click on message in reply to highlight the parent message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const messageId = pyEnv["mail.message"].create({
        body: "Hey lol",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    pyEnv["mail.message"].create({
        body: "Reply to Hey",
        message_type: "comment",
        model: "discuss.channel",
        parent_id: messageId,
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click(".o-mail-Message:contains(Reply to Hey) .o-mail-MessageInReply-message");
    await contains(".o-mail-Message:contains(Hey lol).o-highlighted");
});

QUnit.test("click on message in reply to scroll to the parent message", async (assert) => {
    // make scroll behavior instantaneous.
    patchWithCleanup(Element.prototype, {
        scrollIntoView() {
            return super.scrollIntoView(true);
        },
    });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const [oldestMessageId] = pyEnv["mail.message"].create(
        Array(20)
            .fill(0)
            .map(() => ({
                body: "Non Empty Body ".repeat(25),
                message_type: "comment",
                model: "discuss.channel",
                res_id: channelId,
            }))
    );
    pyEnv["mail.message"].create({
        body: "Response to first message",
        message_type: "comment",
        model: "discuss.channel",
        parent_id: oldestMessageId,
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click(
        ".o-mail-Message:contains(Response to first message) .o-mail-MessageInReply-message"
    );
    await nextTick();
    assert.isVisible(document.querySelector(".o-mail-Message"));
});

QUnit.test("reply shows correct author avatar", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const messageId = pyEnv["mail.message"].create({
        body: "Hey there",
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    });
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    pyEnv["mail.message"].create({
        body: "Howdy",
        message_type: "comment",
        model: "discuss.channel",
        author_id: partnerId,
        parent_id: messageId,
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    const replyAvatar = document.querySelector(".o-mail-MessageInReply-avatar");
    assert.ok(
        replyAvatar.dataset["src"].includes(
            `/discuss/channel/${channelId}/partner/${pyEnv.currentPartnerId}/avatar_128`
        )
    );
});
