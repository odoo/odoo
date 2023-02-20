/** @odoo-module */

import {
    afterNextRender,
    click,
    insertText,
    start,
    startServer,
} from "@mail/../tests/helpers/test_utils";
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

QUnit.test("No reply button", async function (assert) {
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
    assert.containsNone(document.body, "i[aria-label='Reply']");
});

QUnit.test("add livechat in the sidebar on visitor sending first message", async function (assert) {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([pyEnv.currentUserId], { im_status: "online" });
    const countryId = pyEnv["res.country"].create({ code: "be", name: "Belgium" });
    const livechatChannelId = pyEnv["im_livechat.channel"].create({
        user_ids: [pyEnv.currentUserId],
    });
    const channelId = pyEnv["mail.channel"].create({
        anonymous_name: "Visitor (Belgium)",
        channel_member_ids: [
            [0, 0, { is_pinned: false, partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: pyEnv.publicPartnerId }],
        ],
        channel_type: "livechat",
        country_id: countryId,
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { env, openDiscuss } = await start();
    await openDiscuss();
    assert.containsNone(target, ".o-mail-category-livechat");
    // simulate livechat visitor sending a message
    const [channel] = pyEnv["mail.channel"].searchRead([["id", "=", channelId]]);
    await afterNextRender(async () =>
        env.services.rpc("/mail/chat_post", {
            context: { mockedUserId: false },
            uuid: channel.uuid,
            message_content: "new message",
        })
    );
    assert.containsOnce(target, ".o-mail-category-livechat");
    assert.containsOnce(target, ".o-mail-category-livechat + .o-mail-category-item");
    assert.containsOnce(
        target,
        ".o-mail-category-livechat + .o-mail-category-item:contains(Visitor (Belgium))"
    );
});

QUnit.test("reaction button should not be present on livechat", async function (assert) {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        anonymous_name: "Visitor 11",
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
        channel_partner_ids: [pyEnv.currentPartnerId, pyEnv.publicPartnerId],
    });
    const { insertText, openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-composer-textarea", "Test");
    await click(".o-mail-composer-send-button");
    await click(".o-mail-message");
    assert.containsNone(target, ".i[title='Add a Reaction']");
});

QUnit.test("invite button should be present on livechat", async function (assert) {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: pyEnv.publicPartnerId }],
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce(target, ".o-mail-discuss-actions [title='Add Users']");
});

QUnit.test(
    "livechats are sorted by last activity time in the sidebar: most recent at the top",
    async function (assert) {
        const pyEnv = await startServer();
        pyEnv["mail.channel"].create([
            {
                anonymous_name: "Visitor 11",
                channel_member_ids: [
                    [
                        0,
                        0,
                        {
                            last_interest_dt: "2021-01-01 10:00:00",
                            partner_id: pyEnv.currentPartnerId,
                        },
                    ],
                    [0, 0, { partner_id: pyEnv.publicPartnerId }],
                ],
                channel_type: "livechat",
                livechat_operator_id: pyEnv.currentPartnerId,
            },
            {
                anonymous_name: "Visitor 12",
                channel_member_ids: [
                    [
                        0,
                        0,
                        {
                            last_interest_dt: "2021-02-01 10:00:00",
                            partner_id: pyEnv.currentPartnerId,
                        },
                    ],
                    [0, 0, { partner_id: pyEnv.publicPartnerId }],
                ],
                channel_type: "livechat",
                livechat_operator_id: pyEnv.currentPartnerId,
            },
        ]);
        const { openDiscuss } = await start();
        await openDiscuss();
        const initialLivechats = document.querySelectorAll(".o-mail-category-item");
        assert.strictEqual(initialLivechats[0].textContent, "Visitor 12");
        assert.strictEqual(initialLivechats[1].textContent, "Visitor 11");
        // post a new message on the last channel
        await click($(initialLivechats[1]));
        await insertText(".o-mail-composer-textarea", "Blabla");
        await click(".o-mail-composer-send-button");
        const newLivechats = document.querySelectorAll(".o-mail-category-item");
        assert.strictEqual(newLivechats.length, 2, "should have 2 livechat items");
        assert.strictEqual(newLivechats[0].textContent, "Visitor 11");
        assert.strictEqual(newLivechats[1].textContent, "Visitor 12");
    }
);
