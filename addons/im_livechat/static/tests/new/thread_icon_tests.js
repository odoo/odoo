/** @odoo-module */

import { afterNextRender, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("thread icon");

QUnit.test("Public website visitor is typing", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        anonymous_name: "Visitor 20",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: pyEnv.publicPartnerId }],
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { env, openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-mail-thread-icon .fa.fa-comments");
    const channel = pyEnv["mail.channel"].searchRead([["id", "=", channelId]])[0];
    // simulate receive typing notification from livechat visitor "is typing"
    await afterNextRender(() =>
        env.services.rpc("/im_livechat/notify_typing", {
            context: { mockedPartnerId: pyEnv.publicPartnerId },
            is_typing: true,
            uuid: channel.uuid,
        })
    );
    assert.containsOnce($, ".o-mail-discuss-header .o-mail-typing-icon");
    assert.containsOnce(
        $,
        ".o-mail-discuss-header .o-mail-typing-icon[title='Visitor 20 is typing...']"
    );
});
