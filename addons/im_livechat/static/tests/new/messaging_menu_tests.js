/** @odoo-module */

import { getFixture } from "@web/../tests/helpers/utils";

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";

let target;
QUnit.module("messaging menu", {
    beforeEach() {
        target = getFixture();
    },
});

QUnit.test('livechats should be in "chat" filter', async function (assert) {
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
    assert.containsOnce(target, ".o-mail-messaging-menu button:contains(All)");
    assert.hasClass($(".o-mail-messaging-menu button:contains(All)"), "fw-bolder");
    assert.containsOnce(target, ".o-mail-notification-item:contains(Visitor 11)");
    await click(".o-mail-messaging-menu button:contains(Chat)");
    assert.hasClass($(".o-mail-messaging-menu button:contains(Chat)"), "fw-bolder");
    assert.containsOnce(target, ".o-mail-notification-item:contains(Visitor 11)");
});
