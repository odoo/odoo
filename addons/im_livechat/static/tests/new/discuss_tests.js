/** @odoo-module */

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";
import { getFixture } from "@web/../tests/helpers/utils";

let target;
QUnit.module("discuss", {
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
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsNone(target, ".o-mail-discuss-actions button i.fa-phone");
    assert.containsNone(target, ".o-mail-discuss-actions button i.fa-gear");
});

QUnit.test("No reaction button", async function (assert) {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        anonymous_name: "Visitor 11",
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
        channel_partner_ids: [pyEnv.currentPartnerId, pyEnv.publicPartnerId],
    });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "mail.channel",
        res_id: channelId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await click(".o-mail-message");
    assert.containsNone(document.body, "i[aria-label='Add a Reaction']");
});
