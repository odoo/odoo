/** @odoo-module **/

import { afterNextRender, start } from "@mail/../tests/helpers/test_utils";

QUnit.module("messaging");

QUnit.test(
    "Posting a message to a partner out of discuss should open a chat window",
    async (assert) => {
        const { env, pyEnv } = await start();
        const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
        const userId = pyEnv["res.users"].create({ partner_id: partnerId });
        const channelId = pyEnv["mail.channel"].create({
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId }],
            ],
            channel_type: "chat",
        });
        const [channel] = pyEnv["mail.channel"].searchRead([["id", "=", channelId]]);
        await afterNextRender(() =>
            env.services.rpc("/mail/chat_post", {
                context: { mockedUserId: userId },
                message_content: "new message",
                uuid: channel.uuid,
            })
        );
        assert.containsOnce($, ".o-mail-ChatWindow-header:contains(Dumbledore)");
    }
);

QUnit.test(
    "Posting a message to a partner should open a chat window after leaving discuss",
    async (assert) => {
        const { env, openDiscuss, openFormView, pyEnv } = await start();
        await openDiscuss();
        const partnerId = pyEnv["res.partner"].create({ name: "Dumbledore" });
        const userId = pyEnv["res.users"].create({ partner_id: partnerId });
        const channelId = pyEnv["mail.channel"].create({
            channel_member_ids: [
                [0, 0, { partner_id: pyEnv.currentPartnerId }],
                [0, 0, { partner_id: partnerId }],
            ],
            channel_type: "chat",
        });
        const [channel] = pyEnv["mail.channel"].searchRead([["id", "=", channelId]]);
        env.services.rpc("/mail/chat_post", {
            context: { mockedUserId: userId },
            message_content: "new message",
            uuid: channel.uuid,
        });
        // leaving discuss.
        await openFormView("res.partner", partnerId);
        assert.containsOnce($, ".o-mail-ChatWindow-header:contains(Dumbledore)");
    }
);
