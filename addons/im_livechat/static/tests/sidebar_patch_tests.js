/* @odoo-module */

import { afterNextRender, click, start, startServer } from "@mail/../tests/helpers/test_utils";

import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";
import { nextTick } from "@web/../tests/helpers/utils";

QUnit.module("discuss sidebar (patch)");

QUnit.test("Unknown visitor", async (assert) => {
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
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-mail-DiscussSidebar .o-mail-DiscussCategory-livechat");
    assert.containsOnce($, ".o-mail-DiscussCategoryItem:contains(Visitor 11)");
});

QUnit.test("Known user with country", async (assert) => {
    const pyEnv = await startServer();
    const countryId = pyEnv["res.country"].create({
        code: "be",
        name: "Belgium",
    });
    const partnerId = pyEnv["res.partner"].create({
        country_id: countryId,
        name: "Jean",
    });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-mail-DiscussCategoryItem:contains(Jean (Belgium))");
});

QUnit.test("Do not show channel when visitor is typing", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([pyEnv.currentUserId], { im_status: "online" });
    const livechatChannelId = pyEnv["im_livechat.channel"].create({
        user_ids: [pyEnv.currentUserId],
    });
    const channelId = pyEnv["discuss.channel"].create({
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
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { env, openDiscuss } = await start();
    await openDiscuss();
    assert.containsNone($, ".o-mail-DiscussCategory-livechat");
    // simulate livechat visitor typing
    const channel = pyEnv["discuss.channel"].searchRead([["id", "=", channelId]])[0];
    await env.services.rpc("/im_livechat/notify_typing", {
        context: {
            mockedPartnerId: pyEnv.publicPartnerId,
        },
        is_typing: true,
        uuid: channel.uuid,
    });
    await nextTick();
    assert.containsNone($, ".o-mail-DiscussCategory-livechat");
});

QUnit.test("Close should update the value on the server", async (assert) => {
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
    pyEnv["res.users.settings"].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_livechat_open: true,
    });
    const currentUserId = pyEnv.currentUserId;
    const { env, openDiscuss } = await start();
    await openDiscuss();
    const initalSettings = await env.services.orm.call(
        "res.users.settings",
        "_find_or_create_for_user",
        [[currentUserId]]
    );
    assert.ok(initalSettings.is_discuss_sidebar_category_livechat_open);
    await click(".o-mail-DiscussCategory-livechat .btn");
    const newSettings = await env.services.orm.call(
        "res.users.settings",
        "_find_or_create_for_user",
        [[currentUserId]]
    );
    assert.notOk(newSettings.is_discuss_sidebar_category_livechat_open);
});

QUnit.test("Open should update the value on the server", async (assert) => {
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
    pyEnv["res.users.settings"].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_livechat_open: false,
    });
    const currentUserId = pyEnv.currentUserId;
    const { env, openDiscuss } = await start();
    await openDiscuss();
    const initalSettings = await env.services.orm.call(
        "res.users.settings",
        "_find_or_create_for_user",
        [[currentUserId]]
    );
    assert.notOk(initalSettings.is_discuss_sidebar_category_livechat_open);
    await click(".o-mail-DiscussCategory-livechat .btn");
    const newSettings = await env.services.orm.call(
        "res.users.settings",
        "_find_or_create_for_user",
        [[currentUserId]]
    );
    assert.ok(newSettings.is_discuss_sidebar_category_livechat_open);
});

QUnit.test("Open from the bus", async (assert) => {
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
    const settingsId = pyEnv["res.users.settings"].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_livechat_open: false,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsNone($, ".o-mail-DiscussCategory-livechat + .o-mail-DiscussCategoryItem");
    await afterNextRender(() => {
        pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.record/insert", {
            "res.users.settings": {
                id: settingsId,
                is_discuss_sidebar_category_livechat_open: true,
            },
        });
    });
    assert.containsOnce($, ".o-mail-DiscussCategory-livechat + .o-mail-DiscussCategoryItem");
});

QUnit.test("Close from the bus", async (assert) => {
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
    const settingsId = pyEnv["res.users.settings"].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_livechat_open: true,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-mail-DiscussCategory-livechat + .o-mail-DiscussCategoryItem");
    await afterNextRender(() => {
        pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.record/insert", {
            "res.users.settings": {
                id: settingsId,
                is_discuss_sidebar_category_livechat_open: false,
            },
        });
    });
    assert.containsNone($, ".o-mail-DiscussCategory-livechat + .o-mail-DiscussCategoryItem");
});

QUnit.test("Smiley face avatar for an anonymous livechat item", async (assert) => {
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
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.strictEqual(
        $(".o-mail-DiscussCategory-livechat + .o-mail-DiscussCategoryItem img")[0].dataset.src,
        "/mail/static/src/img/smiley/avatar.jpg"
    );
});

QUnit.test("Partner profile picture for livechat item linked to a partner", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Jean" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.strictEqual(
        $(".o-mail-DiscussCategory-livechat + .o-mail-DiscussCategoryItem img")[0].dataset.src,
        `/web/image/res.partner/${partnerId}/avatar_128`
    );
});

QUnit.test("No counter if the category is unfolded and with unread messages", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            [
                0,
                0,
                {
                    message_unread_counter: 10,
                    partner_id: pyEnv.currentPartnerId,
                },
            ],
            [0, 0, { partner_id: pyEnv.publicPartnerId }],
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsNone(
        $,
        ".o-mail-DiscussCategory-livechat .o-mail-Discuss-category-counter",
        "should not have a counter if the category is unfolded and with unread messages"
    );
});

QUnit.test("No counter if category is folded and without unread messages", async (assert) => {
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
    pyEnv["res.users.settings"].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_livechat_open: false,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsNone(
        $,
        ".o-mail-DiscussCategory-livechat .o-discuss-badge",
        "should not have a counter if the category is unfolded and with unread messages"
    );
});

QUnit.test(
    "Counter should have correct value of unread threads if category is folded and with unread messages",
    async (assert) => {
        const pyEnv = await startServer();
        pyEnv["discuss.channel"].create({
            anonymous_name: "Visitor 11",
            channel_member_ids: [
                [
                    0,
                    0,
                    {
                        message_unread_counter: 10,
                        partner_id: pyEnv.currentPartnerId,
                    },
                ],
                [0, 0, { partner_id: pyEnv.publicPartnerId }],
            ],
            channel_type: "livechat",
            livechat_operator_id: pyEnv.currentPartnerId,
        });
        pyEnv["res.users.settings"].create({
            user_id: pyEnv.currentUserId,
            is_discuss_sidebar_category_livechat_open: false,
        });
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.strictEqual($(".o-mail-DiscussCategory-livechat .o-discuss-badge").text(), "1");
    }
);

QUnit.test("Close manually by clicking the title", async (assert) => {
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
    pyEnv["res.users.settings"].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_livechat_open: true,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce(
        $,
        ".o-mail-DiscussCategory-livechat + .o-mail-DiscussCategoryItem",
        "Category is unfolded initially"
    );
    // fold the livechat category
    await click(".o-mail-DiscussCategory-livechat .btn");
    assert.containsNone($, ".o-mail-DiscussCategoryItem");
});

QUnit.test("Open manually by clicking the title", async (assert) => {
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
    pyEnv["res.users.settings"].create({
        user_id: pyEnv.currentUserId,
        is_discuss_sidebar_category_livechat_open: false,
    });
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsNone(
        $,
        ".o-mail-DiscussCategory-livechat + .o-mail-DiscussCategoryItem",
        "Category is folded initially"
    );
    // open the livechat category
    await click(".o-mail-DiscussCategory-livechat .btn");
    assert.containsOnce($, ".o-mail-DiscussCategory-livechat + .o-mail-DiscussCategoryItem");
});

QUnit.test("Category item should be invisible if the category is closed", async (assert) => {
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
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-mail-DiscussCategory-livechat + .o-mail-DiscussCategoryItem");
    await click(".o-mail-DiscussCategory-livechat .btn");
    assert.containsNone($, ".o-mail-DiscussCategory-livechat + .o-mail-DiscussCategoryItem");
});

QUnit.test(
    "Active category item should be visible even if the category is closed",
    async (assert) => {
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
        const { openDiscuss } = await start();
        await openDiscuss();
        assert.containsOnce($, ".o-mail-DiscussCategory-livechat + .o-mail-DiscussCategoryItem");
        await click(".o-mail-DiscussCategory-livechat + .o-mail-DiscussCategoryItem");
        assert.containsOnce(
            $,
            ".o-mail-DiscussCategory-livechat + .o-mail-DiscussCategoryItem.o-active"
        );
        await click(".o-mail-DiscussCategory-livechat .btn");
        assert.containsOnce($, ".o-mail-DiscussCategory-livechat + .o-mail-DiscussCategoryItem");
    }
);

QUnit.test("Clicking on unpin button unpins the channel", async (assert) => {
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
    const { openDiscuss } = await start({
        services: {
            notification: makeFakeNotificationService((message) => assert.step(message)),
        },
    });
    await openDiscuss();
    await click(".o-mail-DiscussCategoryItem [title='Unpin Conversation']");
    assert.verifySteps(["You unpinned your conversation with Visitor 11"]);
});

QUnit.test("Message unread counter", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Harry" });
    const userId = pyEnv["res.users"].create({ name: "Harry", partner_id: partnerId });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: pyEnv.publicPartnerId }],
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { env, openDiscuss } = await start();
    await openDiscuss();
    await afterNextRender(async () =>
        env.services.rpc("/im_livechat/chat_post", {
            context: { mockedUserId: userId },
            message_content: "hu",
            uuid: pyEnv["discuss.channel"].searchRead([["id", "=", channelId]])[0].uuid,
        })
    );
    assert.containsOnce($, ".o-mail-DiscussCategoryItem .badge:contains(1)");
});
