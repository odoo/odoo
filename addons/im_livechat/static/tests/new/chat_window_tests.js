/** @odoo-module */

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";
import { getFixture } from "@web/../tests/helpers/utils";

let target;
QUnit.module("chat window", {
    beforeEach() {
        target = getFixture();
    },
});

QUnit.test("No call buttons", async function (assert) {
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
    await click(".o-mail-notification-item");
    assert.containsOnce(target, ".o-mail-chat-window");
    assert.containsNone(target, ".o-mail-chat-window-header .o-mail-command i.fa-phone");
    assert.containsNone(target, ".o-mail-chat-window-header .o-mail-command i.fa-gear");
});
