/* @odoo-module */

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("chat window (patch)");

QUnit.test("No call buttons", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: pyEnv.publicPartnerId }],
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    assert.containsOnce($, ".o-mail-ChatWindow");
    assert.containsNone($, ".o-mail-ChatWindow-header .o-mail-ChatWindow-command i.fa-phone");
    assert.containsNone($, ".o-mail-ChatWindow-header .o-mail-ChatWindow-command i.fa-gear");
});

QUnit.test("closing a chat window with no message from admin side unpins it", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Demo" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            [
                0,
                0,
                {
                    is_pinned: true,
                    partner_id: pyEnv.currentPartnerId,
                },
            ],
            [0, 0, { partner_id: partnerId }],
        ],
        channel_type: "livechat",
        uuid: "channel-10-uuid",
    });
    const { env } = await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await click(".o-mail-ChatWindow-header .o-mail-ChatWindow-command[title='Close Chat Window']");
    const [channel] = await env.services.rpc(
        "/discuss/channel/info",
        { channel_id: channelId },
        { silent: true }
    );
    assert.strictEqual(channel.is_pinned, false, "Livechat channel should not be pinned");
});
