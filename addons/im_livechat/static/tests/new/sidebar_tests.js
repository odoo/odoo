/** @odoo-module */

import { getFixture, nextTick } from "@web/../tests/helpers/utils";

import { start, startServer } from "@mail/../tests/helpers/test_utils";

let target;
QUnit.module("discuss sidebar", {
    beforeEach() {
        target = getFixture();
    },
});

QUnit.test("Unknown visitor", async function (assert) {
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
    assert.containsOnce(target, ".o-mail-discuss-sidebar .o-mail-category-livechat");
    assert.containsOnce(target, ".o-mail-category-item:contains(Visitor 11)");
});

QUnit.test("Known user with country", async function (assert) {
    const pyEnv = await startServer();
    const resCountryId1 = pyEnv["res.country"].create({
        code: "be",
        name: "Belgium",
    });
    const resPartnerId1 = pyEnv["res.partner"].create({
        country_id: resCountryId1,
        name: "Jean",
    });
    pyEnv["mail.channel"].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: resPartnerId1 }],
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(target, ".o-mail-category-item:contains(Jean (Belgium))");
});

QUnit.test("Do not show channel when visitor is typing", async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    pyEnv["res.users"].write([pyEnv.currentUserId], { im_status: "online" });
    const imLivechatChannelId1 = pyEnv["im_livechat.channel"].create({
        user_ids: [pyEnv.currentUserId],
    });
    const mailChannelId1 = pyEnv["mail.channel"].create({
        channel_member_ids: [
            [
                0,
                0,
                {
                    is_pinned: false,
                    partner_id: pyEnv.currentPartnerId,
                },
            ],
            [0, 0, { partner_id: pyEnv.publicPartnerId }],
        ],
        channel_type: "livechat",
        livechat_channel_id: imLivechatChannelId1,
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { env, openDiscuss } = await start();
    await openDiscuss();
    assert.containsNone(target, ".o-mail-category-livechat");
    // simulate livechat visitor typing
    const channel = pyEnv["mail.channel"].searchRead([["id", "=", mailChannelId1]])[0];
    await env.services.rpc("/im_livechat/notify_typing", {
        context: {
            mockedPartnerId: pyEnv.publicPartnerId,
        },
        is_typing: true,
        uuid: channel.uuid,
    });
    await nextTick();
    assert.containsNone(target, ".o-mail-category-livechat");
});
