/** @odoo-module */

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("messaging menu");

QUnit.test('livechats should be in "chat" filter', async (assert) => {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({
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
    assert.containsOnce($, ".o-MessagingMenu button:contains(All)");
    assert.hasClass($(".o-MessagingMenu button:contains(All)"), "fw-bolder");
    assert.containsOnce($, ".o-NotificationItem:contains(Visitor 11)");
    await click(".o-MessagingMenu button:contains(Chat)");
    assert.hasClass($(".o-MessagingMenu button:contains(Chat)"), "fw-bolder");
    assert.containsOnce($, ".o-NotificationItem:contains(Visitor 11)");
});
